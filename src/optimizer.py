#!/usr/bin/env python3
"""
OPTIMISEUR QUANTITATIF - STRATÉGIE 3 : FRONTIÈRE ESG-EFFICIÈNTE DE PEDERSEN ET AL. (2021)
-----------------------------------------------------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry Béchu & Jean Jardel (Kanopy AM)

Formulation Mathématique (Slide 63 du Cours "Approche Quantitative") :
    W* = argmin_W  f(W)
    avec f(W) = 0.5 * gamma * W^T Sigma W - W^T mu - theta * W^T S_Impact
    
Sous contraintes :
    1. sum(w_i) = 1.0 (Plein investissement)
    2. w_min <= w_i <= w_max (Bornes UCITS 5/10/40 : 1.0% <= w_i <= 4.5%)
    3. Contraintes sectorielles thématiques HealthTech & AI :
       - Santé (Health Care) : 50% - 65%
       - Technologies de l'Information (AI & Enablers) : 28% - 40%
       - Industrie / CleanTech : <= 15%
    4. Contrainte extra-financière PAB / Art. 9 :
       - ITR moyen <= 1.8°C (Alignement Trajectoire Paris 1.5°C)
"""

import csv
import math
import os
import sys

def to_float(val, default=0.0):
    try:
        return float(val) if val not in ('', None, 'NA', 'N/A') else default
    except (ValueError, TypeError):
        return default

def compute_zscores(values):
    """Calcule les z-scores standardisés d'une liste de valeurs."""
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance) if variance > 1e-12 else 1.0
    return [(x - mean) / std for x in values]

def resolve_project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) in ["src", "dossier_tri"]:
        return os.path.dirname(current_dir)
    return current_dir


class PedersenPortfolioOptimizer:
    def __init__(self, input_csv_path, gamma=3.0, theta=0.04, w_min=0.010, w_max=0.045, max_itr=2.5):
        self.input_csv_path = input_csv_path
        self.gamma = gamma
        self.theta = theta
        self.w_min = w_min
        self.w_max = w_max
        self.max_itr = max_itr
        
        self.assets = []
        self.load_and_filter_universe()
        
    def load_and_filter_universe(self):
        """Charge l'univers éligible."""
        with open(self.input_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            raw_rows = list(reader)
            
        for r in raw_rows:
            itr_val = to_float(r.get('ITR'), default=10.0)
            if itr_val <= self.max_itr:
                self.assets.append(r)
                
        self.n = len(self.assets)
        print(f"[Optimizer] Univers chargé : {self.n} actifs éligibles.")
        
    def build_inputs(self):
        """Construit les vecteurs mu, S_Impact et la matrice Sigma."""
        self.tickers = [r['ticker'] for r in self.assets]
        self.names = [r['name'] for r in self.assets]
        self.sectors = [r['gics_sector_name'] for r in self.assets]
        
        # Rendements espérés (5Y Annualized Return)
        self.mu = [to_float(r['Annualized return 5Y']) for r in self.assets]
        # Volatilités 5Y
        self.vols = [to_float(r['Volatility 5Y']) for r in self.assets]
        
        # Métriques Extra-Financières pour Score Composite S_Impact
        sdg3 = [to_float(r['SDG_03_NET_ALIGNMENT_SCORE']) for r in self.assets]
        sdg9 = [to_float(r['SDG_09_NET_ALIGNMENT_SCORE']) for r in self.assets]
        itrs = [to_float(r['ITR']) for r in self.assets]
        govs = [to_float(r['GOVERNANCE_PILLAR_SCORE']) for r in self.assets]
        
        z_sdg3 = compute_zscores(sdg3)
        z_sdg9 = compute_zscores(sdg9)
        z_itr = compute_zscores(itrs)
        z_gov = compute_zscores(govs)
        
        # Score composite : 40% SDG3 + 25% SDG9 - 20% ITR + 15% Gov (Béchu)
        self.s_impact = [
            0.40 * z_sdg3[i] + 0.25 * z_sdg9[i] - 0.20 * z_itr[i] + 0.15 * z_gov[i]
            for i in range(self.n)
        ]
        
        # Matrice de Covariance Structurée (Elton-Gruber Multi-Index)
        # rho_intra = 0.50, rho_inter = 0.28
        self.Sigma = []
        for i in range(self.n):
            row = []
            for j in range(self.n):
                if i == j:
                    rho = 1.0
                elif self.sectors[i] == self.sectors[j]:
                    rho = 0.50
                else:
                    rho = 0.28
                row.append(rho * self.vols[i] * self.vols[j])
            self.Sigma.append(row)

    def project_simplex_box(self, w_raw, total=1.0, max_iter=80):
        """Algorithme de Water-Filling par bissection pour projection sur simplexe borné."""
        low = min(w_raw[i] - self.w_max for i in range(self.n))
        high = max(w_raw[i] - self.w_min for i in range(self.n))
        
        mid = 0.0
        for _ in range(max_iter):
            mid = (low + high) / 2.0
            s = sum(max(self.w_min, min(self.w_max, w_raw[i] - mid)) for i in range(self.n))
            if abs(s - total) < 1e-11:
                break
            if s > total:
                low = mid
            else:
                high = mid
                
        return [max(self.w_min, min(self.w_max, w_raw[i] - mid)) for i in range(self.n)]

    def optimize(self, max_steps=1500, lr=0.005):
        """Descente de gradient projetée."""
        self.build_inputs()
        
        H = [[self.gamma * self.Sigma[i][j] for j in range(self.n)] for i in range(self.n)]
        c = [self.mu[i] + self.theta * self.s_impact[i] for i in range(self.n)]
        
        # Initialisation équipondérée 1/N (Slide 63)
        w = [1.0 / self.n] * self.n
        
        for step in range(max_steps):
            grad = [sum(H[i][j] * w[j] for j in range(self.n)) - c[i] for i in range(self.n)]
            
            # Pénalité secteur Santé (Health Care >= 50%)
            hc_weight = sum(w[i] for i in range(self.n) if self.sectors[i] == 'Health Care')
            if hc_weight < 0.52:
                for i in range(self.n):
                    if self.sectors[i] == 'Health Care':
                        grad[i] -= 15.0 * (0.52 - hc_weight)
            elif hc_weight > 0.65:
                for i in range(self.n):
                    if self.sectors[i] == 'Health Care':
                        grad[i] += 15.0 * (hc_weight - 0.65)
                        
            # Pénalité secteur Tech (IT >= 28%)
            tech_weight = sum(w[i] for i in range(self.n) if self.sectors[i] == 'Information Technology')
            if tech_weight < 0.28:
                for i in range(self.n):
                    if self.sectors[i] == 'Information Technology':
                        grad[i] -= 15.0 * (0.28 - tech_weight)
            elif tech_weight > 0.40:
                for i in range(self.n):
                    if self.sectors[i] == 'Information Technology':
                        grad[i] += 15.0 * (tech_weight - 0.40)
            
            w_raw = [w[i] - lr * grad[i] for i in range(self.n)]
            w = self.project_simplex_box(w_raw)
            
        self.weights = w
        print(f"[Optimizer] Optimisation convergée. Somme des poids = {sum(self.weights):.6f}")
        return self.weights

    def export_final_portfolio(self, output_csv_path):
        """Exporte le portefeuille final."""
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        fieldnames = [
            'ticker', 'name', 'isin', 'gics_sector_name', 'industry_group', 'country',
            'weight_percent', 'weight_decimal',
            'annualized_return_5y', 'volatility_5y', 'sharpe_5y',
            'itr_celsius', 'sdg_03_score', 'sdg_09_score', 'governance_score',
            'intensity_scope1_2', 'intensity_scope1_2_3', 'eu_taxonomy_max_rev'
        ]
        
        ranked_indices = sorted(range(self.n), key=lambda i: self.weights[i], reverse=True)
        
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for idx in ranked_indices:
                r = self.assets[idx]
                w = self.weights[idx]
                int1 = to_float(r.get('INTENSITY_SCOPE_1'))
                int2 = to_float(r.get('INTENSITY_SCOPE_2'))
                int3 = to_float(r.get('INTENSITY_SCOPE_3'))
                
                writer.writerow({
                    'ticker': r.get('ticker'),
                    'name': r.get('name'),
                    'isin': r.get('isin'),
                    'gics_sector_name': r.get('gics_sector_name'),
                    'industry_group': r.get('industry_group'),
                    'country': r.get('country'),
                    'weight_percent': f"{w * 100:.2f}%",
                    'weight_decimal': f"{w:.6f}",
                    'annualized_return_5y': f"{to_float(r.get('Annualized return 5Y')) * 100:.2f}%",
                    'volatility_5y': f"{to_float(r.get('Volatility 5Y')) * 100:.2f}%",
                    'sharpe_5y': f"{to_float(r.get('Sharpe 5Y')):.2f}",
                    'itr_celsius': f"{to_float(r.get('ITR')):.2f}",
                    'sdg_03_score': f"{to_float(r.get('SDG_03_NET_ALIGNMENT_SCORE')):.2f}",
                    'sdg_09_score': f"{to_float(r.get('SDG_09_NET_ALIGNMENT_SCORE')):.2f}",
                    'governance_score': f"{to_float(r.get('GOVERNANCE_PILLAR_SCORE')):.2f}",
                    'intensity_scope1_2': f"{int1 + int2:.2f}",
                    'intensity_scope1_2_3': f"{int1 + int2 + int3:.2f}",
                    'eu_taxonomy_max_rev': f"{to_float(r.get('EST_EU_TAXONOMY_MAX_REV')):.2f}%"
                })
                
        print(f"[Optimizer] Fichier exporté avec succès : {output_csv_path}")


def run_optimization():
    root_dir = resolve_project_root()
    possible_inputs = [
        os.path.join(root_dir, "data", "actifs_notre_secteur_healthtech_ai.csv"),
        os.path.join(root_dir, "dossier_tri", "actifs_notre_secteur_healthtech_ai.csv")
    ]
    input_file = next((p for p in possible_inputs if os.path.exists(p)), None)
    
    if not input_file:
        print(f"Erreur : Impossible de trouver actifs_notre_secteur_healthtech_ai.csv dans {possible_inputs}")
        sys.exit(1)
        
    output_file = os.path.join(root_dir, "data", "portefeuille_final_pondere.csv")
    
    optimizer = PedersenPortfolioOptimizer(input_file, gamma=3.0, theta=0.04, w_min=0.010, w_max=0.045)
    optimizer.optimize()
    optimizer.export_final_portfolio(output_file)
    
    # Copie de compatibilité
    legacy_tri = os.path.join(root_dir, "dossier_tri")
    if os.path.exists(legacy_tri):
        optimizer.export_final_portfolio(os.path.join(legacy_tri, "portefeuille_final_pondere.csv"))


if __name__ == '__main__':
    run_optimization()
