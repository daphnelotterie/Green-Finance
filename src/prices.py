#!/usr/bin/env python3
"""
TÉLÉCHARGEMENT DES SÉRIES DE PRIX HISTORIQUES (YAHOO FINANCE)
-------------------------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry Béchu & Jean Jardel (Kanopy AM)
Module créé par Mohamed (Modif Mohamed) : toutes les lignes de ce fichier sont nouvelles.

Récupère via yfinance les cours de clôture ajustés (dividendes et divisions) :
    1. des titres du portefeuille final (data/portefeuille_final_pondere.csv, sortie de l'optimiseur)
    2. du benchmark MSCI World (ETF iShares Core MSCI World UCITS, IWDA.AS, coté en EUR)
puis les convertit en euros (devise de référence d'un fonds de droit français).
Le portefeuille final ne contient ni ticker Yahoo ni devise : on les retrouve dans data/all_data.csv.
Tout autre fichier de titres avec une colonne 'ticker' peut être passé à la place (par exemple l'univers
sélectionnable data/actifs_notre_secteur_healthtech_ai.csv, pour un optimiseur qui utiliserait la covariance).

Sorties (dossier data/prix/) :
    - prix_devise_locale.csv : cours ajustés en devise de cotation (une colonne par titre)
    - taux_de_change.csv     : taux EUR/devise utilisés pour la conversion (unités de devise pour 1 EUR)
    - prix_eur.csv           : cours convertis en EUR + colonne du benchmark MSCI World

Ces séries serviront au backtest historique (période avant 2024 et période de 2024 à aujourd'hui).
"""

import csv
import os
import sys

import pandas as pd
import yfinance as yf

# Devises cotées en sous-unités (pence, agorot, cents) : devise réelle et diviseur
MINOR_UNITS = {"GBp": ("GBP", 100.0), "GBX": ("GBP", 100.0), "ILA": ("ILS", 100.0), "ZAc": ("ZAR", 100.0)}

BENCHMARK_COLUMN = "BENCHMARK MSCI World (IWDA.AS)"


def resolve_project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) in ["src", "dossier_tri"]:
        return os.path.dirname(current_dir)
    return current_dir


class HistoricalPriceLoader:
    def __init__(self, all_data_csv, weighted_portfolio_csv, start_date="2015-01-01", end_date=None,
                 base_currency="EUR", benchmark_ticker="IWDA.AS", benchmark_currency="EUR", split_date="2024-01-01"):
        self.all_data_csv = all_data_csv
        self.weighted_portfolio_csv = weighted_portfolio_csv
        self.start_date = start_date
        self.end_date = end_date
        self.base_currency = base_currency
        self.benchmark_ticker = benchmark_ticker
        self.benchmark_currency = benchmark_currency
        self.split_date = split_date

        self.assets = []
        self.load_universe()

    def load_universe(self):
        """Charge les titres du portefeuille final, avec leur ticker Yahoo et leur devise lus dans all_data.csv."""
        with open(self.all_data_csv, 'r', encoding='utf-8') as f:
            reference = {r['ticker']: r for r in csv.DictReader(f)}

        with open(self.weighted_portfolio_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            raw_rows = list(reader)

        for r in raw_rows:
            ref = reference.get(r['ticker'], {})
            asset = dict(r, ticker_yahoo=(ref.get('ticker_yahoo') or '').strip(), currency=(ref.get('currency') or '').strip())
            if asset['ticker_yahoo']:
                self.assets.append(asset)
            else:
                print(f"[Prices] Attention : pas de ticker Yahoo pour {r.get('name')}, titre ignoré.")

        self.n = len(self.assets)
        self.yahoo_to_ticker = {r['ticker_yahoo']: r['ticker'] for r in self.assets}
        weight = sum(float(r.get('weight_decimal') or 0.0) for r in self.assets)
        weight_info = f", {weight:.1%} du poids" if weight > 0 else ""
        print(f"[Prices] Portefeuille chargé : {self.n} titres à télécharger{weight_info} (+ benchmark {self.benchmark_ticker}).")

    def download_prices(self):
        """Télécharge les cours de clôture ajustés (dividendes et divisions) des titres et du benchmark."""
        yahoo_tickers = list(self.yahoo_to_ticker) + [self.benchmark_ticker]
        data = yf.download(yahoo_tickers, start=self.start_date, end=self.end_date,
                           auto_adjust=True, progress=False, threads=True)
        closes = data["Close"].dropna(how="all").sort_index()

        missing = [t for t in yahoo_tickers if t not in closes.columns or closes[t].isna().all()]
        if missing:
            labels = {r['ticker_yahoo']: f"{r['name']} ({r['ticker_yahoo']}, poids {r.get('weight_percent') or 'n.d.'})"
                      for r in self.assets}
            print(f"[Prices] Attention : aucune donnée Yahoo pour {', '.join(labels.get(t, t) for t in missing)} "
                  f"(titre radié ou ticker inconnu, à traiter dans le backtest)")

        self.benchmark_local = closes[self.benchmark_ticker] if self.benchmark_ticker not in missing else None
        self.prices_local = closes[[t for t in self.yahoo_to_ticker if t not in missing]]
        print(f"[Prices] Cours téléchargés : {self.prices_local.shape[1]} titres, {len(self.prices_local)} séances "
              f"du {self.prices_local.index[0]:%d/%m/%Y} au {self.prices_local.index[-1]:%d/%m/%Y}.")
        return self.prices_local

    def download_fx_rates(self):
        """Télécharge les taux de change (unités de devise pour 1 EUR) nécessaires à la conversion."""
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
        """Exporte les séries de prix (devise locale, taux de change, EUR + benchmark) dans data/prix/."""
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


def run_prices():
    root_dir = resolve_project_root()
    possible_inputs_data = [
        os.path.join(root_dir, "data", "all_data.csv"),
        os.path.join(root_dir, "all_data.csv")
    ]
    all_data_file = next((p for p in possible_inputs_data if os.path.exists(p)), None)

    possible_inputs_pf = [
        os.path.join(root_dir, "data", "portefeuille_final_pondere.csv"),
        os.path.join(root_dir, "dossier_tri", "portefeuille_final_pondere.csv")
    ]
    pf_file = next((p for p in possible_inputs_pf if os.path.exists(p)), None)

    if not all_data_file or not pf_file:
        print("Erreur : Impossible de trouver all_data.csv ou portefeuille_final_pondere.csv (lancer d'abord run_pipeline.py)")
        sys.exit(1)

    output_dir = os.path.join(root_dir, "data", "prix")

    loader = HistoricalPriceLoader(all_data_file, pf_file, start_date="2015-01-01", base_currency="EUR",
                                   benchmark_ticker="IWDA.AS", benchmark_currency="EUR", split_date="2024-01-01")
    loader.download_prices()
    loader.download_fx_rates()
    loader.convert_to_base_currency()
    loader.export_prices(output_dir)

    rows, late_starts = loader.summarize()
    print("\n--- COUVERTURE DES SÉRIES DE PRIX (EN EUR) ---")
    for label, dates, n_days, n_assets in rows:
        print(f"{label:<20} | {dates:<26} | {n_days:>5} séances | {n_assets:>3} titres avec données")
    if late_starts:
        print("Historique plus court (cotation postérieure au début de la période) : "
              + ", ".join(f"{t} (depuis le {d})" for t, d in late_starts))


if __name__ == '__main__':
    run_prices()
