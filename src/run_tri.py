#!/usr/bin/env python3
"""
SCRIPT D'EXÉCUTION DU PIPELINE DE SÉLECTION ESG & ARTICLE 9 SFDR
----------------------------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry BÉCHU & Jean JARDEL (Kanopy AM)

Basé sur les diapositives de 'Finance Durable - Approche Quantitative' (Jean Jardel, 2026) :
  - Étape 1 : Exclusions PAB (Slide 44 & 50)
  - Étape 2 : DNSH - Filtrage des controverses sévères E, S, G (Slide 42 & 50)
  - Étape 3 : Bonne gouvernance - Notes ESG < BB exclues (Slide 41 & 50)
  - Étape 4 : Accord de Paris - Température ITR < Q80% (Slide 43 & 50)
  - Étape 5 : Pilier E > quantile à 5% (Slide 45 & 50)
  - Étape 6 : Empreinte carbone sectorielle Scope 1+2+3 (Slide 46 & 50)
  - Étape 7 : Intensité carbone sectorielle Scope 1+2+3 (Slide 46 & 50)
  - Étape 8 : ODD climatiques 7, 12, 13 (Slide 47 & 50)
  - Étape 9 : Contribution positive : Taxonomie >= 20% du CA ou objectif SBTi validé (Slide 13)
              (jointure par ISIN avec les données SBTi de data/sbti/)

  - Étape 10 : Intersection Univers Thématique HealthTech & AI (Slide 62)
  - Étape 11 : Intersection Univers Financier Quantitatif (Slide 59 & 62, FCF Jensen 1986)
  ==> Exporte 'data/actifs_notre_secteur_healthtech_ai.csv'
  ==> Exporte 'data/sbti/jointure_sbti_msci.csv' (statut SBTi de chaque valeur de l'univers)
"""  # Modif Mohamed

import csv
import os
import sys
from collections import Counter

try:
    from src.filters import (
        Company,
        PABExclusionFilter,
        DNSHControversyFilter,
        GoodGovernanceAndRatingFilter,
        ParisAlignmentITRFilter,
        EnvironmentalPillarFilter,  # Modif Mohamed
        SectorCarbonFootprintFilter,  # Modif Mohamed
        SectorCarbonIntensityFilter,
        ClimateSDGFilter,
        PositiveContributionFilter,
        HealthTechAIScopeFilter,
        FinancialQualityFilter,
        SBTI_STATUS_FIELDS,  # Modif Mohamed
    )
except ImportError:
    from filters import (
        Company,
        PABExclusionFilter,
        DNSHControversyFilter,
        GoodGovernanceAndRatingFilter,
        ParisAlignmentITRFilter,
        EnvironmentalPillarFilter,  # Modif Mohamed
        SectorCarbonFootprintFilter,  # Modif Mohamed
        SectorCarbonIntensityFilter,
        ClimateSDGFilter,
        PositiveContributionFilter,
        HealthTechAIScopeFilter,
        FinancialQualityFilter,
        SBTI_STATUS_FIELDS,  # Modif Mohamed
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


def load_sbti_by_isin(filepath: str):  # Modif Mohamed
    """Charge la base SBTi (une ligne par entreprise) indexée par ISIN. Les lignes sans ISIN sont ignorées."""  # Modif Mohamed
    sbti_by_isin = {}  # Modif Mohamed
    with open(filepath, mode="r", encoding="utf-8") as f:  # Modif Mohamed
        for row in csv.DictReader(f):  # Modif Mohamed
            isin = (row.get("isin") or "").strip().upper()  # Modif Mohamed
            if isin and isin not in sbti_by_isin:  # Modif Mohamed
                sbti_by_isin[isin] = row  # Modif Mohamed
    return sbti_by_isin  # Modif Mohamed


def export_sbti_join(filepath: str, companies, contrib_filter):  # Modif Mohamed
    """Exporte la jointure ISIN entre notre univers et la base SBTi (données complémentaires du rendu)."""  # Modif Mohamed
    os.makedirs(os.path.dirname(filepath), exist_ok=True)  # Modif Mohamed
    fieldnames = ["ticker", "name", "isin", "sbti_company_name", "statut_sbti"] + list(SBTI_STATUS_FIELDS) + [  # Modif Mohamed
        "ca_aligne_taxonomie_pct", "contribution_positive_slide13"]  # Modif Mohamed
    with open(filepath, mode="w", encoding="utf-8", newline="") as f:  # Modif Mohamed
        writer = csv.DictWriter(f, fieldnames=fieldnames)  # Modif Mohamed
        writer.writeheader()  # Modif Mohamed
        for c in companies:  # Modif Mohamed
            record = contrib_filter.sbti_by_isin.get(c.isin.upper(), {})  # Modif Mohamed
            row = {  # Modif Mohamed
                "ticker": c.ticker,  # Modif Mohamed
                "name": c.name,  # Modif Mohamed
                "isin": c.isin,  # Modif Mohamed
                "sbti_company_name": record.get("company_name", ""),  # Modif Mohamed
                "statut_sbti": contrib_filter.sbti_status(c),  # Modif Mohamed
                "ca_aligne_taxonomie_pct": c.to_dict().get("EST_EU_TAXONOMY_MAX_REV", ""),  # Modif Mohamed
                "contribution_positive_slide13": "Oui" if contrib_filter.evaluate(c) else "Non",  # Modif Mohamed
            }  # Modif Mohamed
            for field in SBTI_STATUS_FIELDS:  # Modif Mohamed
                row[field] = record.get(field, "")  # Modif Mohamed
            writer.writerow(row)  # Modif Mohamed
    print(f"-> Fichier exporté avec succès : {filepath} ({len(companies)} entreprises)")  # Modif Mohamed


def run_pipeline(verbose=True):
    root_dir = resolve_project_root()
    
    possible_inputs = [
        os.path.join(root_dir, "data", "all_data.csv"),
        os.path.join(root_dir, "all_data.csv")
    ]
    input_csv = next((p for p in possible_inputs if os.path.exists(p)), None)
    
    if not input_csv:
        print(f"Erreur : Impossible de trouver all_data.csv dans {possible_inputs}")
        sys.exit(1)

    sbti_csv = os.path.join(root_dir, "data", "sbti", "companies-excel.csv")  # Modif Mohamed
    if not os.path.exists(sbti_csv):  # Modif Mohamed
        print(f"Erreur : Impossible de trouver les données SBTi : {sbti_csv}")  # Modif Mohamed
        sys.exit(1)  # Modif Mohamed

    if verbose:
        print("=" * 80)
        print(" PIPELINE DE SÉLECTION CONFORME AU COURS 'APPROCHE QUANTITATIVE' (JEAN JARDEL)")
        print("=" * 80)

    # 1. Chargement de l'univers initial
    companies, headers = load_data(input_csv)
    total_initial = len(companies)
    if verbose:
        print(f"\n[Univers Initial] MSCI World Developed Markets : {total_initial} valeurs\n")

    # Données SBTi (jointure par ISIN)  # Modif Mohamed
    sbti_by_isin = load_sbti_by_isin(sbti_csv)  # Modif Mohamed

    # 2. Instanciation des filtres (seuils relatifs calculés sur l'univers complet)  # Modif Mohamed
    pab_filter = PABExclusionFilter()
    dnsh_filter = DNSHControversyFilter()
    gov_filter = GoodGovernanceAndRatingFilter()
    itr_filter = ParisAlignmentITRFilter(companies, quantile_level=0.80)  # Modif Mohamed
    env_pillar_filter = EnvironmentalPillarFilter(companies, quantile_level=0.05)  # Modif Mohamed
    footprint_filter = SectorCarbonFootprintFilter(companies, percentile=0.90)  # Modif Mohamed
    carbon_filter = SectorCarbonIntensityFilter(companies, percentile=0.90)
    climate_sdg_filter = ClimateSDGFilter()
    pos_contrib_filter = PositiveContributionFilter(sbti_by_isin, min_taxonomy_rev=20.0)  # Modif Mohamed
    thematic_filter = HealthTechAIScopeFilter()
    financial_filter = FinancialQualityFilter()

    if verbose:  # Modif Mohamed
        sbti_counts = Counter(pos_contrib_filter.sbti_status(c) for c in companies)  # Modif Mohamed
        print(f"[Données SBTi] {len(sbti_by_isin)} entreprises avec ISIN dans la base SBTi")  # Modif Mohamed
        print(f"   Jointure ISIN avec notre univers : {total_initial - sbti_counts['Absent de la base SBTi']} valeurs trouvées")  # Modif Mohamed
        for status, n in sbti_counts.most_common():  # Modif Mohamed
            print(f"   - {status:<36} : {n:>4}")  # Modif Mohamed
        print()  # Modif Mohamed

    # --- SÉLECTION EXTRA-FINANCIÈRE (Slides 13 & 40 à 50) ---  # Modif Mohamed
    if verbose:
        print("-" * 80)
        print(" A. FILTRAGE EXTRA-FINANCIER SFDR ARTICLE 2(17) & PAB (SLIDES 13, 40-50)")  # Modif Mohamed
        print("-" * 80)

    step1 = pab_filter.filter(companies)
    if verbose:
        print(f"[1] {pab_filter.name:<52} ({pab_filter.slide_ref}) : {len(step1):>4} valeurs (-{total_initial - len(step1):>3} exclues)")  # Modif Mohamed

    step2 = dnsh_filter.filter(step1)
    if verbose:
        print(f"[2] {dnsh_filter.name:<52} ({dnsh_filter.slide_ref}) : {len(step2):>4} valeurs (-{len(step1) - len(step2):>3} exclues)")  # Modif Mohamed

    step3 = gov_filter.filter(step2)
    if verbose:
        print(f"[3] {gov_filter.name:<52} ({gov_filter.slide_ref}) : {len(step3):>4} valeurs (-{len(step2) - len(step3):>3} exclues)")  # Modif Mohamed

    step4 = itr_filter.filter(step3)
    if verbose:
        print(f"[4] {itr_filter.name:<52} ({itr_filter.slide_ref}) : {len(step4):>4} valeurs (-{len(step3) - len(step4):>3} exclues)")  # Modif Mohamed

    step5 = env_pillar_filter.filter(step4)  # Modif Mohamed
    if verbose:
        print(f"[5] {env_pillar_filter.name:<52} ({env_pillar_filter.slide_ref}) : {len(step5):>4} valeurs (-{len(step4) - len(step5):>3} exclues)")  # Modif Mohamed

    step6 = footprint_filter.filter(step5)  # Modif Mohamed
    if verbose:
        print(f"[6] {footprint_filter.name:<52} ({footprint_filter.slide_ref}) : {len(step6):>4} valeurs (-{len(step5) - len(step6):>3} exclues)")  # Modif Mohamed

    step7 = carbon_filter.filter(step6)  # Modif Mohamed
    if verbose:
        print(f"[7] {carbon_filter.name:<52} ({carbon_filter.slide_ref}) : {len(step7):>4} valeurs (-{len(step6) - len(step7):>3} exclues)")  # Modif Mohamed

    step8 = climate_sdg_filter.filter(step7)  # Modif Mohamed
    if verbose:  # Modif Mohamed
        print(f"[8] {climate_sdg_filter.name:<52} ({climate_sdg_filter.slide_ref}) : {len(step8):>4} valeurs (-{len(step7) - len(step8):>3} exclues)")  # Modif Mohamed

    sustainable_companies = pos_contrib_filter.filter(step8)  # Modif Mohamed
    if verbose:  # Modif Mohamed
        print(f"[9] {pos_contrib_filter.name:<52} ({pos_contrib_filter.slide_ref}) : {len(sustainable_companies):>4} valeurs (-{len(step8) - len(sustainable_companies):>3} exclues)")  # Modif Mohamed
        print(f"\n=> UNIVERS EXTRA-FINANCIER ÉLIGIBLE ARTICLE 2(17) SFDR : {len(sustainable_companies)} valeurs conservées sur {total_initial}")
        print(f"   Taux de sélectivité extra-financière : {(1 - len(sustainable_companies)/total_initial)*100:.1f}% exclus (conforme AMF > 20% & Slide 50)")

    # --- INTERSECTION THÉMATIQUE & FINANCIÈRE (Slide 62) ---
    if verbose:
        print("\n" + "-" * 80)
        print(" B. INTERSECTION DES 3 UNIVERS : NOTRE SCOPE HEALTHTECH & AI (SLIDE 62)")
        print("-" * 80)

    thematic_candidates = thematic_filter.filter(sustainable_companies)
    if verbose:
        print(f"[10] {thematic_filter.name:<51} ({thematic_filter.slide_ref}) : {len(thematic_candidates):>4} valeurs dans le scope")  # Modif Mohamed

    final_selected_universe = financial_filter.filter(thematic_candidates)
    if verbose:
        print(f"[11] {financial_filter.name:<51} ({financial_filter.slide_ref}) : {len(final_selected_universe):>4} valeurs hautement qualifiées")  # Modif Mohamed
        print(f"\n=> UNIVERS SÉLECTIONNABLE FINAL (Synapse HealthTech & AI Fund) : {len(final_selected_universe)} actifs")

    # Export des actifs du fonds dans data/
    file_scope_data = os.path.join(root_dir, "data", "actifs_notre_secteur_healthtech_ai.csv")
    export_to_csv(file_scope_data, final_selected_universe, headers)

    # Export de la jointure SBTi (statut de chaque valeur de l'univers) dans data/sbti/  # Modif Mohamed
    file_sbti_join = os.path.join(root_dir, "data", "sbti", "jointure_sbti_msci.csv")  # Modif Mohamed
    export_sbti_join(file_sbti_join, companies, pos_contrib_filter)  # Modif Mohamed

    legacy_tri = os.path.join(root_dir, "dossier_tri")
    if os.path.exists(legacy_tri):
        export_to_csv(os.path.join(legacy_tri, "actifs_notre_secteur_healthtech_ai.csv"), final_selected_universe, headers)

    if verbose:
        print("\n" + "=" * 80)
        print(" SYNTHÈSE DU LIVRABLE GÉNÉRÉ DANS LE DOSSIER data/")
        print(f" • Actifs sélectionnés pour le fonds : {file_scope_data} ({len(final_selected_universe)} actifs)")
        print(f" • Jointure SBTi de l'univers         : {file_sbti_join} ({len(companies)} valeurs)")  # Modif Mohamed
        print("=" * 80)

    return final_selected_universe


if __name__ == "__main__":
    run_pipeline(verbose=True)
