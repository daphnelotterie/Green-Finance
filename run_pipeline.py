#!/usr/bin/env python3
"""
ORCHESTRATEUR PRINCIPAL DU PROJET - SYNAPSE HEALTHTECH & AI FUND
-----------------------------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry BÉCHU & Jean JARDEL (Kanopy AM)

Exécute la chaîne complète en une commande :
  1. Tri ESG & SFDR Article 2(17) (src/run_tri.py)
  2. Optimisation Quantitative Pedersen (src/optimizer.py)
  3. Moteur de Backtest Multi-Horizons (src/backtest.py)

Génère tous les fichiers CSV dans le dossier 'data/'.
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.run_tri import run_pipeline as run_tri_step
from src.optimizer import run_optimization as run_optimizer_step
from src.backtest import run_backtest as run_backtest_step


def print_banner(text):
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)


def main():
    start_time = time.time()
    
    print_banner("DÉMARRAGE DU PIPELINE COMPLET : SYNAPSE HEALTHTECH & AI FUND")
    print(f"Répertoire du projet : {BASE_DIR}")
    print(f"Dossier des données   : {os.path.join(BASE_DIR, 'data')}")
    print(f"Code source           : {os.path.join(BASE_DIR, 'src')}")
    print(f"Documentation         : {os.path.join(BASE_DIR, 'docs')}")

    # Étape 1 : Filtrage et sélection d'actifs
    print_banner("ÉTAPE 1 / 3 : FILTRAGE SFDR ARTICLE 2(17) & SCOPE HEALTHTECH & AI")
    run_tri_step(verbose=True)

    # Étape 2 : Optimisation mathématique
    print_banner("ÉTAPE 2 / 3 : OPTIMISATION QUANTITATIVE DE PEDERSEN ET AL. (2021)")
    run_optimizer_step()

    # Étape 3 : Backtest comparatif
    print_banner("ÉTAPE 3 / 3 : BACKTEST MULTI-HORIZONS & COMPARAISON MSCI WORLD")
    run_backtest_step()

    elapsed = time.time() - start_time
    print_banner(f"PIPELINE EXÉCUTÉ AVEC SUCCÈS EN {elapsed:.2f} SECONDES")
    print("Tous les livrables sont à jour dans le dossier 'data/' :")
    print(f"  • data/all_data.csv                       (Univers brut 1 247 valeurs)")
    print(f"  • data/actifs_notre_secteur_healthtech_ai.csv (Univers sélectionnable du fonds)")  # Modif Mohamed
    print(f"  • data/portefeuille_final_pondere.csv     (Portefeuille final avec poids optimaux)")
    print(f"  • data/resultats_backtest_comparaison.csv (Tableau complet de backtest)")
    print(f"  • data/sbti/jointure_sbti_msci.csv        (Statut SBTi de chaque valeur, jointure ISIN)")  # Modif Mohamed
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
