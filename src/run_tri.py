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
              (SBTi : photo du 13/01/2025, objectifs validés publiés au 31/12/2024 - Modif Mohamed)

  - Étape 8 : Intersection Univers Thématique HealthTech & AI (Slide 62)
  - Étape 9 : Intersection Univers Financier Quantitatif (Slide 59 & 62, FCF Jensen 1986)
  ==> Exporte 'data/actifs_notre_secteur_healthtech_ai.csv' (49 valeurs - Modif Mohamed)
"""

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
        EnvironmentalPillarFilter,
        SectorCarbonFootprintFilter,
        SectorCarbonIntensityFilter,
        ClimateSDGFilter,
        PositiveContributionFilter,
        HealthTechAIScopeFilter,
        FinancialQualityFilter,
        SBTI_STATUS_FIELDS,
        SBTI_VALIDATED,  # Modif Mohamed
        SBTI_COMMITTED,  # Modif Mohamed
        SBTI_REMOVED,  # Modif Mohamed
    )
except ImportError:
    from filters import (
        Company,
        PABExclusionFilter,
        DNSHControversyFilter,
        GoodGovernanceAndRatingFilter,
        ParisAlignmentITRFilter,
        EnvironmentalPillarFilter,
        SectorCarbonFootprintFilter,
        SectorCarbonIntensityFilter,
        ClimateSDGFilter,
        PositiveContributionFilter,
        HealthTechAIScopeFilter,
        FinancialQualityFilter,
        SBTI_STATUS_FIELDS,
        SBTI_VALIDATED,  # Modif Mohamed
        SBTI_COMMITTED,  # Modif Mohamed
        SBTI_REMOVED,  # Modif Mohamed
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


def load_sbti_by_isin(filepath: str):
    """Charge la base SBTi indexée par ISIN (pour les données complémentaires)."""
    sbti_by_isin = {}
    if not os.path.exists(filepath):
        return sbti_by_isin
    with open(filepath, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            isin = (row.get("isin") or "").strip().upper()
            if isin and isin not in sbti_by_isin:
                sbti_by_isin[isin] = row
    return sbti_by_isin


def load_sbti_snapshot_by_isin(filepath: str):  # Modif Mohamed
    """Charge la photo SBTi du 13/01/2025, déjà jointe à l'univers MSCI, indexée par ISIN (Modif Mohamed).

    Elle donne les statuts SBTi à la date de nos données (31/12/2024), sans le biais d'anticipation
    de la base de novembre 2026 (89 valeurs y sont validées alors qu'elles ne l'étaient pas fin 2024).
      - seuls les rapprochements sûrs sont gardés (sbti_match_status == 'MATCHED') : les cas 'REVIEW'
        (Roche...) et 'UNMATCHED' restent absents de la base SBTi, une donnée manquante ne vaut pas validation ;
      - un objectif n'est validé que si sa publication avant le 31/12/2024 est confirmée
        (sbti_near_term_validation_published_by_cutoff_confirmed == '1') ;
      - les statuts de la photo ('Targets Set', 'Committed', 'Removed') sont traduits dans le vocabulaire
        du Target Dashboard utilisé par filters.py. Aucun objectif long terme n'y est validé sans objectif
        court terme validé : le statut court terme suffit.
    """
    snapshot_to_dashboard = {"Committed": SBTI_COMMITTED, "Removed": SBTI_REMOVED}  # Modif Mohamed
    sbti_by_isin = {}  # Modif Mohamed
    if not os.path.exists(filepath):  # Modif Mohamed
        return sbti_by_isin  # Modif Mohamed
    with open(filepath, mode="r", encoding="utf-8-sig") as f:  # Modif Mohamed
        for row in csv.DictReader(f):  # Modif Mohamed
            isin = (row.get("isin") or "").strip().upper()  # Modif Mohamed
            if not isin or row.get("sbti_match_status") != "MATCHED":  # Modif Mohamed
                continue  # Modif Mohamed
            snapshot = (row.get("sbti_near_term_status_snapshot") or "").strip()  # Modif Mohamed
            if row.get("sbti_near_term_validation_published_by_cutoff_confirmed") == "1":  # Modif Mohamed
                near_term = SBTI_VALIDATED  # Modif Mohamed
            elif snapshot == "Targets Set":  # validé en janvier 2025 mais publication non confirmée au 31/12/2024  # Modif Mohamed
                near_term = "Targets Set (publication non confirmée au 31/12/2024)"  # Modif Mohamed
            else:  # Modif Mohamed
                near_term = snapshot_to_dashboard.get(snapshot, snapshot)  # Modif Mohamed
            sbti_by_isin[isin] = {"company_name": row.get("sbti_company_name", ""), "near_term_status": near_term}  # Modif Mohamed
    return sbti_by_isin  # Modif Mohamed


def export_sbti_join(filepath: str, companies, contrib_filter):
    """Exporte la jointure ISIN entre notre univers et la base SBTi (livrable complémentaire)."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fieldnames = ["ticker", "name", "isin", "sbti_company_name", "statut_sbti"] + list(SBTI_STATUS_FIELDS) + [
        "ca_aligne_taxonomie_pct", "contribution_positive_sfdr"]
    with open(filepath, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in companies:
            record = contrib_filter.sbti_by_isin.get(c.isin.upper(), {})
            row = {
                "ticker": c.ticker,
                "name": c.name,
                "isin": c.isin,
                "sbti_company_name": record.get("company_name", ""),
                "statut_sbti": contrib_filter.sbti_status(c),
                "ca_aligne_taxonomie_pct": c.to_dict().get("EST_EU_TAXONOMY_MAX_REV", ""),
                "contribution_positive_sfdr": "Oui" if contrib_filter.evaluate(c) else "Non",
            }
            for field in SBTI_STATUS_FIELDS:
                row[field] = record.get(field, "")
            writer.writerow(row)
    print(f"-> Fichier exporté avec succès : {filepath} ({len(companies)} entreprises)")


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

    # Base SBTi de novembre 2026 (postérieure à nos données du 31/12/2024 : biais d'anticipation)  # Modif Mohamed
    # sbti_csv = os.path.join(root_dir, "data", "sbti", "companies-excel.csv")  # Modif Mohamed
    # sbti_by_isin = load_sbti_by_isin(sbti_csv) if os.path.exists(sbti_csv) else {}  # Modif Mohamed
    sbti_csv = os.path.join(root_dir, "data", "sbti", "msci_world_jointure_sbti_2025-01-13.csv")  # Modif Mohamed
    sbti_by_isin = load_sbti_snapshot_by_isin(sbti_csv) if os.path.exists(sbti_csv) else {}  # Modif Mohamed

    if verbose:
        print("=" * 80)
        print(" PIPELINE DE SÉLECTION CONFORME AU COURS 'APPROCHE QUANTITATIVE' (JEAN JARDEL)")
        print("=" * 80)

    # 1. Chargement de l'univers initial
    companies, headers = load_data(input_csv)
    total_initial = len(companies)
    if verbose:
        print(f"\n[Univers Initial] MSCI World Developed Markets : {total_initial} valeurs\n")
        if sbti_by_isin:
            print(f"[Données SBTi] {len(sbti_by_isin)} valeurs retrouvées dans la photo SBTi du 13/01/2025 (statuts au 31/12/2024)")  # Modif Mohamed

    # 2. Instanciation des filtres (conformes aux Slides 13 & 40 à 50)
    pab_filter = PABExclusionFilter()
    dnsh_filter = DNSHControversyFilter()
    gov_filter = GoodGovernanceAndRatingFilter()
    itr_filter = ParisAlignmentITRFilter(max_itr=2.0)
    env_pillar_filter = EnvironmentalPillarFilter(companies, quantile_level=0.05)
    footprint_filter = SectorCarbonFootprintFilter(companies, percentile=0.90)
    carbon_filter = SectorCarbonIntensityFilter(companies, percentile=0.90)
    climate_sdg_filter = ClimateSDGFilter()
    pos_contrib_filter = PositiveContributionFilter(sbti_by_isin=sbti_by_isin, min_taxonomy_rev=20.0)
    thematic_filter = HealthTechAIScopeFilter()
    financial_filter = FinancialQualityFilter()

    # --- SÉLECTION EXTRA-FINANCIÈRE (Slides 40 à 50) ---
    if verbose:
        print("-" * 80)
        print(" A. FILTRAGE EXTRA-FINANCIER SFDR ARTICLE 2(17) & PAB (SLIDES 40-50)")
        print("-" * 80)

    step1 = pab_filter.filter(companies)
    if verbose:
        print(f"[1] {pab_filter.name:<48} ({pab_filter.slide_ref}) : {len(step1):>4} valeurs (-{total_initial - len(step1):>3} exclues)")

    step2 = dnsh_filter.filter(step1)
    if verbose:
        print(f"[2] {dnsh_filter.name:<48} ({dnsh_filter.slide_ref}) : {len(step2):>4} valeurs (-{len(step1) - len(step2):>3} exclues)")

    step3 = gov_filter.filter(step2)
    if verbose:
        print(f"[3] {gov_filter.name:<48} ({gov_filter.slide_ref}) : {len(step3):>4} valeurs (-{len(step2) - len(step3):>3} exclues)")

    step4 = itr_filter.filter(step3)
    if verbose:
        print(f"[4] {itr_filter.name:<48} ({itr_filter.slide_ref}) : {len(step4):>4} valeurs (-{len(step3) - len(step4):>3} exclues)")

    step5 = env_pillar_filter.filter(step4)
    if verbose:
        print(f"[5] {env_pillar_filter.name:<48} ({env_pillar_filter.slide_ref}) : {len(step5):>4} valeurs (-{len(step4) - len(step5):>3} exclues)")

    step6 = footprint_filter.filter(step5)
    if verbose:
        print(f"[6] {footprint_filter.name:<48} ({footprint_filter.slide_ref}) : {len(step6):>4} valeurs (-{len(step5) - len(step6):>3} exclues)")

    step7 = carbon_filter.filter(step6)
    if verbose:
        print(f"[7] {carbon_filter.name:<48} ({carbon_filter.slide_ref}) : {len(step7):>4} valeurs (-{len(step6) - len(step7):>3} exclues)")

    step8 = climate_sdg_filter.filter(step7)
    if verbose:
        print(f"[8] {climate_sdg_filter.name:<48} ({climate_sdg_filter.slide_ref}) : {len(step8):>4} valeurs (-{len(step7) - len(step8):>3} exclues)")

    sustainable_companies = pos_contrib_filter.filter(step8)
    if verbose:
        print(f"[9] {pos_contrib_filter.name:<48} ({pos_contrib_filter.slide_ref}) : {len(sustainable_companies):>4} valeurs (-{len(step8) - len(sustainable_companies):>3} exclues)")
        print(f"\n=> UNIVERS EXTRA-FINANCIER ÉLIGIBLE ARTICLE 2(17) SFDR : {len(sustainable_companies)} valeurs conservées sur {total_initial}")
        print(f"   Taux de sélectivité extra-financière : {(1 - len(sustainable_companies)/total_initial)*100:.1f}% exclus (conforme AMF > 20% & Slide 50)")

    # --- INTERSECTION THÉMATIQUE & FINANCIÈRE (Slide 62) ---
    if verbose:
        print("\n" + "-" * 80)
        print(" B. INTERSECTION DES 3 UNIVERS : NOTRE SCOPE HEALTHTECH & AI (SLIDE 62)")
        print("-" * 80)

    thematic_candidates = thematic_filter.filter(sustainable_companies)
    if verbose:
        print(f"[10] {thematic_filter.name:<47} ({thematic_filter.slide_ref}) : {len(thematic_candidates):>4} valeurs dans le scope")

    final_selected_universe = financial_filter.filter(thematic_candidates)
    if verbose:
        print(f"[11] {financial_filter.name:<47} ({financial_filter.slide_ref}) : {len(final_selected_universe):>4} valeurs hautement qualifiées")
        print(f"\n=> UNIVERS SÉLECTIONNABLE FINAL (Synapse HealthTech & AI Fund) : {len(final_selected_universe)} actifs")

    # Export des actifs du fonds dans data/
    file_scope_data = os.path.join(root_dir, "data", "actifs_notre_secteur_healthtech_ai.csv")
    export_to_csv(file_scope_data, final_selected_universe, headers)

    # Export de la jointure SBTi dans data/sbti/ (donnée complémentaire pour le rendu)
    if sbti_by_isin:
        file_sbti_join = os.path.join(root_dir, "data", "sbti", "jointure_sbti_msci.csv")
        export_sbti_join(file_sbti_join, companies, pos_contrib_filter)

    legacy_tri = os.path.join(root_dir, "dossier_tri")
    if os.path.exists(legacy_tri):
        export_to_csv(os.path.join(legacy_tri, "actifs_notre_secteur_healthtech_ai.csv"), final_selected_universe, headers)

    if verbose:
        print("\n" + "=" * 80)
        print(" SYNTHÈSE DU LIVRABLE GÉNÉRÉ DANS LE DOSSIER data/")
        print(f" • Actifs sélectionnés pour le fonds : {file_scope_data} ({len(final_selected_universe)} actifs)")
        if sbti_by_isin:
            print(f" • Donnée complémentaire SBTi        : {file_sbti_join} ({len(companies)} valeurs)")
        print("=" * 80)

    return final_selected_universe


if __name__ == "__main__":
    run_pipeline(verbose=True)
