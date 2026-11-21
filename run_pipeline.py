#!/usr/bin/env python3
"""Exécute les quatre variantes de sélection/allocation, avec résultats isolés."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import time

import numpy as np
import pandas as pd

from src.run_tri import run_pipeline as run_tri_step
from src.optimizer import run_optimization, load_prices
from src.backtest import PortfolioBacktester, WalkForwardBacktester, run_comparison
from src.graphiques import COULEURS, tracer_diagnostics
from src.prices import BENCHMARK_COLUMN, run_prices

BASE_DIR = Path(__file__).resolve().parent
MODES = {
    'daphne_original': ('daphne', 'original', 'Daphné · origine'),
    'daphne_esg_risk': ('daphne', 'esg_risk', 'Daphné · risque ESG'),
    'mohamed_esg_risk': ('mohamed', 'esg_risk', 'Mohamed · risque ESG'),
    'thematique_recalibree': ('recalibree', 'te_div', 'A · Thématique recalibrée'),
}


def print_banner(text):
    print('\n' + '=' * 80 + '\n ' + text + '\n' + '=' * 80, flush=True)


def file_fingerprint(path):
    path = Path(path)
    return {'path': path.relative_to(BASE_DIR).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size}


def audit_prices(prices_path, tickers, output_path):
    """Contrôle le cache et expose les mouvements atypiques sans modifier les données."""
    prices = load_prices(prices_path)
    if prices.empty or not prices.index.is_unique or not prices.index.is_monotonic_increasing:
        raise ValueError('Cache vide, dates dupliquées ou non triées.')
    missing = set(tickers + [BENCHMARK_COLUMN]) - set(prices.columns)
    if missing:
        raise ValueError(f'Cache incomplet : {sorted(missing)}. Utiliser --refresh-prices.')
    values = prices[tickers + [BENCHMARK_COLUMN]]
    if (values <= 0).any().any() or np.isinf(values.to_numpy()).any():
        raise ValueError('Cache : cours non positifs ou non finis.')
    rows = []
    for ticker in values:
        series = values[ticker].dropna()
        if len(series) < 2:
            raise ValueError(f'Aucune donnée pour {ticker}.')
        returns = series.pct_change(fill_method=None).dropna()
        last = series.index[-1]
        gaps = values.loc[series.index[0]:, ticker].isna()
        longest_gap = int(gaps.groupby((~gaps).cumsum()).sum().max())
        rows.append({'ticker': ticker, 'premier_cours': str(series.index[0].date()),
                     'dernier_cours': str(last.date()), 'observations': len(series),
                     'lignes_sans_cotation': int(values[ticker].isna().sum()),
                     'plus_long_trou_seances': longest_gap,
                     'variation_max_abs': returns.abs().max(),
                     'date_variation_max': str(returns.abs().idxmax().date()),
                     'variation_signee': returns.loc[returns.abs().idxmax()],
                     'seances_depuis_dernier_cours': int((prices.index > last).sum())})
    audit = pd.DataFrame(rows)
    audit.to_csv(output_path, index=False, float_format='%.10f')
    if (audit['seances_depuis_dernier_cours'] > 10).any():
        raise ValueError('Un titre est sans cours récent depuis plus de dix séances; voir qualite_prix.csv.')
    print(f'Cache local : {len(prices)} dates, {len(tickers)} titres, '
          f'{prices.index[0]:%d/%m/%Y} au {prices.index[-1]:%d/%m/%Y}.')
    print(f"Mouvements quotidiens >25 % à examiner : {(audit['variation_max_abs'] > .25).sum()} séries (qualite_prix.csv).")
    return prices


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['all', *MODES], default='all')
    parser.add_argument('--refresh-prices', action='store_true', help='Retélécharger les prix et devises via Yahoo Finance.')
    parser.add_argument('--skip-history', action='store_true', help='Exécuter seulement la période postérieure à fin 2024.')
    args = parser.parse_args(argv)
    start = time.perf_counter()
    selected_modes = list(MODES) if args.mode == 'all' else [args.mode]
    source = BASE_DIR / 'data/raw/all_data.csv'
    sbti = BASE_DIR / 'data/raw/sbti/msci_world_jointure_sbti_2025-01-13.csv'
    prices_path = BASE_DIR / 'data/cache/prices/prix_eur.csv'
    output_dir = BASE_DIR / 'results'
    output_dir.mkdir(exist_ok=True)
    print_banner('SYNAPSE HEALTHTECH & AI : ' + ', '.join(selected_modes))
    print_banner('1 / 4 : SÉLECTION DES UNIVERS')
    selections = []
    for mode in selected_modes:
        directory = output_dir / mode
        directory.mkdir(exist_ok=True)
        run_tri_step(filter_mode=MODES[mode][0], input_path=source,
                     output_path=directory / 'actifs_selectionnes.csv', sbti_input_path=sbti)
        selections.append(pd.read_csv(directory / 'actifs_selectionnes.csv'))
    union = pd.concat(selections).drop_duplicates('ticker').sort_values('ticker')
    union_path = output_dir / 'univers_prix.csv'
    union.to_csv(union_path, index=False)
    print_banner('2 / 4 : COUVERTURE ET QUALITÉ DU CACHE DE PRIX')
    if args.refresh_prices:
        run_prices(source, union_path, output_dir=prices_path.parent)
    if not prices_path.exists():
        raise FileNotFoundError('Cache absent : lancer avec --refresh-prices pour télécharger les cours.')
    prices = audit_prices(prices_path, list(union['ticker']), output_dir / 'qualite_prix.csv')
    print_banner('3 / 4 : ALLOCATION ET BACKTEST PAR MODE')
    for mode in selected_modes:
        _, optimizer_mode, label = MODES[mode]
        directory = output_dir / mode
        print_banner(label)
        universe = directory / 'actifs_selectionnes.csv'
        portfolio = directory / 'portefeuille_final_pondere.csv'
        run_optimization(optimizer_mode=optimizer_mode, input_path=universe,
                         output_path=portfolio, prices_path=prices_path,
                         diagnostics_path=directory / 'diagnostics_optimisation.json')
        PortfolioBacktester(source, portfolio).run_and_compare(directory / 'indicateurs_esg.csv')
        WalkForwardBacktester(universe, portfolio, prices_path, optimizer_mode=optimizer_mode).run_and_compare(
            directory, label, COULEURS[mode], skip_history=args.skip_history)
    print_banner('4 / 4 : COMPARAISONS ET GRAPHIQUES')
    modes = [(mode, MODES[mode][2]) for mode in selected_modes]
    rows = run_comparison(modes, output_dir, skip_history=args.skip_history)
    tracer_diagnostics(modes, output_dir)
    manifest = {
        'execution_utc': datetime.now(timezone.utc).isoformat(),
        'modes': selected_modes, 'skip_history': args.skip_history, 'refresh_prices': args.refresh_prices,
        'date_constitution': '2024-12-31', 'cache_debut': str(prices.index[0].date()),
        'cache_fin': str(prices.index[-1].date()), 'fenetre_covariance_semaines': 156,
        'rebalancement_historique': 'trimestriel',
        'rebalancement_post_2024': 'poids figés (hors_echantillon) et trimestriel (hors_echantillon_rebalance)',
        'mode_thematique_recalibree': {'plafond_par_sous_secteur': 0.12, 'intensite_carbone_max_vs_msci': 0.5,
                                       'sous_secteur': 'gics_sector_name | industry_group (all_data.csv)'},
        'frais_sur_montant_echange': 0.001,
        'taux_sans_risque_annuel': 0.02,
        'sources': [file_fingerprint(path) for path in (source, sbti, prices_path,
                    prices_path.with_name('prix_devise_locale.csv'), prices_path.with_name('taux_de_change.csv'))],
        'versions': {name: version(name) for name in ('numpy', 'pandas', 'scipy', 'scikit-learn', 'matplotlib', 'yfinance')},
        'limites': ['Univers et scores ESG figés fin 2024 : historique rétrospectif avec biais de sélection/survivance.',
                    'Période post-2024 à poids figés; filtres choisis a posteriori, pas une validation prospective.',
                    'Gestion active post-2024 : réoptimisation trimestrielle sur les cours connus, univers et ESG figés fin 2024.',
                    'Mode thematique_recalibree conçu après une recherche sur 2018-2026 : le choix des règles a vu la période post-2024.',
                    'SBTi : photographie du 13/01/2025, validation au cutoff seulement si confirmée par la source.',
                    'Cours ajustés du cache fournis, mouvements atypiques non corrigés arbitrairement.',
                    'Pas de frais de gestion ni de frais de constitution du portefeuille.'],
    }
    (output_dir / 'execution.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(pd.DataFrame(rows)[['Période', 'Portefeuille', 'Rendement annualisé', 'Volatilité', 'Sharpe (Rf 2%)']].to_string(index=False))
    print_banner(f'EXÉCUTION TERMINÉE EN {time.perf_counter() - start:.1f} S — résultats : {output_dir}')
    return rows


if __name__ == '__main__':
    main()
