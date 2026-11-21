#!/usr/bin/env python3
"""Deux allocations sur le même univers, sans modifier les règles de sélection.

``original`` conserve l'objectif de Daphné / Pedersen :
    min 0.5 * gamma * w' Sigma w - mu'w - theta * S_Impact'w.
La covariance structurée (corrélations 0.50 / 0.28) et les rendements 5Y
restent ceux du code initial. Les contraintes remplacent ses pénalités.

``esg_risk`` conserve les budgets de risque ESG commencés dans le dépôt :
    min_y 0.5 * y' Sigma y - somme(b_i * log(y_i)), puis w = y / somme(y).
Sigma est estimée sur 156 rendements hebdomadaires EUR par Ledoit-Wolf,
connus à la date de constitution. Aucun rendement espéré n'est utilisé.

``te_div`` (stratégie A, thématique recalibrée) : moitié tracking error
minimale contre le MSCI World (IWDA), moitié diversification maximale, sous
les mêmes contraintes plus une intensité carbone S1+2+3 <= 50 % de celle du
MSCI World et un plafond de 12 % par sous-secteur (secteur GICS + industry_group).
La moyenne de deux solutions admissibles reste admissible.

Contraintes communes : somme=1, poids<=4.5%, Santé 50-65%, Tech 28-40%,
autres<=15%, ITR pondéré<=1.8°C. Plancher original=1%, ESG=0%.
Une solution infaisable ou un échec du solveur arrête le calcul.
"""

import argparse
import csv
import json
import math
import warnings
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize
from sklearn.covariance import LedoitWolf

try:
    from .prices import BENCHMARK_COLUMN
except ImportError:  # Exécution directe : python src/optimizer.py
    from prices import BENCHMARK_COLUMN


TOLERANCE = 1e-7
OPTIMIZER_MODES = ("original", "esg_risk", "te_div")
CARBON_FIELDS = ("INTENSITY_SCOPE_1", "INTENSITY_SCOPE_2", "INTENSITY_SCOPE_3")


def to_float(val, default=0.0):
    """Conversion pour les seules colonnes de présentation facultatives."""
    try:
        number = float(val)
        return number if math.isfinite(number) else default
    except (ValueError, TypeError):
        return default


def required_float(row, field):
    number = to_float(row.get(field), default=float("nan"))
    if not math.isfinite(number):
        raise ValueError(f"Donnée d'optimisation manquante/non finie : {row.get('ticker')} / {field}")
    return number


def compute_zscores(values):
    """Standardisation de population, inchangée (score nul si variance nulle)."""
    xs = np.asarray(values, dtype=float)
    if not len(xs) or not np.isfinite(xs).all():
        raise ValueError("Les scores d'impact doivent être non vides et finis.")
    std = float(xs.std())
    return ((xs - xs.mean()) / (std if std > 1e-6 else 1.0)).tolist()


def resolve_project_root():
    return str(Path(__file__).resolve().parent.parent)


def load_prices(prices_csv_path):
    """Cours EUR : une colonne par ticker et un index de dates unique."""
    # pandas renomme automatiquement deux en-têtes identiques en A / A.1.
    # Vérifier le CSV brut avant cette transformation évite un faux ticker.
    with open(prices_csv_path, encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), [])
    if (len(header) < 2 or any(not name.strip() for name in header[1:])
            or len(header[1:]) != len(set(header[1:]))):
        raise ValueError("Colonnes de cours absentes ou dupliquées.")
    prices = pd.read_csv(prices_csv_path, index_col=0, parse_dates=True).sort_index()
    if prices.index.has_duplicates or prices.columns.has_duplicates:
        raise ValueError("Les cours contiennent des dates ou des tickers en double.")
    if not isinstance(prices.index, pd.DatetimeIndex) or prices.index.isna().any():
        raise ValueError("Index de cours invalide.")
    prices = prices.apply(pd.to_numeric, errors="raise")
    if np.isinf(prices.values).any() or (prices <= 0).any().any():
        raise ValueError("Les cours renseignés doivent être strictement positifs et finis.")
    return prices


class ThematicConstraints:
    """Contraintes linéaires communes ; aucun seuil n'est relâché automatiquement.

    ``max_waci`` (facultatif) plafonne l'intensité carbone S1+2+3 moyenne pondérée ;
    les intensités des titres sont alors exigées (``waci``) par toutes les méthodes.
    ``max_sub_industry`` (facultatif) plafonne le poids de chaque sous-secteur ; le
    sous-secteur de chaque titre (``groups``) est alors exigé.
    """

    def __init__(self, health=(0.50, 0.65), tech=(0.28, 0.40), other_max=0.15, max_itr=1.8, max_waci=None,
                 max_sub_industry=None):
        if not (0 <= health[0] <= health[1] <= 1 and 0 <= tech[0] <= tech[1] <= 1):
            raise ValueError("Bornes sectorielles invalides.")
        if not 0 <= other_max <= 1 or not math.isfinite(max_itr):
            raise ValueError("Plafond sectoriel ou ITR invalide.")
        if max_waci is not None and (not math.isfinite(max_waci) or max_waci <= 0):
            raise ValueError("Plafond d'intensité carbone invalide.")
        if max_sub_industry is not None and not 0 < max_sub_industry <= 1:
            raise ValueError("Plafond par sous-secteur invalide.")
        self.health, self.tech = health, tech
        self.other_max, self.max_itr = other_max, max_itr
        self.max_waci = max_waci
        self.max_sub_industry = max_sub_industry

    def matrices(self, sectors, itrs, waci=None, groups=None):
        hc = np.array([float(s == "Health Care") for s in sectors])
        te = np.array([float(s == "Information Technology") for s in sectors])
        A = np.vstack([-hc, hc, -te, te, 1.0 - hc - te, np.asarray(itrs, dtype=float)])
        b = np.array([-self.health[0], self.health[1], -self.tech[0], self.tech[1],
                      self.other_max, self.max_itr])
        if self.max_waci is not None:
            if waci is None:
                raise ValueError("Contrainte carbone demandée sans intensités carbone des titres.")
            A = np.vstack([A, np.asarray(waci, dtype=float)])
            b = np.r_[b, self.max_waci]
        if self.max_sub_industry is not None:
            if groups is None:
                raise ValueError("Plafond par sous-secteur demandé sans sous-secteur des titres.")
            labels = np.asarray(groups)
            rows = [(labels == g).astype(float) for g in sorted(set(groups))]
            A = np.vstack([A, *rows])
            b = np.r_[b, [self.max_sub_industry] * len(rows)]
        return A, b

    def report(self, weights, sectors, itrs, w_min=0.0, w_max=1.0, waci=None, groups=None):
        w = np.asarray(weights, dtype=float)
        A, b = self.matrices(sectors, itrs, waci, groups)
        report = {"Santé": float(A[1] @ w), "Tech": float(A[3] @ w),
                  "Autres": float(A[4] @ w), "ITR": float(A[5] @ w),
                  "Somme": float(w.sum()), "Poids_min": float(w.min()), "Poids_max": float(w.max()),
                  "Dépassement": max(0.0, float((A @ w - b).max()), abs(float(w.sum()) - 1.0),
                                     float(w_min - w.min()), float(w.max() - w_max))}
        if self.max_waci is not None:
            report["Intensité carbone"] = float(A[6] @ w)
        if self.max_sub_industry is not None:
            report["Sous-secteur max"] = float(pd.Series(w).groupby(np.asarray(groups)).sum().max())
        return report

    @staticmethod
    def describe(report):
        carbon = f" | carbone {report['Intensité carbone']:.0f}" if "Intensité carbone" in report else ""
        sub = f" | sous-secteur max {report['Sous-secteur max']:.1%}" if "Sous-secteur max" in report else ""
        return (f"Santé {report['Santé']:.1%} | Tech {report['Tech']:.1%} | "
                f"Autres {report['Autres']:.1%} | ITR {report['ITR']:.2f}°C{carbon}{sub} | "
                f"dépassement max : {report['Dépassement']:.1e}")

    def as_dict(self):
        return {"health_min": self.health[0], "health_max": self.health[1],
                "tech_min": self.tech[0], "tech_max": self.tech[1],
                "other_max": self.other_max, "max_itr": self.max_itr, "max_waci": self.max_waci,
                "max_sub_industry": self.max_sub_industry}


@lru_cache(maxsize=4)
def msci_waci(all_data_path=None):
    """Intensité carbone S1+2+3 du MSCI World : poids de l'indice renormalisés sur la couverture."""
    path = Path(all_data_path) if all_data_path else Path(resolve_project_root()) / "data" / "raw" / "all_data.csv"
    total = covered = 0.0
    with open(path, encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            weight = to_float(row.get("Weight in MSCI World"), default=float("nan"))
            values = [to_float(row.get(field), default=float("nan")) for field in CARBON_FIELDS]
            if math.isfinite(weight) and all(math.isfinite(v) for v in values):
                total += weight * sum(values)
                covered += weight
    if covered <= 0:
        raise ValueError("Intensité carbone du MSCI World incalculable : poids ou intensités absents.")
    return total / covered


def feasible_weights(sectors, itrs, w_min, w_max, constraints, positive=False, waci=None, groups=None):
    """Point admissible par programme linéaire, intérieur pour les budgets log."""
    n = len(sectors)
    if not n or not 0 <= w_min <= w_max <= 1:
        raise ValueError("Univers vide ou bornes de poids invalides.")
    A, b = constraints.matrices(sectors, itrs, waci, groups)
    if positive:
        # Maximise le plus petit poids t pour initialiser log(y) sans zéro.
        A_lp = np.vstack([np.c_[A, np.zeros(len(b))], np.c_[-np.eye(n), np.ones(n)]])
        lp = linprog(np.r_[np.zeros(n), -1.0], A_ub=A_lp,
                     b_ub=np.r_[b, np.zeros(n)], A_eq=np.array([np.r_[np.ones(n), 0.0]]),
                     b_eq=[1.0], bounds=[(w_min, w_max)] * n + [(0.0, w_max)], method="highs")
        interior_ok = lp.success and lp.x[-1] > 1e-9
    else:
        lp = linprog(np.zeros(n), A_ub=A, b_ub=b, A_eq=np.ones((1, n)), b_eq=[1.0],
                     bounds=[(w_min, w_max)] * n, method="highs")
        interior_ok = lp.success
    if not interior_ok:
        raise ValueError(f"Contraintes infaisables avec {n} titres et bornes {w_min:.1%}-{w_max:.1%} "
                         f"(point strictement positif requis : {positive}) : {lp.message}")
    return lp.x[:n]


def verify_solution(weights, result, sectors, itrs, w_min, w_max, constraints, waci=None, groups=None):
    if not result.success or not np.isfinite(weights).all():
        raise RuntimeError(f"Optimisation non convergée : {result.message}")
    report = constraints.report(weights, sectors, itrs, w_min, w_max, waci, groups)
    if report["Dépassement"] > TOLERANCE:
        raise RuntimeError(f"Solution hors contraintes : {report}")
    return report


def solve_constrained_qp(H, c, sectors, itrs, w_min, w_max, constraints, waci=None, groups=None):
    """Même objectif quadratique qu'à l'origine, contraintes désormais strictes."""
    n = len(c)
    A, b = constraints.matrices(sectors, itrs, waci, groups)
    initial = feasible_weights(sectors, itrs, w_min, w_max, constraints, waci=waci, groups=groups)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0, "jac": lambda w: np.ones(n)},
            {"type": "ineq", "fun": lambda w: b - A @ w, "jac": lambda w: -A}]
    with warnings.catch_warnings():
        # SLSQP signale ses essais intermédiaires hors boîte avant de les
        # ramener dans la boîte ; seule la solution finale est contrôlée ici.
        warnings.filterwarnings("ignore", message="Values in x were outside bounds during a minimize step, clipping to bounds",
                                category=RuntimeWarning, module=r"scipy\.optimize\._slsqp_py")
        res = minimize(lambda w: 0.5 * w @ H @ w - c @ w, initial, jac=lambda w: H @ w - c,
                       method="SLSQP", bounds=[(w_min, w_max)] * n, constraints=cons,
                       options={"maxiter": 3000, "ftol": 1e-12})
    # Ne pas tronquer/renormaliser après le solveur : cela pourrait casser A w <= b.
    verify_solution(res.x, res, sectors, itrs, w_min, w_max, constraints, waci, groups)
    return res.x, res


def solve_max_diversification(cov, sectors, itrs, w_max, constraints, waci=None, groups=None):
    """Diversification maximale (Choueifaty & Coignard, 2008) : max somme(w_i s_i) / sqrt(w'Sw).

    Forme convexe équivalente : min y'Sy sous s'y = 1, y >= 0 et contraintes rendues
    homogènes (A y <= b somme(y), y_i <= w_max somme(y)), puis w = y / somme(y).
    """
    n = len(sectors)
    vols = np.sqrt(np.diag(cov))
    A, b = constraints.matrices(sectors, itrs, waci, groups)
    G = np.vstack([A - b[:, None], np.eye(n) - w_max])
    initial = feasible_weights(sectors, itrs, 0.0, w_max, constraints, positive=True, waci=waci, groups=groups)
    y0 = initial / (vols @ initial)
    cons = [{"type": "eq", "fun": lambda y: vols @ y - 1.0, "jac": lambda y: vols},
            {"type": "ineq", "fun": lambda y: -G @ y, "jac": lambda y: -G}]
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Values in x were outside bounds during a minimize step, clipping to bounds",
                                category=RuntimeWarning, module=r"scipy\.optimize\._slsqp_py")
        res = minimize(lambda y: y @ cov @ y, y0, jac=lambda y: 2.0 * cov @ y, method="SLSQP",
                       bounds=[(0.0, None)] * n, constraints=cons, options={"maxiter": 3000, "ftol": 1e-12})
    weights = res.x / res.x.sum()
    verify_solution(weights, res, sectors, itrs, 0.0, w_max, constraints, waci, groups)
    return weights, res


def solve_risk_budgeting(cov, budgets, sectors, itrs, w_max, constraints):
    """Budgets sous contraintes homogènes ; égalité exacte non garantie quand
    les contraintes thématiques / de concentration sont actives."""
    n = len(budgets)
    A, b = constraints.matrices(sectors, itrs)
    initial = feasible_weights(sectors, itrs, 0.0, w_max, constraints, positive=True)
    G = np.vstack([A - b[:, None], np.eye(n) - w_max])
    y0 = initial / np.sqrt(initial @ cov @ initial)
    cons = [{"type": "ineq", "fun": lambda y: -G @ y, "jac": lambda y: -G}]
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Values in x were outside bounds during a minimize step, clipping to bounds",
                                category=RuntimeWarning, module=r"scipy\.optimize\._slsqp_py")
        res = minimize(lambda y: 0.5 * y @ cov @ y - budgets @ np.log(y), y0,
                       jac=lambda y: cov @ y - budgets / y, method="SLSQP",
                       bounds=[(1e-10, None)] * n, constraints=cons,
                       options={"maxiter": 3000, "ftol": 1e-12})
    weights = res.x / res.x.sum()
    verify_solution(weights, res, sectors, itrs, 0.0, w_max, constraints)
    return weights, res


class PedersenPortfolioOptimizer:
    optimizer_mode = "original"

    def __init__(self, input_csv_path, gamma=3.0, theta=0.04, w_min=0.010, w_max=0.045,
                 max_itr=None, constraints=None, rows=None, market_inputs=None, verbose=True):
        self.input_csv_path = input_csv_path
        self.gamma, self.theta = gamma, theta
        if not math.isfinite(gamma) or gamma < 0 or not math.isfinite(theta):
            raise ValueError("Gamma doit être positif ou nul et theta fini.")
        self.w_min, self.w_max = w_min, w_max
        self.max_itr = max_itr
        self.constraints = constraints or ThematicConstraints()
        self.rows, self.market_inputs, self.verbose = rows, market_inputs, verbose
        self.assets, self.excluded_assets = [], []
        self.load_and_filter_universe()

    def load_and_filter_universe(self):
        if self.rows is not None:
            raw_rows = list(self.rows)
        else:
            with open(self.input_csv_path, encoding="utf-8-sig", newline="") as stream:
                raw_rows = list(csv.DictReader(stream))
        self.requested_count = len(raw_rows)
        seen = set()
        for row in raw_rows:
            ticker = row.get("ticker", "").strip()
            if not ticker or ticker in seen:
                raise ValueError(f"Ticker absent ou dupliqué : {ticker!r}")
            seen.add(ticker)
            itr = required_float(row, "ITR")
            if self.max_itr is not None and itr > self.max_itr:
                self.excluded_assets.append({"ticker": ticker, "reason": f"Plafond individuel explicite ITR {self.max_itr}"})
            else:
                self.assets.append(row)
        self.n = len(self.assets)
        if not self.n:
            raise ValueError("Aucun actif disponible pour l'optimisation.")
        if self.verbose:
            print(f"[Optimizer] Univers chargé : {self.n} actifs éligibles.")

    def build_inputs(self, include_market=True):
        self.tickers = [r["ticker"] for r in self.assets]
        self.names = [r["name"] for r in self.assets]
        self.sectors = [r["gics_sector_name"] for r in self.assets]
        self.itrs = [required_float(r, "ITR") for r in self.assets]
        if include_market:
            if self.market_inputs is None:
                self.mu = [required_float(r, "Annualized return 5Y") for r in self.assets]
                self.vols = [required_float(r, "Volatility 5Y") for r in self.assets]
            else:
                # Pas de repli sur le snapshot 2024 lors d'un calcul à une date passée.
                missing = set(self.tickers) - self.market_inputs.keys()
                if missing:
                    raise ValueError(f"Rendements/volatilités historiques manquants : {sorted(missing)}")
                self.mu = [self.market_inputs[t][0] for t in self.tickers]
                self.vols = [self.market_inputs[t][1] for t in self.tickers]
            if not np.isfinite(self.mu).all() or not np.isfinite(self.vols).all() or min(self.vols) <= 0:
                raise ValueError("Rendements et volatilités invalides pour Pedersen.")
        z_sdg3 = compute_zscores([required_float(r, "SDG_03_NET_ALIGNMENT_SCORE") for r in self.assets])
        z_sdg9 = compute_zscores([required_float(r, "SDG_09_NET_ALIGNMENT_SCORE") for r in self.assets])
        z_itr = compute_zscores(self.itrs)
        z_gov = compute_zscores([required_float(r, "GOVERNANCE_PILLAR_SCORE") for r in self.assets])
        self.s_impact = [0.40 * z_sdg3[i] + 0.25 * z_sdg9[i] - 0.20 * z_itr[i] + 0.15 * z_gov[i]
                         for i in range(self.n)]
        if include_market:
            self.Sigma = np.array([[(1.0 if i == j else 0.50 if self.sectors[i] == self.sectors[j] else 0.28)
                                    * self.vols[i] * self.vols[j] for j in range(self.n)] for i in range(self.n)])

    def record_solution(self, weights, result, covariance):
        self.weights = weights.tolist()
        self.report = verify_solution(weights, result, self.sectors, self.itrs, self.w_min, self.w_max,
                                      self.constraints, getattr(self, "waci", None), getattr(self, "groups", None))
        variance = float(weights @ covariance @ weights)
        self.risk_contributions = weights * (covariance @ weights) / variance
        self.diagnostics = {
            "optimizer_mode": self.optimizer_mode, "converged": bool(result.success),
            "solver_message": str(result.message), "iterations": int(result.nit),
            "objective_value": float(result.fun), "requested_assets": self.requested_count,
            "included_assets": self.n, "excluded_assets": self.excluded_assets,
            "weight_min_constraint": self.w_min, "weight_max_constraint": self.w_max,
            "constraints": self.constraints.as_dict(), "report": self.report,
            "model_volatility": math.sqrt(variance),
            "min_covariance_eigenvalue": float(np.linalg.eigvalsh(covariance).min()),
        }
        if self.verbose:
            print(f"[Optimizer] {self.optimizer_mode} : convergence atteinte ({result.nit} itérations).")
            print(f"[Optimizer] {ThematicConstraints.describe(self.report)}")

    def optimize(self):
        self.build_inputs()
        H = self.gamma * self.Sigma
        c = np.asarray(self.mu) + self.theta * np.asarray(self.s_impact)
        weights, result = solve_constrained_qp(H, c, self.sectors, self.itrs, self.w_min, self.w_max,
                                               self.constraints)
        self.record_solution(weights, result, self.Sigma)
        self.diagnostics.update({"gamma": self.gamma, "theta": self.theta,
                                 "covariance_method": "structured_rho_intra_0.50_inter_0.28",
                                 "expected_returns": "snapshot_5Y" if self.market_inputs is None else "historical_inputs"})
        return self.weights

    def export_final_portfolio(self, output_csv_path):
        """Poids à 12 décimales pour préserver somme et contraintes à la relecture."""
        Path(output_csv_path).parent.mkdir(parents=True, exist_ok=True)
        fields = ["ticker", "name", "isin", "gics_sector_name", "industry_group", "country",
                  "weight_percent", "weight_decimal", "annualized_return_5y", "volatility_5y", "sharpe_5y",
                  "itr_celsius", "sdg_03_score", "sdg_09_score", "governance_score", "intensity_scope1_2",
                  "intensity_scope1_2_3", "eu_taxonomy_max_rev", "impact_score", "risk_budget_decimal",
                  "risk_contribution_decimal", "optimizer_mode"]
        with open(output_csv_path, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for idx in sorted(range(self.n), key=lambda i: self.weights[i], reverse=True):
                row, weight = self.assets[idx], self.weights[idx]
                intensity = [to_float(row.get(f"INTENSITY_SCOPE_{k}")) for k in (1, 2, 3)]
                writer.writerow({
                    **{key: row.get(key, "") for key in fields[:6]},
                    "weight_percent": f"{weight * 100:.4f}%", "weight_decimal": f"{weight:.12f}",
                    "annualized_return_5y": f"{to_float(row.get('Annualized return 5Y')) * 100:.2f}%",
                    "volatility_5y": f"{to_float(row.get('Volatility 5Y')) * 100:.2f}%",
                    "sharpe_5y": f"{to_float(row.get('Sharpe 5Y')):.2f}",
                    "itr_celsius": f"{required_float(row, 'ITR'):.6f}",
                    "sdg_03_score": f"{required_float(row, 'SDG_03_NET_ALIGNMENT_SCORE'):.6f}",
                    "sdg_09_score": f"{required_float(row, 'SDG_09_NET_ALIGNMENT_SCORE'):.6f}",
                    "governance_score": f"{required_float(row, 'GOVERNANCE_PILLAR_SCORE'):.6f}",
                    "intensity_scope1_2": f"{sum(intensity[:2]):.6f}",
                    "intensity_scope1_2_3": f"{sum(intensity):.6f}",
                    "eu_taxonomy_max_rev": f"{to_float(row.get('EST_EU_TAXONOMY_MAX_REV')):.6f}%",
                    "impact_score": f"{self.s_impact[idx]:.12f}",
                    "risk_budget_decimal": f"{self.budgets[idx]:.12f}" if hasattr(self, "budgets") else "",
                    "risk_contribution_decimal": f"{self.risk_contributions[idx]:.12f}",
                    "optimizer_mode": self.optimizer_mode,
                })
        if self.verbose:
            print(f"[Optimizer] Portefeuille exporté : {output_csv_path}")


class ESGRiskBudgetingOptimizer(PedersenPortfolioOptimizer):
    """Budgets d'impact et covariance réelle ; pas de pari de rendement passé."""

    optimizer_mode = "esg_risk"

    def __init__(self, input_csv_path, prices=None, prices_csv_path=None, as_of="2024-12-31", window_weeks=156,
                 w_max=0.045, budget_range=(0.5, 1.5), constraints=None, rows=None, verbose=True):
        self.prices = prices if prices is not None else load_prices(prices_csv_path)
        self.as_of = pd.Timestamp(as_of)
        if pd.isna(self.as_of):
            raise ValueError("Date de constitution invalide.")
        self.window_weeks, self.budget_range = window_weeks, budget_range
        if window_weeks < 2 or not 0 < budget_range[0] <= budget_range[1]:
            raise ValueError("Fenêtre de covariance ou bornes des budgets invalides.")
        super().__init__(input_csv_path, w_min=0.0, w_max=w_max, constraints=constraints, rows=rows, verbose=verbose)

    def estimate_covariance(self):
        # Les semaines étiquetées après as_of sont retirées : au 31/12/2024,
        # le dernier vendredi utilisé est bien le 27/12, pas le 03/01/2025.
        tickers = [r["ticker"] for r in self.assets if r["ticker"] in self.prices.columns]
        history = self.prices.loc[:self.as_of, tickers].ffill(limit=10)
        weekly = history.resample("W-FRI").last().loc[:self.as_of]
        returns = weekly.pct_change(fill_method=None).iloc[1:].tail(self.window_weeks)
        if len(returns) != self.window_weeks:
            raise ValueError(f"Historique insuffisant au {self.as_of.date()} : {len(returns)} semaines, "
                             f"{self.window_weeks} requises.")
        complete = returns.columns[returns.notna().all() & np.isfinite(returns).all()]
        retained = set(complete)
        for row in self.assets:
            if row["ticker"] not in retained:
                reason = "Cours absents" if row["ticker"] not in tickers else "Historique incomplet sur la fenêtre"
                self.excluded_assets.append({"ticker": row["ticker"], "reason": reason})
        self.assets = [r for r in self.assets if r["ticker"] in retained]
        self.n = len(self.assets)
        if not self.n:
            raise ValueError("Aucun titre avec historique complet pour la covariance.")
        returns = returns[[r["ticker"] for r in self.assets]]
        self.weekly_returns = returns
        estimator = LedoitWolf().fit(returns.values)
        self.cov = estimator.covariance_ * 52
        if not np.isfinite(self.cov).all() or np.linalg.eigvalsh(self.cov).min() <= 0:
            raise ValueError("Covariance non définie positive : données de prix insuffisantes ou constantes.")
        self.covariance_details = {
            "as_of": self.as_of.date().isoformat(), "window_weeks": self.window_weeks,
            "first_return_week": returns.index.min().date().isoformat(),
            "last_return_week": returns.index.max().date().isoformat(),
            "observations": len(returns), "ledoit_wolf_shrinkage": float(estimator.shrinkage_),
            "forward_fill_limit_rows": 10,
        }

    def optimize(self):
        self.estimate_covariance()
        self.build_inputs(include_market=False)
        low, high = self.budget_range
        # Convention existante : rang moyen / N ; minimum > low, maximum high
        # avant normalisation ; les égalités reçoivent le rang moyen.
        budgets = low + (high - low) * pd.Series(self.s_impact).rank(pct=True).values
        self.budgets = budgets / budgets.sum()
        weights, result = solve_risk_budgeting(self.cov, self.budgets, self.sectors, self.itrs,
                                                self.w_max, self.constraints)
        self.record_solution(weights, result, self.cov)
        self.diagnostics.update({"covariance_method": "LedoitWolf_weekly_EUR", **self.covariance_details,
                                 "budget_range": list(self.budget_range),
                                 "risk_budget_absolute_gap_sum": float(np.abs(self.risk_contributions - self.budgets).sum()),
                                 "risk_budget_max_absolute_gap": float(np.abs(self.risk_contributions - self.budgets).max()),
                                 "risk_budgets_exact_under_active_constraints": False})
        return self.weights


class TrackingDiversificationOptimizer(ESGRiskBudgetingOptimizer):
    """Stratégie A : ensemble 50/50 tracking error minimale (MSCI World) + diversification maximale.

    Pourquoi : la tracking error minimale rapproche le fonds du marché sous les contraintes
    thématiques et climat (slide 63 du cours) ; la diversification maximale répartit le risque
    entre titres peu corrélés. Seule, chacune dépend fortement de la lecture retenue ; leur moyenne
    réduit ce risque de méthode. Aucun rendement espéré n'est estimé.
    Covariances Ledoit-Wolf sur 156 rendements hebdomadaires EUR connus à la date : jointe
    titres + IWDA pour la tracking error, titres seuls pour la diversification.
    Plafond de 12 % par sous-secteur (secteur GICS + industry_group de all_data.csv) : règle de
    diversification fixée a priori (au plus un huitième du fonds par segment), pas un réglage
    de performance ; sur les données 2018-2026, elle coûte en historique et n'apporte pas de gain
    significatif après 2024, mais limite la perte si le plus gros segment chute.
    """

    optimizer_mode = "te_div"

    def __init__(self, input_csv_path, prices=None, prices_csv_path=None, benchmark=None, as_of="2024-12-31",
                 window_weeks=156, w_max=0.045, mix=0.5, waci_ratio=0.5, sub_industry_cap=0.12, all_data_path=None,
                 constraints=None, rows=None, verbose=True):
        if not 0.0 <= mix <= 1.0:
            raise ValueError("La part tracking error doit être comprise entre 0 et 1.")
        self.mix, self.waci_ratio = mix, waci_ratio
        self.msci_waci = None
        if constraints is None:
            if waci_ratio is not None:
                self.msci_waci = msci_waci(str(all_data_path) if all_data_path else None)
            constraints = ThematicConstraints(max_waci=None if waci_ratio is None else waci_ratio * self.msci_waci,
                                              max_sub_industry=sub_industry_cap)
        super().__init__(input_csv_path, prices=prices, prices_csv_path=prices_csv_path, as_of=as_of,
                         window_weeks=window_weeks, w_max=w_max, constraints=constraints, rows=rows, verbose=verbose)
        if benchmark is None:
            if BENCHMARK_COLUMN not in self.prices.columns:
                raise ValueError("Cours du MSCI World (IWDA) absents : tracking error incalculable.")
            benchmark = self.prices[BENCHMARK_COLUMN]
        self.benchmark = benchmark

    def estimate_covariance(self):
        """Covariance des titres (parent) puis covariance jointe avec l'indice, mêmes semaines."""
        super().estimate_covariance()
        returns = self.weekly_returns
        weekly = self.benchmark.loc[:self.as_of].ffill(limit=10).resample("W-FRI").last().loc[:self.as_of]
        bench = weekly.pct_change(fill_method=None).reindex(returns.index)
        if bench.isna().any() or not np.isfinite(bench.to_numpy()).all():
            raise ValueError("Rendements hebdomadaires du MSCI World incomplets sur la fenêtre de covariance.")
        estimator = LedoitWolf().fit(np.column_stack([returns.values, bench.values]))
        self.cov_joint = estimator.covariance_ * 52
        self.covariance_details["ledoit_wolf_shrinkage_avec_indice"] = float(estimator.shrinkage_)

    def carbon_intensities(self):
        return [sum(required_float(r, field) for field in CARBON_FIELDS) for r in self.assets]

    def sub_industries(self):
        """Sous-secteur = secteur GICS + industry_group (certains libellés existent dans plusieurs secteurs)."""
        labels = [f"{r.get('gics_sector_name', '').strip()} | {r.get('industry_group', '').strip()}" for r in self.assets]
        if any(label.endswith("| ") for label in labels):
            raise ValueError("industry_group manquant : plafond par sous-secteur incalculable.")
        return labels

    def tracking_error(self, weights):
        v = np.r_[np.asarray(weights, dtype=float), -1.0]
        return math.sqrt(max(float(v @ self.cov_joint @ v), 0.0))

    def optimize(self):
        self.estimate_covariance()
        self.build_inputs(include_market=False)
        self.waci = self.carbon_intensities() if self.constraints.max_waci is not None else None
        self.groups = self.sub_industries() if self.constraints.max_sub_industry is not None else None
        n = self.n
        w_te, res_te = solve_constrained_qp(self.cov_joint[:n, :n], self.cov_joint[:n, n], self.sectors, self.itrs,
                                            0.0, self.w_max, self.constraints, self.waci, self.groups)
        w_div, res_div = solve_max_diversification(self.cov, self.sectors, self.itrs, self.w_max,
                                                   self.constraints, self.waci, self.groups)
        weights = self.mix * w_te + (1.0 - self.mix) * w_div
        result = SimpleNamespace(success=bool(res_te.success and res_div.success),
                                 message=f"TE : {res_te.message} | diversification : {res_div.message}",
                                 nit=int(res_te.nit + res_div.nit), fun=self.tracking_error(weights))
        self.components = {"tracking_error": w_te, "diversification": w_div}
        self.record_solution(weights, result, self.cov)
        vols = np.sqrt(np.diag(self.cov))
        div_ratio = lambda w: float(vols @ w / math.sqrt(w @ self.cov @ w))
        self.diagnostics.update({
            "covariance_method": "LedoitWolf_weekly_EUR (titres) + jointe titres/IWDA (tracking error)",
            **self.covariance_details, "part_tracking_error": self.mix,
            "tracking_error_ex_ante": self.tracking_error(weights),
            "tracking_error_ex_ante_poche_te": self.tracking_error(w_te),
            "tracking_error_ex_ante_poche_diversification": self.tracking_error(w_div),
            "ratio_diversification": div_ratio(weights),
            "ratio_diversification_poche_diversification": div_ratio(w_div),
            "intensite_carbone_msci_world": self.msci_waci, "plafond_intensite_carbone": self.constraints.max_waci,
            "plafond_sous_secteur": self.constraints.max_sub_industry,
            "poids_sous_secteurs": ({g: float(v) for g, v in pd.Series(weights).groupby(np.asarray(self.groups)).sum()
                                     .sort_values(ascending=False).items()} if self.groups is not None else None),
        })
        return self.weights


def run_optimization(optimizer_mode="original", input_path=None, output_path=None, prices_path=None,
                     as_of="2024-12-31", diagnostics_path=None, verbose=True):
    """Étape appelée par run_pipeline ; retourne le chemin du portefeuille CSV."""
    if optimizer_mode not in OPTIMIZER_MODES:
        raise ValueError(f"Optimiseur inconnu : {optimizer_mode!r}. Choisir {OPTIMIZER_MODES}.")
    root = Path(resolve_project_root())
    destination = root / "results" / {"original": "daphne_original", "esg_risk": "daphne_esg_risk",
                                      "te_div": "thematique_recalibree"}[optimizer_mode]
    input_path = Path(input_path) if input_path is not None else destination / "actifs_selectionnes.csv"
    output_path = Path(output_path) if output_path is not None else destination / "portefeuille_final_pondere.csv"
    diagnostics_path = Path(diagnostics_path) if diagnostics_path is not None else output_path.with_name("diagnostics_optimisation.json")
    if optimizer_mode in ("esg_risk", "te_div"):
        prices_path = Path(prices_path) if prices_path is not None else root / "data" / "cache" / "prices" / "prix_eur.csv"
        optimizer_class = ESGRiskBudgetingOptimizer if optimizer_mode == "esg_risk" else TrackingDiversificationOptimizer
        optimizer = optimizer_class(input_path, prices_csv_path=prices_path, as_of=as_of, verbose=verbose)
    else:
        optimizer = PedersenPortfolioOptimizer(input_path, verbose=verbose)
    optimizer.optimize()
    optimizer.export_final_portfolio(output_path)
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    with diagnostics_path.open("w", encoding="utf-8") as stream:
        json.dump(optimizer.diagnostics, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--optimizer-mode", choices=OPTIMIZER_MODES, default="original")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prices", type=Path)
    parser.add_argument("--as-of", default="2024-12-31")
    args = parser.parse_args()
    run_optimization(args.optimizer_mode, args.input, args.output, args.prices, args.as_of)
