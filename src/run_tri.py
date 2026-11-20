#!/usr/bin/env python3
"""
SCRIPT D'EXÉCUTION DU PIPELINE DE SÉLECTION ESG & ARTICLE 9 SFDR
----------------------------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry BÉCHU & Jean JARDEL (Kanopy AM)

Basé sur les diapositives de 'Finance Durable - Approche Quantitative' (Jean Jardel, 2026) :
  - Étape 1 : Exclusions PAB (Slide 44 & 50)
  - Étape 2 : DNSH - Filtrage des controverses sévères E, S, G (Slide 42 & 50)
  - Étape 3 : Pratiques de bonne gouvernance & Notes ESG (Slide 41, 45 & 50)
  - Étape 4 : Accord de Paris - Trajectoire de température ITR <= 2.0°C (Slide 43 & 50)
  - Étape 5 : Empreinte & intensité carbone sectorielle (Slide 46 & 50)
  - Étape 6 : ODD climatiques et environnementaux (Slide 47 & 50)
  - Étape 7 : Contribution positive substantielle (Slide 24 & SFDR Art. 2(17))
  ==> Exporte 'data/actifs_tous_article_9.csv' (412 valeurs)

  - Étape 8 : Intersection Univers Thématique HealthTech & AI (Slide 62)
  - Étape 9 : Intersection Univers Financier Quantitatif (Slide 59 & 62, FCF Jensen 1986)
  ==> Exporte 'data/actifs_notre_secteur_healthtech_ai.csv' (50 valeurs)
"""

import csv
import os
import sys
from collections import Counter

# Support d'importation direct ou en module
try:
    from src.filters import (
        Company,
        PABExclusionFilter,
        DNSHControversyFilter,
        GoodGovernanceAndRatingFilter,
        ParisAlignmentITRFilter,
        SectorCarbonIntensityFilter,
        ClimateSDGFilter,
        PositiveContributionFilter,
        HealthTechAIScopeFilter,
        FinancialQualityFilter,
    )
except ImportError:
    from filters import (
        Company,
        PABExclusionFilter,
        DNSHControversyFilter,
        GoodGovernanceAndRatingFilter,
        ParisAlignmentITRFilter,
        SectorCarbonIntensityFilter,
        ClimateSDGFilter,
        PositiveContributionFilter,
        HealthTechAIScopeFilter,
        FinancialQualityFilter,
    )


def resolve_project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) in ["src", "dossier_tri"]:
        return os.path.dirname(current_dir)
    return current_dir


def load_data(filepath: str):
    companies = []
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for row in reader:
            companies.append(Company(row))
    return companies, headers


def export_to_csv(filepath: str, companies, headers):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for c in companies:
            writer.writerow(c.to_dict())
    print(f"-> Fichier exporté avec succès : {filepath} ({len(companies)} entreprises)")


def run_pipeline(verbose=True):
    root_dir = resolve_project_root()
    
    # Recherche all_data.csv (dans data/ ou racine)
    possible_inputs = [
        os.path.join(root_dir, "data", "all_data.csv"),
        os.path.join(root_dir, "all_data.csv")
    ]
    input_csv = next((p for p in possible_inputs if os.path.exists(p)), None)
    
    if not input_csv:
        print(f"Erreur : Impossible de trouver all_data.csv dans {possible_inputs}")
        sys.exit(1)

    if verbose:
        print("=" * 80)
        print(" PIPELINE DE SÉLECTION CONFORME AU COURS 'APPROCHE QUANTITATIVE' (JEAN JARDEL)")
        print("=" * 80)

    # 1. Chargement de l'univers initial
    companies, headers = load_data(input_csv)
    total_initial = len(companies)
    if verbose:
        print(f"\n[Univers Initial] MSCI World Developed Markets : {total_initial} valeurs\n")

    # 2. Instanciation des filtres
    pab_filter = PABExclusionFilter()
    dnsh_filter = DNSHControversyFilter()
    gov_filter = GoodGovernanceAndRatingFilter()
    itr_filter = ParisAlignmentITRFilter(max_itr=2.0)
    carbon_filter = SectorCarbonIntensityFilter(companies, percentile=0.90)
    climate_sdg_filter = ClimateSDGFilter()
    pos_contrib_filter = PositiveContributionFilter()
    thematic_filter = HealthTechAIScopeFilter()
    financial_filter = FinancialQualityFilter()

    # --- SÉLECTION EXTRA-FINANCIÈRE (Slides 40 à 50) ---
    if verbose:
        print("-" * 80)
        print(" A. CONSTRUCTION DE L'UNIVERS EXTRA-FINANCIER ARTICLE 9 GLOBAL (SLIDES 40-50)")
        print("-" * 80)

    step1 = pab_filter.filter(companies)
    if verbose:
        print(f"[1] {pab_filter.name:<45} ({pab_filter.slide_ref}) : {len(step1):>4} valeurs (-{total_initial - len(step1):>3} exclues)")

    step2 = dnsh_filter.filter(step1)
    if verbose:
        print(f"[2] {dnsh_filter.name:<45} ({dnsh_filter.slide_ref}) : {len(step2):>4} valeurs (-{len(step1) - len(step2):>3} exclues)")

    step3 = gov_filter.filter(step2)
    if verbose:
        print(f"[3] {gov_filter.name:<45} ({gov_filter.slide_ref}) : {len(step3):>4} valeurs (-{len(step2) - len(step3):>3} exclues)")

    step4 = itr_filter.filter(step3)
    if verbose:
        print(f"[4] {itr_filter.name:<45} ({itr_filter.slide_ref}) : {len(step4):>4} valeurs (-{len(step3) - len(step4):>3} exclues)")

    step5 = carbon_filter.filter(step4)
    if verbose:
        print(f"[5] {carbon_filter.name:<45} ({carbon_filter.slide_ref}) : {len(step5):>4} valeurs (-{len(step4) - len(step5):>3} exclues)")

    step6 = climate_sdg_filter.filter(step5)
    if verbose:
        print(f"[6] {climate_sdg_filter.name:<45} ({climate_sdg_filter.slide_ref}) : {len(step6):>4} valeurs (-{len(step5) - len(step6):>3} exclues)")

    all_art9_universe = pos_contrib_filter.filter(step6)
    if verbose:
        print(f"[7] {pos_contrib_filter.name:<45} ({pos_contrib_filter.slide_ref}) : {len(all_art9_universe):>4} valeurs (-{len(step6) - len(all_art9_universe):>3} exclues)")
        print(f"\n=> TOTAL UNIVERS EXTRA-FINANCIER ARTICLE 9 GLOBAL : {len(all_art9_universe)} valeurs conservées sur {total_initial}")
        print(f"   Taux de sélectivité extra-financière : {(1 - len(all_art9_universe)/total_initial)*100:.1f}% exclus (conforme AMF > 20% & Slide 50)")

    # Export fichier 1 dans data/
    file_art9_data = os.path.join(root_dir, "data", "actifs_tous_article_9.csv")
    export_to_csv(file_art9_data, all_art9_universe, headers)

    # Copie dans dossier_tri si existant pour compatibilité
    legacy_tri = os.path.join(root_dir, "dossier_tri")
    if os.path.exists(legacy_tri):
        export_to_csv(os.path.join(legacy_tri, "actifs_tous_article_9.csv"), all_art9_universe, headers)

    # --- INTERSECTION THÉMATIQUE & FINANCIÈRE (Slide 62) ---
    if verbose:
        print("\n" + "-" * 80)
        print(" B. INTERSECTION DES 3 UNIVERS : NOTRE SCOPE HEALTHTECH & AI (SLIDE 62)")
        print("-" * 80)

    thematic_candidates = thematic_filter.filter(all_art9_universe)
    if verbose:
        print(f"[8] {thematic_filter.name:<45} ({thematic_filter.slide_ref}) : {len(thematic_candidates):>4} valeurs dans le scope")

    final_selected_universe = financial_filter.filter(thematic_candidates)
    if verbose:
        print(f"[9] {financial_filter.name:<45} ({financial_filter.slide_ref}) : {len(final_selected_universe):>4} valeurs hautement qualifiées")
        print(f"\n=> UNIVERS SÉLECTIONNABLE FINAL (Synapse HealthTech & AI Fund) : {len(final_selected_universe)} actifs")

    # Export fichier 2 dans data/
    file_scope_data = os.path.join(root_dir, "data", "actifs_notre_secteur_healthtech_ai.csv")
    export_to_csv(file_scope_data, final_selected_universe, headers)

    if os.path.exists(legacy_tri):
        export_to_csv(os.path.join(legacy_tri, "actifs_notre_secteur_healthtech_ai.csv"), final_selected_universe, headers)

    if verbose:
        print("\n" + "=" * 80)
        print(" SYNTHÈSE DES LIVRABLES GÉNÉRÉS DANS LE DOSSIER data/")
        print(f" 1. Fichier Article 9 Global   : {file_art9_data} ({len(all_art9_universe)} actifs)")
        print(f" 2. Fichier Scope HealthTech&AI: {file_scope_data} ({len(final_selected_universe)} actifs)")
        print("=" * 80)

    return all_art9_universe, final_selected_universe


if __name__ == "__main__":
    run_pipeline(verbose=True)
