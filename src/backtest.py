"""Photographie ESG et backtest sur cours ajustés EUR.

L'univers et les scores ESG restent ceux de fin 2024 : l'historique est
rétrospectif, même lorsque les entrées de marché sont réestimées à chaque date.
Après 2024, deux lectures : poids figés à la constitution (``hors_echantillon``)
et gestion active avec réoptimisation trimestrielle sur les seuls cours connus
à chaque date (``hors_echantillon_rebalance``).
"""

import csv
import math
from pathlib import Path

import numpy as np
import pandas as pd

from src.optimizer import (PedersenPortfolioOptimizer, ESGRiskBudgetingOptimizer, TrackingDiversificationOptimizer,
                           load_prices)
from src.prices import BENCHMARK_COLUMN
from src.graphiques import tracer_performances, COULEURS

MOIS_COLONNES = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
PERIODES = {
    'historique': ('Historique rétrospectif', 'Réoptimisation trimestrielle, frais de transaction 10 pb · univers et ESG figés fin 2024'),
    'hors_echantillon': ('Depuis fin 2024', 'Poids fin 2024 conservés · cours ajustés en EUR · aucun rebalancement'),
    'hors_echantillon_rebalance': ('Depuis fin 2024, gestion active',
                                   'Réoptimisation trimestrielle avec les seuls cours connus · frais 10 pb · univers et ESG figés fin 2024'),
}


def monthly_returns(values):
    """Rendements mensuels d'une valorisation ; le premier mois part de la date initiale.

    Une série qui démarre le dernier jour coté d'un mois (31/12/2024, 29/12/2017) prend ce
    mois comme base ; une série qui démarre en cours de mois compte ce mois partiel.
    """
    values = values.dropna()
    month_end = values.resample('ME').last()
    month_end.index = month_end.index.to_period('M')
    first_month = values.index[0].to_period('M')
    if values.index[0] < values[values.index.to_period('M') == first_month].index[-1]:
        month_end = pd.concat([pd.Series([values.iloc[0]], index=[first_month - 1]), month_end])
    return month_end.pct_change(fill_method=None).dropna()


def monthly_table(series, period):
    """Tableau année x mois, avec la performance de l'année (mois composés)."""
    rows = []
    for name, values in series.items():
        returns = monthly_returns(values)
        for year, group in returns.groupby(returns.index.year):
            row = {'Période': period, 'Série': name, 'Année': year}
            row.update({MOIS_COLONNES[p.month - 1]: r for p, r in group.items()})
            row['Année complète'] = float(np.prod(1 + group.values) - 1)
            rows.append(row)
    return pd.DataFrame(rows, columns=['Période', 'Série', 'Année', *MOIS_COLONNES, 'Année complète'])


def compute_metrics(values, bench, rf_rate=0.02):
    """CAGR calendaire, risque hebdomadaire et drawdown quotidien, dates communes."""
    pair = pd.concat([values.rename('fonds'), bench.rename('indice')], axis=1).dropna()
    if len(pair) < 3 or not np.isfinite(pair.to_numpy()).all() or (pair <= 0).any().any():
        raise ValueError('Au moins trois valorisations positives communes sont nécessaires.')
    v, b = pair['fonds'] / pair['fonds'].iloc[0], pair['indice'] / pair['indice'].iloc[0]
    years = (pair.index[-1] - pair.index[0]).days / 365.25
    ann, ann_b = v.iloc[-1] ** (1 / years) - 1, b.iloc[-1] ** (1 / years) - 1
    weekly = pair.resample('W-FRI').last()
    weekly = weekly.loc[weekly.index <= pair.index[-1]].pct_change(fill_method=None).dropna()
    rw, rb = weekly['fonds'], weekly['indice']
    vol, te = rw.std() * math.sqrt(52), (rw - rb).std() * math.sqrt(52)
    return {'Perf. cumulée': float(v.iloc[-1] - 1), 'Rendement annualisé': float(ann),
            'Volatilité': float(vol), 'Sharpe (Rf 2%)': float((ann - rf_rate) / vol) if vol > 0 else np.nan,
            'Perte maximale': float((v / v.cummax() - 1).min()), 'Tracking error': float(te),
            "Ratio d'information": float((ann - ann_b) / te) if te > 1e-9 else np.nan,
            'Bêta': float(rw.cov(rb) / rb.var()) if rb.var() > 0 else np.nan}


def format_metrics(metrics):
    result = {}
    percentage = {'Perf. cumulée', 'Rendement annualisé', 'Volatilité', 'Perte maximale',
                  'Tracking error', 'Rotation annuelle'}
    for key, value in metrics.items():
        if isinstance(value, str):
            result[key] = value
        elif value is None or not np.isfinite(value):
            result[key] = '-'
        else:
            result[key] = f'{value:.2%}' if key in percentage else f'{value:.3f}'
    return result


class PortfolioBacktester:
    """Photographie ESG pondérée; performances mesurées séparément sur les cours."""

    FIELDS = {
        'ITR (°C)': ('ITR',),
        'Intensité carbone Scope 1+2': ('INTENSITY_SCOPE_1', 'INTENSITY_SCOPE_2'),
        'Intensité carbone Scope 1+2+3': ('INTENSITY_SCOPE_1', 'INTENSITY_SCOPE_2', 'INTENSITY_SCOPE_3'),
        'Empreinte carbone Scope 1+2+3': ('FOOTPRINT_SCOPE_1', 'FOOTPRINT_SCOPE_2', 'FOOTPRINT_SCOPE_3'),
        'ODD 3': ('SDG_03_NET_ALIGNMENT_SCORE',), 'ODD 9': ('SDG_09_NET_ALIGNMENT_SCORE',),
        'Gouvernance /10': ('GOVERNANCE_PILLAR_SCORE',),
        'Revenus Taxonomie UE max (%)': ('EST_EU_TAXONOMY_MAX_REV',),
    }

    def __init__(self, all_data_csv, weighted_portfolio_csv, rf_rate=0.02):
        self.data = pd.read_csv(all_data_csv).set_index('ticker')
        self.portfolio = pd.read_csv(weighted_portfolio_csv).set_index('ticker')
        self.weights = self.portfolio['weight_decimal']
        if (not self.weights.index.is_unique or not np.isfinite(self.weights).all()
                or (self.weights < 0).any() or not np.isclose(self.weights.sum(), 1, atol=1e-6)):
            raise ValueError('Poids invalides : doublon, valeur non finie, poids négatif ou somme différente de 1.')

    def run_and_compare(self, output_csv_path):
        benchmark = pd.to_numeric(self.data['Weight in MSCI World'], errors='coerce').fillna(0)
        benchmark /= benchmark.sum()
        weights = {'fonds': self.weights,
                   'equipondere': pd.Series(1 / len(self.weights), index=self.weights.index),
                   'msci_world': benchmark}
        rows = []
        for label, w in weights.items():
            for metric, fields in self.FIELDS.items():
                vals = self.data.loc[w.index, list(fields)].apply(pd.to_numeric, errors='coerce').sum(axis=1, min_count=len(fields))
                valid = vals.notna()
                coverage = w.loc[valid].sum()
                value = (w.loc[valid] * vals.loc[valid]).sum() / coverage if coverage > 0 else np.nan
                rows.append({'Portefeuille': label, 'Indicateur': metric, 'Valeur': value,
                             'Couverture poids': coverage})
        pd.DataFrame(rows).to_csv(output_csv_path, index=False, float_format='%.10f')
        sector = pd.DataFrame({'secteur': self.data.loc[self.weights.index, 'gics_sector_name'],
                               'poids': self.weights}).groupby('secteur')['poids'].sum()
        sector.to_csv(Path(output_csv_path).with_name('allocation_sectorielle.csv'))
        # Sous-secteur = secteur GICS + industry_group, comme le plafond de la stratégie A.
        labels = (self.data.loc[self.weights.index, 'gics_sector_name'] + ' | '
                  + self.data.loc[self.weights.index, 'industry_group'])
        pd.DataFrame({'sous_secteur': labels, 'poids': self.weights}).groupby('sous_secteur')['poids'].sum() \
            .sort_values(ascending=False).to_csv(Path(output_csv_path).with_name('allocation_sous_secteurs.csv'))
        return rows


class WalkForwardBacktester:
    """Trimestriel 2018-2024 puis poids fin 2024 conservés.

    Frais de 10 pb par montant acheté/vendu, hors investissement initial;
    pas de frais de gestion. Aucun remplissage antérieur à l'introduction.
    """

    def __init__(self, universe_csv, weighted_portfolio_csv, prices_csv, optimizer_mode='esg_risk',
                 split_date='2024-12-31', first_rebalance='2017-12-29', window_weeks=156,
                 rf_rate=0.02, cost=0.0010):
        self.universe_csv = universe_csv
        self.weighted_portfolio_csv = weighted_portfolio_csv
        self.optimizer_mode = optimizer_mode
        if optimizer_mode not in ('original', 'esg_risk', 'te_div'):
            raise ValueError(f'Optimiseur inconnu : {optimizer_mode}')
        self.split_date, self.first_rebalance = pd.Timestamp(split_date), pd.Timestamp(first_rebalance)
        self.window_weeks, self.rf_rate, self.cost = window_weeks, rf_rate, cost
        with open(universe_csv, encoding='utf-8-sig', newline='') as f:
            self.universe_rows = list(csv.DictReader(f))
        px = load_prices(prices_csv)
        self.tickers = [r['ticker'] for r in self.universe_rows]
        missing = set(self.tickers + [BENCHMARK_COLUMN]) - set(px.columns)
        if missing:
            raise ValueError(f'Cours manquants dans le cache : {sorted(missing)}')
        self.prices = px[self.tickers]
        self.prices_val = self.prices.ffill()
        self.bench = px[BENCHMARK_COLUMN].ffill()
        self.last_date = px.index[-1]
        self.start_oos = px.index[px.index <= self.split_date][-1]
        if self.last_date <= self.split_date:
            raise ValueError('Le cache ne couvre pas la période postérieure à fin 2024.')
        self.rebalance_audit, self.weight_history = [], []

    def rebalance_dates(self):
        idx = self.prices.loc[:self.start_oos].index
        dates = pd.Series(idx, index=idx).groupby(idx.to_period('Q')).max()
        return [pd.Timestamp(d) for d in dates if self.first_rebalance <= d < self.start_oos]

    def available_tickers(self, date):
        p = self.prices.loc[:date].ffill(limit=10).resample('W-FRI').last()
        returns = p.loc[p.index <= date].pct_change(fill_method=None).iloc[1:].tail(self.window_weeks)
        if len(returns) < self.window_weeks:
            raise ValueError(f'Historique inférieur à {self.window_weeks} semaines au {date}.')
        return [t for t in self.tickers if returns[t].notna().all()]

    def pedersen_market_inputs(self, date, tickers):
        p = self.prices.loc[date - pd.DateOffset(years=5):date].ffill()
        inputs = {}
        for ticker in tickers:
            series = p[ticker].dropna()
            years = (series.index[-1] - series.index[0]).days / 365.25
            weekly = series.resample('W-FRI').last()
            vol = weekly.loc[weekly.index <= date].pct_change(fill_method=None).std() * math.sqrt(52)
            inputs[ticker] = ((series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1, vol)
        return inputs

    def weights_at(self, date):
        tickers = self.available_tickers(date)
        rows = [r for r in self.universe_rows if r['ticker'] in tickers]
        if self.optimizer_mode == 'original':
            optimizer = PedersenPortfolioOptimizer(None, rows=rows,
                market_inputs=self.pedersen_market_inputs(date, tickers), verbose=False)
        elif self.optimizer_mode == 'te_div':
            optimizer = TrackingDiversificationOptimizer(None, prices=self.prices, benchmark=self.bench, as_of=date,
                window_weeks=self.window_weeks, rows=rows, verbose=False)
        else:
            optimizer = ESGRiskBudgetingOptimizer(None, prices=self.prices, as_of=date,
                window_weeks=self.window_weeks, rows=rows, verbose=False)
        optimizer.optimize()
        weights = pd.Series(optimizer.weights, index=[r['ticker'] for r in optimizer.assets])
        self.rebalance_audit.append({'date': str(date.date()), 'titres_disponibles': len(weights),
                                     'titres_investis': int((weights > 1e-8).sum()),
                                     'titres_sans_historique': '|'.join(sorted(set(self.tickers) - set(weights.index))),
                                     'poids_total': weights.sum(), 'poids_max': weights.max(),
                                     'poids_sante': optimizer.report['Santé'],
                                     'poids_tech': optimizer.report['Tech'], 'itr': optimizer.report['ITR'],
                                     'depassement_max_contraintes': optimizer.report['Dépassement']})
        self.weight_history.append(weights.rename(date))
        return weights

    def simulate(self, weights_by_date, end):
        """Nombre de parts constant entre rebalancements; frais aux dates de transaction."""
        dates = sorted(weights_by_date)
        if not dates or dates[-1] >= end:
            raise ValueError('Calendrier vide ou sans période de détention.')
        pieces, value, turnover, previous = [], 1.0, [], None
        for k, date in enumerate(dates):
            nxt = dates[k + 1] if k + 1 < len(dates) else end
            weights = weights_by_date[date]
            if (not weights.index.is_unique or not np.isfinite(weights).all()
                    or not np.isclose(weights.sum(), 1, atol=1e-6) or (weights < -1e-9).any()):
                raise ValueError(f'Poids invalides au {date}.')
            weights = weights[weights > 1e-10]
            prices = self.prices_val.loc[date:nxt, weights.index]
            if prices.isna().any().any() or (prices <= 0).any().any():
                raise ValueError(f'Valorisation impossible au {date}.')
            if previous is not None:
                drift = previous * self.prices_val.loc[date, previous.index] / value
                idx = drift.index.union(weights.index)
                traded = (weights.reindex(idx, fill_value=0) - drift.reindex(idx, fill_value=0)).abs().sum()
                turnover.append(traded / 2)
                value *= 1 - self.cost * traded
            shares = value * weights / prices.iloc[0]
            segment = prices.mul(shares, axis=1).sum(axis=1)
            pieces.append(segment if k == len(dates) - 1 else segment.iloc[:-1])
            value, previous = segment.iloc[-1], shares
        return pd.concat(pieces), turnover

    def run_historique(self):
        weights = {date: self.weights_at(date) for date in self.rebalance_dates()}
        equal = {date: pd.Series(1 / len(w), index=w.index) for date, w in weights.items()}
        fund, rotation = self.simulate(weights, self.start_oos)
        ew, ew_rotation = self.simulate(equal, self.start_oos)
        bench = self.bench.loc[fund.index]
        years = (fund.index[-1] - fund.index[0]).days / 365.25
        return {'fonds': fund, 'equipondere': ew, 'msci_world': bench / bench.iloc[0]}, {
            'fonds': sum(rotation) / years, 'equipondere': sum(ew_rotation) / years}

    def run_hors_echantillon(self):
        weights = pd.read_csv(self.weighted_portfolio_csv).set_index('ticker')['weight_decimal']
        if set(weights.index) - set(self.tickers):
            raise ValueError('Portefeuille et univers incohérents.')
        equal = pd.Series(1 / len(self.tickers), index=self.tickers)
        fund, _ = self.simulate({self.start_oos: weights}, self.last_date)
        ew, _ = self.simulate({self.start_oos: equal}, self.last_date)
        bench = self.bench.loc[fund.index]
        return {'fonds': fund, 'equipondere': ew, 'msci_world': bench / bench.iloc[0]}

    def run_hors_echantillon_rebalance(self):
        """Gestion active après 2024 : poids de constitution, puis réoptimisation à chaque fin de
        trimestre avec les seuls cours connus à la date. Univers et scores ESG restent ceux de fin 2024."""
        initial = pd.read_csv(self.weighted_portfolio_csv).set_index('ticker')['weight_decimal']
        if set(initial.index) - set(self.tickers):
            raise ValueError('Portefeuille et univers incohérents.')
        idx = self.prices.loc[self.start_oos:].index
        ends = pd.Series(idx, index=idx).groupby(idx.to_period('Q')).max()
        dates = [pd.Timestamp(d) for d in ends if self.start_oos < d < self.last_date]
        n_audit, n_history = len(self.rebalance_audit), len(self.weight_history)
        weights = {self.start_oos: initial}
        equal = {self.start_oos: pd.Series(1 / len(self.tickers), index=self.tickers)}
        for date in dates:
            weights[date] = self.weights_at(date)
            equal[date] = pd.Series(1 / len(weights[date]), index=weights[date].index)
        # Audits de cette période exportés à part : ceux de l'historique restent inchangés.
        self.post2024_audit = self.rebalance_audit[n_audit:]
        self.post2024_weights = [initial.rename(self.start_oos)] + self.weight_history[n_history:]
        del self.rebalance_audit[n_audit:]
        del self.weight_history[n_history:]
        fund, rotation = self.simulate(weights, self.last_date)
        ew, ew_rotation = self.simulate(equal, self.last_date)
        years = (fund.index[-1] - fund.index[0]).days / 365.25
        bench = self.bench.loc[fund.index]
        return ({'fonds': fund, 'equipondere': ew, 'msci_world': bench / bench.iloc[0]},
                {'fonds': sum(rotation) / years, 'equipondere': sum(ew_rotation) / years})

    def export_attribution(self, output_dir, baseline):
        """Contributions exactes à la performance d'un portefeuille sans rebalancement."""
        weights = pd.read_csv(self.weighted_portfolio_csv).set_index('ticker')['weight_decimal']
        start = self.prices_val.loc[self.start_oos, weights.index]
        end = self.prices_val.loc[self.last_date, weights.index]
        asset_return = end / start - 1
        contributions = weights * asset_return
        total_value = (weights * (1 + asset_return)).sum()
        attribution = pd.DataFrame({'poids_initial': weights, 'rendement_titre_eur': asset_return,
            'contribution_performance': contributions,
            'poids_final': weights * (1 + asset_return) / total_value})
        attribution.sort_values('contribution_performance', ascending=False).to_csv(
            Path(output_dir) / 'attribution_post2024.csv', index_label='ticker', float_format='%.10f')
        if not np.isclose(contributions.sum(), baseline.iloc[-1] / baseline.iloc[0] - 1, atol=1e-8):
            raise RuntimeError('Les contributions ne correspondent pas à la performance du portefeuille.')
        # Sensibilité explicite, sans modifier le cours téléchargé ni la simulation principale.
        ticker = 'PTC US Equity'
        if ticker in weights.index:
            reduced = weights.drop(ticker)
            reduced /= reduced.sum()
            scenario, _ = self.simulate({self.start_oos: reduced}, self.last_date)
            rows = []
            for label, values in [('portefeuille_complet', baseline), ('sans_ptc_poids_renormalises', scenario)]:
                rows.append({'scenario': label, 'poids_ptc_initial': weights[ticker],
                             **compute_metrics(values, self.bench)})
            pd.DataFrame(rows).to_csv(Path(output_dir) / 'sensibilite_ptc.csv', index=False, float_format='%.10f')

    def run_and_compare(self, output_dir, label, color, skip_history=False):
        output_dir = Path(output_dir)
        graph_dir = output_dir / 'graphiques'
        graph_dir.mkdir(parents=True, exist_ok=True)
        periods = []
        if not skip_history:
            history, turnover = self.run_historique()
            periods.append(('historique', history, turnover))
            pd.DataFrame(self.rebalance_audit).to_csv(output_dir / 'audit_rebalancements.csv', index=False)
            pd.DataFrame(self.weight_history).fillna(0).to_csv(output_dir / 'poids_historiques.csv', index_label='date')
        recent = self.run_hors_echantillon()
        self.export_attribution(output_dir, recent['fonds'])
        periods.append(('hors_echantillon', recent, {}))
        active, active_turnover = self.run_hors_echantillon_rebalance()
        periods.append(('hors_echantillon_rebalance', active, active_turnover))
        pd.DataFrame(self.post2024_audit).to_csv(output_dir / 'audit_rebalancements_post2024.csv', index=False)
        pd.DataFrame(self.post2024_weights).fillna(0).to_csv(output_dir / 'poids_post2024_rebalance.csv', index_label='date')
        rows, monthly = [], []
        names = {'fonds': label, 'equipondere': 'Équipondéré (1/N)', 'msci_world': 'MSCI World (IWDA)'}
        for period, series, turnover in periods:
            for key, values in series.items():
                rows.append({'Période': period, 'Portefeuille': names[key], 'strategie': key,
                    'Début': str(values.index[0].date()), 'Fin': str(values.index[-1].date()),
                    **compute_metrics(values, series['msci_world'], self.rf_rate),
                    'Rotation annuelle': turnover.get(key, 0.0)})
            pd.DataFrame(series).to_csv(output_dir / f'performances_{period}.csv', index_label='date', float_format='%.10f')
            monthly.append(monthly_table({names[k]: v for k, v in series.items()}, period))
            title, subtitle = PERIODES[period]
            tracer_performances([(label, series['fonds'], color, 2.4),
                ('Équipondéré', series['equipondere'], COULEURS['equipondere'], 2.0),
                ('MSCI World', series['msci_world'], COULEURS['msci_world'], 1.6)],
                f'{title} : {label}', subtitle, graph_dir / f'{period}.png')
        pd.concat(monthly).to_csv(output_dir / 'performances_mensuelles.csv', index=False, float_format='%.10f')
        frame = pd.DataFrame(rows)
        frame.to_csv(output_dir / 'metriques_backtest.csv', index=False, float_format='%.10f')
        print(frame[['Période', 'Portefeuille', 'Rendement annualisé', 'Volatilité', 'Sharpe (Rf 2%)']].to_string(index=False))
        return rows


def run_comparison(modes, output_dir, skip_history=False):
    """Compare les exécutions demandées, sur leur intersection de dates."""
    output_dir = Path(output_dir)
    (output_dir / 'graphiques').mkdir(parents=True, exist_ok=True)
    rows, monthly = [], []
    periods = ['hors_echantillon', 'hors_echantillon_rebalance']
    for period in (periods if skip_history else ['historique', *periods]):
        frames = {mode: pd.read_csv(output_dir / mode / f'performances_{period}.csv', index_col=0,
                                    parse_dates=True) for mode, _ in modes}
        common = None
        for frame in frames.values():
            common = frame.index if common is None else common.intersection(frame.index)
        bench = next(iter(frames.values())).loc[common, 'msci_world']
        bench = bench / bench.iloc[0]
        curves, by_label = [], {}
        for mode, label in modes:
            series = frames[mode].loc[common, 'fonds']
            series = series / series.iloc[0]
            rows.append({'mode': mode, 'Période': period, 'Portefeuille': label,
                         'Début': str(common[0].date()), 'Fin': str(common[-1].date()),
                         **compute_metrics(series, bench)})
            curves.append((label, series, COULEURS[mode], 2.2))
            by_label[label] = monthly_returns(series)
        rows.append({'mode': 'msci_world', 'Période': period, 'Portefeuille': 'MSCI World (IWDA)',
                     'Début': str(common[0].date()), 'Fin': str(common[-1].date()),
                     **compute_metrics(bench, bench)})
        curves.append(('MSCI World', bench, COULEURS['msci_world'], 1.6))
        by_label['MSCI World (IWDA)'] = monthly_returns(bench)
        table = pd.DataFrame(by_label)
        table.insert(0, 'Mois', table.index.astype(str))
        table.insert(0, 'Période', period)
        monthly.append(table)
        title = PERIODES[period][0].lower()
        tracer_performances(curves, f'Comparaison des modes : {title}',
            'Cours ajustés en EUR · mêmes dates · univers et scores ESG sélectionnés fin 2024',
            output_dir / 'graphiques' / f'comparaison_{period}.png')
    pd.DataFrame(rows).to_csv(output_dir / 'comparaison_modes.csv', index=False, float_format='%.10f')
    pd.concat(monthly).to_csv(output_dir / 'performances_mensuelles_modes.csv', index=False, float_format='%.10f')
    return rows
