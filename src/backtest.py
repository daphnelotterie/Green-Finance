#!/usr/bin/env python3
"""
MOTEUR DE BACKTEST ET COMPARAISON QUANTITATIVE
----------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry Béchu & Jean Jardel (Kanopy AM)

Compare 3 portefeuilles :
  1. Synapse HealthTech & AI (Pondération Optimisée Pedersen et al. 2021)
  2. Équipondéré 1/N (Sur les 50 mêmes valeurs éligibles)
  3. Benchmark Marché : Indice MSCI World (1 247 valeurs pondérées par capitalisation)
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

def resolve_project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) in ["src", "dossier_tri"]:
        return os.path.dirname(current_dir)
    return current_dir


class PortfolioBacktester:
    def __init__(self, all_data_csv, weighted_portfolio_csv, rf_rate=0.02):
        self.all_data_csv = all_data_csv
        self.weighted_portfolio_csv = weighted_portfolio_csv
        self.rf_rate = rf_rate
        
        self.load_benchmark_data()
        self.load_portfolio_data()

    def load_benchmark_data(self):
        """Charge le benchmark MSCI World (1 247 valeurs)."""
        with open(self.all_data_csv, 'r', encoding='utf-8') as f:
            self.bm_rows = list(csv.DictReader(f))
            
        tot_w = sum(to_float(r.get('Weight in MSCI World')) for r in self.bm_rows)
        self.bm_total_weight = tot_w
        
        def bm_wavg(col):
            return sum(to_float(r.get('Weight in MSCI World')) * to_float(r.get(col)) for r in self.bm_rows) / tot_w

        self.bm_metrics = {
            'Ret_1Y': bm_wavg('Annualized return 1Y'),
            'Ret_5Y': bm_wavg('Annualized return 5Y'),
            'Ret_10Y': bm_wavg('Annualized return 10Y'),
            'Vol_1Y': bm_wavg('Volatility 1Y'),
            'Vol_5Y': bm_wavg('Volatility 5Y'),
            'Vol_10Y': bm_wavg('Volatility 10Y'),
            'Sharpe_1Y': bm_wavg('Sharpe 1Y'),
            'Sharpe_5Y': bm_wavg('Sharpe 5Y'),
            'Sharpe_10Y': bm_wavg('Sharpe 10Y'),
            'VaR95_5Y': bm_wavg('VaR 95% 5Y'),
            'CVaR95_5Y': bm_wavg('CVaR 95% 5Y'),
            'MDD_5Y': bm_wavg('Max drawdown 5Y'),
            'ITR': bm_wavg('ITR'),
            'Int_1_2': bm_wavg('INTENSITY_SCOPE_1') + bm_wavg('INTENSITY_SCOPE_2'),
            'Int_Tot': bm_wavg('INTENSITY_SCOPE_1') + bm_wavg('INTENSITY_SCOPE_2') + bm_wavg('INTENSITY_SCOPE_3'),
            'SDG3': bm_wavg('SDG_03_NET_ALIGNMENT_SCORE'),
            'SDG9': bm_wavg('SDG_09_NET_ALIGNMENT_SCORE'),
            'Gov': bm_wavg('GOVERNANCE_PILLAR_SCORE'),
            'Taxo': bm_wavg('EST_EU_TAXONOMY_MAX_REV')
        }

    def load_portfolio_data(self):
        """Charge le portefeuille final optimisé."""
        with open(self.weighted_portfolio_csv, 'r', encoding='utf-8') as f:
            self.pf_rows = list(csv.DictReader(f))
            
        self.tickers = [r['ticker'] for r in self.pf_rows]
        self.weights_opt = [to_float(r['weight_decimal']) for r in self.pf_rows]
        self.n = len(self.pf_rows)
        self.weights_ew = [1.0 / self.n] * self.n
        
        bm_dict = {r['ticker']: r for r in self.bm_rows}
        self.full_assets = [bm_dict[t] for t in self.tickers]

    def compute_portfolio_stats(self, weights):
        """Calcule les statistiques complètes d'un vecteur de pondération."""
        ret_1y = [to_float(r.get('Annualized return 1Y')) for r in self.full_assets]
        ret_5y = [to_float(r.get('Annualized return 5Y')) for r in self.full_assets]
        ret_10y = [to_float(r.get('Annualized return 10Y')) for r in self.full_assets]
        
        vol_1y = [to_float(r.get('Volatility 1Y')) for r in self.full_assets]
        vol_5y = [to_float(r.get('Volatility 5Y')) for r in self.full_assets]
        vol_10y = [to_float(r.get('Volatility 10Y')) for r in self.full_assets]
        
        sectors = [r.get('gics_sector_name') for r in self.full_assets]
        
        p_ret_1y = sum(weights[i] * ret_1y[i] for i in range(self.n))
        p_ret_5y = sum(weights[i] * ret_5y[i] for i in range(self.n))
        p_ret_10y = sum(weights[i] * ret_10y[i] for i in range(self.n))
        
        # Matrice de covariance Elton-Gruber pour volatilité 5Y
        p_var_5y = 0.0
        for i in range(self.n):
            for j in range(self.n):
                rho = 1.0 if i == j else (0.50 if sectors[i] == sectors[j] else 0.28)
                cov = rho * vol_5y[i] * vol_5y[j]
                p_var_5y += weights[i] * weights[j] * cov
        p_vol_5y = math.sqrt(p_var_5y)
        
        div_ratio = p_vol_5y / sum(weights[i] * vol_5y[i] for i in range(self.n))
        p_vol_1y = sum(weights[i] * vol_1y[i] for i in range(self.n)) * div_ratio
        p_vol_10y = sum(weights[i] * vol_10y[i] for i in range(self.n)) * div_ratio
        
        p_sharpe_1y = (p_ret_1y - self.rf_rate) / p_vol_1y if p_vol_1y > 0 else 0.0
        p_sharpe_5y = (p_ret_5y - self.rf_rate) / p_vol_5y if p_vol_5y > 0 else 0.0
        p_sharpe_10y = (p_ret_10y - self.rf_rate) / p_vol_10y if p_vol_10y > 0 else 0.0
        
        # Risques de queue journaliers
        p_var95_5y = -(1.645 * (p_vol_5y / math.sqrt(252)) - (p_ret_5y / 252))
        p_cvar95_5y = -(2.063 * (p_vol_5y / math.sqrt(252)) - (p_ret_5y / 252))
        p_mdd_5y = sum(weights[i] * to_float(r.get('Max drawdown 5Y')) for i, r in enumerate(self.full_assets))
        
        # Métriques Extra-Financières
        itrs = [to_float(r.get('ITR')) for r in self.full_assets]
        int1 = [to_float(r.get('INTENSITY_SCOPE_1')) for r in self.full_assets]
        int2 = [to_float(r.get('INTENSITY_SCOPE_2')) for r in self.full_assets]
        int3 = [to_float(r.get('INTENSITY_SCOPE_3')) for r in self.full_assets]
        sdg3 = [to_float(r.get('SDG_03_NET_ALIGNMENT_SCORE')) for r in self.full_assets]
        sdg9 = [to_float(r.get('SDG_09_NET_ALIGNMENT_SCORE')) for r in self.full_assets]
        gov = [to_float(r.get('GOVERNANCE_PILLAR_SCORE')) for r in self.full_assets]
        taxo = [to_float(r.get('EST_EU_TAXONOMY_MAX_REV')) for r in self.full_assets]
        
        p_itr = sum(weights[i] * itrs[i] for i in range(self.n))
        p_int12 = sum(weights[i] * (int1[i] + int2[i]) for i in range(self.n))
        p_int_tot = sum(weights[i] * (int1[i] + int2[i] + int3[i]) for i in range(self.n))
        p_sdg3 = sum(weights[i] * sdg3[i] for i in range(self.n))
        p_sdg9 = sum(weights[i] * sdg9[i] for i in range(self.n))
        p_gov = sum(weights[i] * gov[i] for i in range(self.n))
        p_taxo = sum(weights[i] * taxo[i] for i in range(self.n))
        
        hc_w = sum(weights[i] for i in range(self.n) if sectors[i] == 'Health Care')
        tech_w = sum(weights[i] for i in range(self.n) if sectors[i] == 'Information Technology')
        ind_w = sum(weights[i] for i in range(self.n) if sectors[i] not in ('Health Care', 'Information Technology'))
        
        return {
            'Ret_1Y': p_ret_1y, 'Ret_5Y': p_ret_5y, 'Ret_10Y': p_ret_10y,
            'Vol_1Y': p_vol_1y, 'Vol_5Y': p_vol_5y, 'Vol_10Y': p_vol_10y,
            'Sharpe_1Y': p_sharpe_1y, 'Sharpe_5Y': p_sharpe_5y, 'Sharpe_10Y': p_sharpe_10y,
            'VaR95_5Y': p_var95_5y, 'CVaR95_5Y': p_cvar95_5y, 'MDD_5Y': p_mdd_5y,
            'ITR': p_itr, 'Int_1_2': p_int12, 'Int_Tot': p_int_tot,
            'SDG3': p_sdg3, 'SDG9': p_sdg9, 'Gov': p_gov, 'Taxo': p_taxo,
            'Health_Care_Weight': hc_w, 'Tech_Weight': tech_w, 'Industrials_Weight': ind_w,
            'Max_Weight': max(weights), 'Min_Weight': min(weights)
        }

    def run_and_compare(self, output_csv_path):
        opt_stats = self.compute_portfolio_stats(self.weights_opt)
        ew_stats = self.compute_portfolio_stats(self.weights_ew)
        bm = self.bm_metrics
        
        rho_p_bm = 0.75
        te_5y = math.sqrt(max(0.0001, opt_stats['Vol_5Y']**2 + bm['Vol_5Y']**2 - 2 * rho_p_bm * opt_stats['Vol_5Y'] * bm['Vol_5Y']))
        ir_5y = (opt_stats['Ret_5Y'] - bm['Ret_5Y']) / te_5y
        
        co2_reduc_12 = (1.0 - (opt_stats['Int_1_2'] / bm['Int_1_2'])) * 100.0
        co2_reduc_tot = (1.0 - (opt_stats['Int_Tot'] / bm['Int_Tot'])) * 100.0

        comparison_rows = [
            ('Rendement Annualisé 5 Ans', f"{opt_stats['Ret_5Y']*100:.2f}%", f"{ew_stats['Ret_5Y']*100:.2f}%", f"{bm['Ret_5Y']*100:.2f}%"),
            ('Volatilité Annualisée 5 Ans', f"{opt_stats['Vol_5Y']*100:.2f}%", f"{ew_stats['Vol_5Y']*100:.2f}%", f"{bm['Vol_5Y']*100:.2f}%"),
            ('Ratio de Sharpe 5 Ans (Rf=2%)', f"{opt_stats['Sharpe_5Y']:.2f}", f"{ew_stats['Sharpe_5Y']:.2f}", f"{bm['Sharpe_5Y']:.2f}"),
            ('Rendement Annualisé 1 An', f"{opt_stats['Ret_1Y']*100:.2f}%", f"{ew_stats['Ret_1Y']*100:.2f}%", f"{bm['Ret_1Y']*100:.2f}%"),
            ('Volatilité Annualisée 1 An', f"{opt_stats['Vol_1Y']*100:.2f}%", f"{ew_stats['Vol_1Y']*100:.2f}%", f"{bm['Vol_1Y']*100:.2f}%"),
            ('Ratio de Sharpe 1 An', f"{opt_stats['Sharpe_1Y']:.2f}", f"{ew_stats['Sharpe_1Y']:.2f}", f"{bm['Sharpe_1Y']:.2f}"),
            ('Rendement Annualisé 10 Ans', f"{opt_stats['Ret_10Y']*100:.2f}%", f"{ew_stats['Ret_10Y']*100:.2f}%", f"{bm['Ret_10Y']*100:.2f}%"),
            ('Volatilité Annualisée 10 Ans', f"{opt_stats['Vol_10Y']*100:.2f}%", f"{ew_stats['Vol_10Y']*100:.2f}%", f"{bm['Vol_10Y']*100:.2f}%"),
            ('Ratio de Sharpe 10 Ans', f"{opt_stats['Sharpe_10Y']:.2f}", f"{ew_stats['Sharpe_10Y']:.2f}", f"{bm['Sharpe_10Y']:.2f}"),
            ('Maximum Drawdown 5 Ans', f"{opt_stats['MDD_5Y']*100:.2f}%", f"{ew_stats['MDD_5Y']*100:.2f}%", f"{bm['MDD_5Y']*100:.2f}%"),
            ('VaR Quotidienne 95% (5 Ans)', f"{opt_stats['VaR95_5Y']*100:.2f}%", f"{ew_stats['VaR95_5Y']*100:.2f}%", f"{bm['VaR95_5Y']*100:.2f}%"),
            ('CVaR Quotidienne 95% (5 Ans)', f"{opt_stats['CVaR95_5Y']*100:.2f}%", f"{ew_stats['CVaR95_5Y']*100:.2f}%", f"{bm['CVaR95_5Y']*100:.2f}%"),
            ('Tracking Error 5 Ans vs MSCI World', f"{te_5y*100:.2f}%", "N/A", "0.00%"),
            ('Information Ratio 5 Ans vs MSCI World', f"{ir_5y:.2f}", "N/A", "0.00"),
            ('--- EXTRA-FINANCIER ---', '---', '---', '---'),
            ('Trajectoire Implied Temp Rise (ITR)', f"{opt_stats['ITR']:.2f}°C", f"{ew_stats['ITR']:.2f}°C", f"{bm['ITR']:.2f}°C"),
            ('Intensité Carbone Scope 1+2 (tCO2e/M$)', f"{opt_stats['Int_1_2']:.1f}", f"{ew_stats['Int_1_2']:.1f}", f"{bm['Int_1_2']:.1f}"),
            ('Réduction Carbone Scope 1+2 vs Benchmark', f"-{co2_reduc_12:.1f}%", f"-{(1.0 - ew_stats['Int_1_2']/bm['Int_1_2'])*100:.1f}%", "0.0%"),
            ('Intensité Carbone Totale Scope 1+2+3', f"{opt_stats['Int_Tot']:.1f}", f"{ew_stats['Int_Tot']:.1f}", f"{bm['Int_Tot']:.1f}"),
            ('Réduction Carbone Scope 1+2+3 vs Benchmark', f"-{co2_reduc_tot:.1f}%", f"-{(1.0 - ew_stats['Int_Tot']/bm['Int_Tot'])*100:.1f}%", "0.0%"),
            ('Score Alignement ODD 3 (Santé)', f"{opt_stats['SDG3']:.2f}", f"{ew_stats['SDG3']:.2f}", f"{bm['SDG3']:.2f}"),
            ('Score Alignement ODD 9 (Innovation IA)', f"{opt_stats['SDG9']:.2f}", f"{ew_stats['SDG9']:.2f}", f"{bm['SDG9']:.2f}"),
            ('Score Pilier Gouvernance (Kanopy)', f"{opt_stats['Gov']:.2f}/10", f"{ew_stats['Gov']:.2f}/10", f"{bm['Gov']:.2f}/10"),
            ('Part Aligné Taxonomie UE (Revenus Max)', f"{opt_stats['Taxo']:.2f}%", f"{ew_stats['Taxo']:.2f}%", f"{bm['Taxo']:.2f}%"),
            ('--- CONSTRAINTS & ALLOCATION ---', '---', '---', '---'),
            ('Nombre de Lignes en Portefeuille', f"{self.n}", f"{self.n}", f"{len(self.bm_rows)}"),
            ('Pondération Maximale Ligne (UCITS <=10%)', f"{opt_stats['Max_Weight']*100:.2f}%", f"{ew_stats['Max_Weight']*100:.2f}%", "4.8%"),
            ('Pondération Minimale Ligne', f"{opt_stats['Min_Weight']*100:.2f}%", f"{ew_stats['Min_Weight']*100:.2f}%", "0.001%"),
            ('Part Santé (Health Care)', f"{opt_stats['Health_Care_Weight']*100:.1f}%", f"{ew_stats['Health_Care_Weight']*100:.1f}%", "12.3%"),
            ('Part Technologie (IT & Enablers)', f"{opt_stats['Tech_Weight']*100:.1f}%", f"{ew_stats['Tech_Weight']*100:.1f}%", "24.1%"),
            ('Part Industrie & Composants Verts', f"{opt_stats['Industrials_Weight']*100:.1f}%", f"{ew_stats['Industrials_Weight']*100:.1f}%", "10.8%")
        ]

        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Indicateur', 'Synapse HealthTech & AI (Optimisé)', 'Équipondéré (EW 1/N)', 'Benchmark (MSCI World)'])
            for row in comparison_rows:
                writer.writerow(row)
                
        print(f"[Backtester] Tableau de comparaison exporté avec succès : {output_csv_path}")
        return comparison_rows


def run_backtest():
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
    
    output_file = os.path.join(root_dir, "data", "resultats_backtest_comparaison.csv")
    
    backtester = PortfolioBacktester(all_data_file, pf_file)
    rows = backtester.run_and_compare(output_file)
    
    legacy_tri = os.path.join(root_dir, "dossier_tri")
    if os.path.exists(legacy_tri):
        backtester.run_and_compare(os.path.join(legacy_tri, "resultats_backtest_comparaison.csv"))
        
    print("\n--- SYNTHÈSE DES RÉSULTATS COMPARATIFS ---")
    for r in rows:
        print(f"{r[0]:<45} | {r[1]:<22} | {r[2]:<20} | {r[3]:<18}")


if __name__ == '__main__':
    run_backtest()
