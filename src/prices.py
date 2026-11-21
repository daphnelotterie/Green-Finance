#!/usr/bin/env python3
"""
TÉLÉCHARGEMENT DES SÉRIES DE PRIX HISTORIQUES (YAHOO FINANCE)
-------------------------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry Béchu & Jean Jardel (Kanopy AM)

Récupère via yfinance les cours de clôture ajustés (dividendes et divisions) :
    1. des titres du portefeuille final (results/<mode>/portefeuille_final_pondere.csv, sortie de l'optimiseur)
    2. du benchmark MSCI World (ETF iShares Core MSCI World UCITS, IWDA.AS, coté en EUR)
puis les convertit en euros (devise de référence d'un fonds de droit français).
Le portefeuille final ne contient ni ticker Yahoo ni devise : on les retrouve dans data/raw/all_data.csv.
Tout autre fichier de titres avec une colonne 'ticker' peut être passé à la place (par exemple l'univers
sélectionnable results/<mode>/actifs_selectionnes.csv, pour un optimiseur qui utiliserait la covariance).

Sorties (dossier data/cache/prices/) :
    - prix_devise_locale.csv : cours ajustés en devise de cotation (une colonne par titre)
    - taux_de_change.csv     : taux EUR/devise utilisés pour la conversion (unités de devise pour 1 EUR)
    - prix_eur.csv           : cours convertis en EUR + colonne du benchmark MSCI World

Ces séries alimentent l'historique rétrospectif et la simulation à poids figés depuis fin 2024.
"""

import csv
import os
from pathlib import Path

import pandas as pd

# Devises cotées en sous-unités (pence, agorot, cents) : devise réelle et diviseur
MINOR_UNITS = {"GBp": ("GBP", 100.0), "GBX": ("GBP", 100.0), "ILA": ("ILS", 100.0), "ZAc": ("ZAR", 100.0)}

BENCHMARK_COLUMN = "BENCHMARK MSCI World (IWDA.AS)"


def resolve_project_root():
    return str(Path(__file__).resolve().parent.parent)


class HistoricalPriceLoader:
    def __init__(self, all_data_csv, weighted_portfolio_csv, start_date="2015-01-01", end_date=None,
                 base_currency="EUR", benchmark_ticker="IWDA.AS", benchmark_currency="EUR", split_date="2024-12-31",
                 preserve_tickers=()):
        self.all_data_csv = all_data_csv
        self.weighted_portfolio_csv = weighted_portfolio_csv
        self.start_date = start_date
        self.end_date = end_date
        self.base_currency = base_currency
        self.benchmark_ticker = benchmark_ticker
        self.benchmark_currency = benchmark_currency
        self.split_date = split_date
        self.preserve_tickers = preserve_tickers

        self.assets = []
        self.load_universe()

    def load_universe(self):
        """Charge les titres du portefeuille final, avec leur ticker Yahoo et leur devise lus dans all_data.csv."""
        with open(self.all_data_csv, 'r', encoding='utf-8') as f:
            reference = {r['ticker']: r for r in csv.DictReader(f)}

        with open(self.weighted_portfolio_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            raw_rows = list(reader)
        present = {row['ticker'] for row in raw_rows}
        for ticker in self.preserve_tickers:
            if ticker not in present:
                if ticker not in reference:
                    raise ValueError(f'Titre du cache inconnu dans la source : {ticker}')
                raw_rows.append(reference[ticker])

        for r in raw_rows:
            ref = reference.get(r['ticker'], {})
            asset = dict(r, ticker_yahoo=(ref.get('ticker_yahoo') or '').strip(), currency=(ref.get('currency') or '').strip())
            if asset['ticker_yahoo']:
                self.assets.append(asset)
            else:
                raise ValueError(f"Pas de ticker Yahoo pour {r.get('ticker')}")

        self.n = len(self.assets)
        self.yahoo_to_ticker = {r['ticker_yahoo']: r['ticker'] for r in self.assets}
        weight = sum(float(r.get('weight_decimal') or 0.0) for r in self.assets)
        weight_info = f", {weight:.1%} du poids" if weight > 0 else ""
        print(f"[Prices] Portefeuille chargé : {self.n} titres à télécharger{weight_info} (+ benchmark {self.benchmark_ticker}).")

    def download_prices(self):
        """Télécharge les cours de clôture ajustés (dividendes et divisions) des titres et du benchmark."""
        import yfinance as yf
        cache_dir = Path(resolve_project_root()) / 'data/cache/yfinance'
        cache_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache_dir))
        yahoo_tickers = list(self.yahoo_to_ticker) + [self.benchmark_ticker]
        data = yf.download(yahoo_tickers, start=self.start_date, end=self.end_date,
                           auto_adjust=True, progress=False, threads=True)
        closes = data["Close"].dropna(how="all").sort_index()

        missing = [t for t in yahoo_tickers if t not in closes.columns or closes[t].isna().all()]
        if missing:
            raise ValueError(f"Téléchargement incomplet, cache conservé : {missing}")

        self.benchmark_local = closes[self.benchmark_ticker] if self.benchmark_ticker not in missing else None
        self.prices_local = closes[[t for t in self.yahoo_to_ticker if t not in missing]]
        print(f"[Prices] Cours téléchargés : {self.prices_local.shape[1]} titres, {len(self.prices_local)} séances "
              f"du {self.prices_local.index[0]:%d/%m/%Y} au {self.prices_local.index[-1]:%d/%m/%Y}.")
        return self.prices_local

    def download_fx_rates(self):
        """Télécharge les taux de change (unités de devise pour 1 EUR) nécessaires à la conversion."""
        import yfinance as yf
        self.quote_currency = {}
        for r in self.assets:
            cur = r['currency']
            self.quote_currency[r['ticker_yahoo']] = MINOR_UNITS.get(cur, (cur, 1.0))

        currencies = sorted({cur for cur, _ in self.quote_currency.values()} | {self.benchmark_currency})
        currencies = [cur for cur in currencies if cur != self.base_currency]
        fx_tickers = {f"{self.base_currency}{cur}=X": cur for cur in currencies}

        if fx_tickers:
            data = yf.download(list(fx_tickers), start=self.start_date, end=self.end_date,
                               auto_adjust=True, progress=False, threads=True)
            fx = data["Close"].rename(columns=fx_tickers)
            if any(cur not in fx or fx[cur].dropna().empty for cur in fx_tickers.values()):
                raise ValueError("Taux de change manquants : cache conservé.")
        else:
            fx = pd.DataFrame(index=self.prices_local.index)
        fx[self.base_currency] = 1.0

        self.fx_rates = fx.sort_index().ffill()
        print(f"[Prices] Taux de change téléchargés : {', '.join(currencies) or 'aucun'} (pour 1 {self.base_currency}).")
        return self.fx_rates

    def convert_to_base_currency(self):
        """Convertit chaque série en EUR : prix / diviseur de sous-unité / taux EUR-devise du jour."""
        fx = self.fx_rates.reindex(self.prices_local.index, method="ffill")

        converted = {}
        for yahoo_ticker in self.prices_local.columns:
            cur, divisor = self.quote_currency[yahoo_ticker]
            converted[yahoo_ticker] = self.prices_local[yahoo_ticker] / divisor / fx[cur]
        self.prices_base = pd.DataFrame(converted, index=self.prices_local.index)

        self.benchmark_base = None
        if self.benchmark_local is not None:
            self.benchmark_base = self.benchmark_local / fx[self.benchmark_currency]

        print(f"[Prices] Cours convertis en {self.base_currency}.")
        return self.prices_base

    def summarize(self):
        """Couverture des séries : période historique (avant split_date) et période récente (depuis split_date)."""
        split = pd.Timestamp(self.split_date)
        rows = []
        for label, part in [(f"Avant le {split:%d/%m/%Y}", self.prices_base[self.prices_base.index < split]),
                            (f"Depuis le {split:%d/%m/%Y}", self.prices_base[self.prices_base.index >= split])]:
            n_with_data = int(part.notna().any().sum())
            dates = f"{part.index[0]:%d/%m/%Y} -> {part.index[-1]:%d/%m/%Y}" if len(part) else "aucune séance"
            rows.append((label, dates, len(part), n_with_data))

        start = pd.Timestamp(self.start_date) + pd.Timedelta(days=31)
        late_starts = [(self.yahoo_to_ticker[t], f"{self.prices_base[t].first_valid_index():%d/%m/%Y}")
                       for t in self.prices_base.columns if self.prices_base[t].first_valid_index() > start]
        return rows, late_starts

    def export_prices(self, output_dir):
        """Exporte les séries de prix (devise locale, taux de change, EUR + benchmark) dans data/cache/prices/."""
        os.makedirs(output_dir, exist_ok=True)

        local = self.prices_local.rename(columns=self.yahoo_to_ticker)
        if self.benchmark_local is not None:
            local[BENCHMARK_COLUMN] = self.benchmark_local
        local.to_csv(os.path.join(output_dir, "prix_devise_locale.csv"), index_label="date", float_format="%.6f")

        self.fx_rates.to_csv(os.path.join(output_dir, "taux_de_change.csv"), index_label="date", float_format="%.6f")

        base = self.prices_base.rename(columns=self.yahoo_to_ticker)
        if self.benchmark_base is not None:
            base[BENCHMARK_COLUMN] = self.benchmark_base
        base.to_csv(os.path.join(output_dir, "prix_eur.csv"), index_label="date", float_format="%.6f")

        print(f"[Prices] Fichiers exportés avec succès dans : {output_dir}")


def run_prices(input_path, universe_path, output_dir=None, end_date=None):
    """Rafraîchit le cache sans perdre les titres téléchargés pour les autres modes."""
    output_dir = Path(output_dir or Path(resolve_project_root()) / "data/cache/prices")
    existing = output_dir / 'prix_eur.csv'
    preserved = [c for c in pd.read_csv(existing, nrows=0).columns
                 if c not in ('date', BENCHMARK_COLUMN)] if existing.exists() else []
    loader = HistoricalPriceLoader(input_path, universe_path, end_date=end_date,
                                   split_date="2024-12-31", preserve_tickers=preserved)
    loader.download_prices()
    loader.download_fx_rates()
    loader.convert_to_base_currency()
    if loader.prices_base.empty or (loader.prices_base <= 0).any().any():
        raise ValueError("Cours téléchargés invalides : cache conservé.")
    # Tous les téléchargements doivent réussir avant de remplacer le cache existant.
    staging = output_dir / ".download"
    loader.export_prices(staging)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("prix_devise_locale.csv", "taux_de_change.csv", "prix_eur.csv"):
        (staging / name).replace(output_dir / name)
    staging.rmdir()
    return output_dir / "prix_eur.csv"
