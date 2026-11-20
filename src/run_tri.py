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
  - Étape 5 : Pilier E >= quantile à 5%, les notes E < Q5% sont exclues (Slide 45 & 50)
  - Étape 6 : Empreinte carbone sectorielle Scope 1+2+3 (Slide 46 & 50)
  - Étape 7 : Intensité carbone sectorielle Scope 1+2+3 (Slide 46 & 50)
  - Étape 8 : ODD climatiques 7, 12, 13 (Slide 47 & 50)
  - Étape 9 : Contribution positive : Taxonomie >= 20% du CA ou objectif SBTi validé (Slide 13)
              (jointure par ISIN avec les données SBTi de data/sbti/ + rapprochements par nom vérifiés : SBTI_NAME_MATCHES)

  - Étape 10 : Intersection Univers Thématique HealthTech & AI (Slide 62)
  - Étape 11 : Intersection Univers Financier Quantitatif (Slide 59 & 62 : rentabilité, FCF > 0, dette, volatilité)
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
        # HealthTechAIScopeFilterV3,  # option thématique à valider par le groupe  # Modif Mohamed
        # HealthTechAIScopeFilterV6b,  # option thématique à valider par le groupe  # Modif Mohamed
        FinancialQualityFilter,
        FinancialQualityFilterDaphne,  # ancienne version conservée  # Modif Mohamed
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
        # HealthTechAIScopeFilterV3,  # option thématique à valider par le groupe  # Modif Mohamed
        # HealthTechAIScopeFilterV6b,  # option thématique à valider par le groupe  # Modif Mohamed
        FinancialQualityFilter,
        FinancialQualityFilterDaphne,  # ancienne version conservée  # Modif Mohamed
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


# Rapprochements par nom, vérifiés à la main un par un (nom, pays, secteur) :  # Modif Mohamed
# fiches SBTi sans ISIN, ou avec un autre ISIN que le nôtre (ancien ISIN avant une division d'actions,  # Modif Mohamed
# autre classe d'actions, ISIN d'obligation). Clé = ISIN de notre univers, valeur = sbti_id de la base SBTi.  # Modif Mohamed
# Le statut reste celui de la base SBTi : seul 'Validated Targets' vaut validation.  # Modif Mohamed
# Rejetés après vérification (autre société ou filiale) : Ferrari Group PLC, PPL Inc. (Japon), Nice Group Holding  # Modif Mohamed
# (Thaïlande), Mercedes-Benz AG, JAPAN POST Co., Kao (ISIN et secteur incohérents), homonymes "X&Y" de T&D Holdings.  # Modif Mohamed
SBTI_NAME_MATCHES = {  # Modif Mohamed
    "US02079K3059": "40009770",  # Alphabet Inc (ISIN SBTi US02079K1079)  # Modif Mohamed
    "US91324P1021": "40004642",  # UnitedHealth Group Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "DK0062498333": "40011759",  # Novo Nordisk A/S (ISIN SBTi DK0060534915)  # Modif Mohamed
    "JP3633400001": "40012050",  # Toyota Motor Corp (ISIN absent dans SBTi)  # Modif Mohamed
    "US8825081040": "40016887",  # Texas Instruments Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "US0311621009": "40013586",  # Amgen Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "US8636671013": "40008600",  # Stryker Corp (ISIN absent dans SBTi)  # Modif Mohamed
    "US0404132054": "40016903",  # Arista Networks Inc (ISIN SBTi US0404131064)  # Modif Mohamed
    "US5128073062": "40002772",  # Lam Research Corp (ISIN SBTi US5128071082)  # Modif Mohamed
    "IE00BK9ZQ967": "40005184",  # Trane Technologies PLC (ISIN SBTi US456873AF50)  # Modif Mohamed
    "US95040Q1040": "40006499",  # Welltower Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "SE0017486889": "40016060",  # Atlas Copco AB (ISIN SBTi SE0000101032)  # Modif Mohamed
    "US34959E1091": "40015131",  # Fortinet Inc (ISIN SBTi US34959EAB56)  # Modif Mohamed
    "GB00BD6K4575": "40011990",  # Compass Group PLC (ISIN SBTi GB00BLNN3L44)  # Modif Mohamed
    "IE000IVNQZ81": "40001391",  # TE Connectivity Ltd (ISIN absent dans SBTi)  # Modif Mohamed
    "JP3837800006": "40025776",  # Hoya Corp (ISIN absent dans SBTi)  # Modif Mohamed
    "SE0000115420": "40000092",  # Volvo AB (ISIN SBTi NO0003573016)  # Modif Mohamed
    "DE000A1EWWW0": "40013504",  # adidas AG (ISIN absent dans SBTi)  # Modif Mohamed
    "US0494681010": "40006398",  # Atlassian Corp (ISIN absent dans SBTi)  # Modif Mohamed
    "US24703L2025": "40003670",  # Dell Technologies Inc (ISIN SBTi US24703L1035)  # Modif Mohamed
    "GB00BM8PJY71": "40007372",  # NatWest Group PLC (ISIN SBTi GB00B7T77214)  # Modif Mohamed
    "US49271V1008": "40000587",  # Keurig Dr Pepper Inc (ISIN SBTi US26138E1091)  # Modif Mohamed
    "US2944291051": "40014347",  # Equifax Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "GB00BLGZ9862": "40010607",  # Tesco PLC (ISIN SBTi GB0008847096)  # Modif Mohamed
    "CA9628791027": "40008490",  # Wheaton Precious Metals Corp (ISIN SBTi CA8283361076)  # Modif Mohamed
    "JP3548600000": "40029049",  # Disco Corp (ISIN absent dans SBTi)  # Modif Mohamed
    "JP3188220002": "40003913",  # Otsuka Holdings Co Ltd (ISIN SBTi JP318822BQ90)  # Modif Mohamed
    "US9553061055": "40003146",  # West Pharmaceutical Services I (ISIN absent dans SBTi)  # Modif Mohamed
    "DE0006048408": "40004394",  # Henkel AG & Co KGaA (ISIN SBTi DE0006048432)  # Modif Mohamed
    "FR001400AJ45": "40006897",  # Michelin (ISIN SBTi FR0000121261)  # Modif Mohamed
    "CA8849038085": "40001574",  # Thomson Reuters Corp (ISIN SBTi CA8849031056)  # Modif Mohamed
    "DE0007664005": "40008739",  # Volkswagen AG (ISIN SBTi DE0007664039)  # Modif Mohamed
    "US29084Q1004": "40010518",  # EMCOR Group Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "US69370C1009": "40014590",  # PTC Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "US30040W1080": "40015961",  # Eversource Energy (ISIN absent dans SBTi)  # Modif Mohamed
    "CH1216478797": "40014780",  # DSM-Firmenich AG (ISIN SBTi NL0000009827)  # Modif Mohamed
    "US8962391004": "40013292",  # Trimble Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "CH0024638212": "40012037",  # Schindler Holding AG (ISIN SBTi CH0024638196)  # Modif Mohamed
    "SE0009922156": "40004069",  # Essity AB (ISIN SBTi SE0009922164)  # Modif Mohamed
    "SE0015658109": "40002519",  # Epiroc AB (ISIN SBTi SE0011166933)  # Modif Mohamed
    "GB00BPQY8M80": "40013805",  # Aviva PLC (ISIN SBTi GB0002162385)  # Modif Mohamed
    "US86800U3023": "40005203",  # Super Micro Computer Inc (ISIN SBTi US86800U1043)  # Modif Mohamed
    "US29362U1043": "40018443",  # Entegris Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "US42250P1030": "40006397",  # Healthpeak Properties Inc (ISIN SBTi US40414L1098)  # Modif Mohamed
    "JE00BTDN8H13": "40005379",  # Aptiv PLC (ISIN SBTi JE00B783TY65)  # Modif Mohamed
    "US98954M1018": "40012569",  # Zillow Group Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "CH1175448666": "40015034",  # Straumann Holding AG (ISIN SBTi CH0012280076)  # Modif Mohamed
    "DK0061539921": "40011359",  # Vestas Wind Systems A/S (ISIN SBTi DK0010268606)  # Modif Mohamed
    "US4262811015": "40009307",  # Jack Henry & Associates Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "US1156371007": "40007741",  # Brown-Forman Corp (ISIN absent dans SBTi)  # Modif Mohamed
    "CH1256740924": "40013913",  # SGS SA (ISIN SBTi CH0002497458)  # Modif Mohamed
    "US7587501039": "40002488",  # Regal Rexnord Corp (ISIN absent dans SBTi)  # Modif Mohamed
    "NL0015001WM6": "40006193",  # QIAGEN NV (ISIN SBTi NL0000240000)  # Modif Mohamed
    "JP3190000004": "40012040",  # Obayashi Corp (ISIN absent dans SBTi)  # Modif Mohamed
    "US79589L1061": "40004091",  # Samsara Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "US8064071025": "40013152",  # Henry Schein Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "JP3429800000": "40003080",  # ANA Holdings Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "JP3137200006": "40002932",  # Isuzu Motors Ltd (ISIN SBTi JP313720AM24)  # Modif Mohamed
    "SE0020050417": "40016052",  # Boliden AB (ISIN SBTi SE0017768716)  # Modif Mohamed
    "JP3820000002": "40002633",  # Fuji Electric Co Ltd (ISIN absent dans SBTi)  # Modif Mohamed
    "SE0000108201": "40006601",  # SKF AB (ISIN SBTi SE0000108227)  # Modif Mohamed
    "SE0021921269": "40011375",  # Saab AB (ISIN SBTi SE0000112385)  # Modif Mohamed
    "US29109X1063": "40007819",  # Aspen Technology Inc (ISIN SBTi US0453271035)  # Modif Mohamed
    "DK0060636678": "40018724",  # Tryg A/S (ISIN absent dans SBTi)  # Modif Mohamed
    "KYG2177B1014": "40012470",  # CK Asset Holdings Ltd (ISIN absent dans SBTi)  # Modif Mohamed
    "DE0007165631": "40004286",  # Sartorius AG (ISIN SBTi DE0007165607)  # Modif Mohamed
    "GB00BMWC6P49": "40010829",  # Mondi PLC (ISIN SBTi GB00B1CRLC47)  # Modif Mohamed
    "DE000KBX1006": "40004014",  # Knorr-Bremse AG (ISIN absent dans SBTi)  # Modif Mohamed
    "FI0009007900": "40009216",  # Kesko Oyj (ISIN SBTi FI0009000202)  # Modif Mohamed
    "CA8029121057": "40011989",  # Saputo Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "SE0004635878": "40013520",  # Sagax AB (ISIN absent dans SBTi)  # Modif Mohamed
    "GB00BP9LHF23": "40014702",  # Schroders PLC (ISIN SBTi GB0002405495)  # Modif Mohamed
    "KYG393871085": "40021977",  # GLOBALFOUNDRIES Inc (ISIN absent dans SBTi)  # Modif Mohamed
    "GB00BM8Q5M07": "40016013",  # JD Sports Fashion PLC (ISIN SBTi GB00BYX91H57)  # Modif Mohamed
    "SE0021628898": "40015797",  # Volvo Car AB (ISIN SBTi SE0016844831)  # Modif Mohamed
}  # Modif Mohamed


def load_sbti_by_isin(filepath: str):  # Modif Mohamed
    """Charge la base SBTi indexée par ISIN, complétée par les rapprochements par nom vérifiés (SBTI_NAME_MATCHES)."""  # Modif Mohamed
    sbti_by_isin = {}  # Modif Mohamed
    sbti_by_id = {}  # Modif Mohamed
    with open(filepath, mode="r", encoding="utf-8") as f:  # Modif Mohamed
        for row in csv.DictReader(f):  # Modif Mohamed
            sbti_by_id[(row.get("sbti_id") or "").strip()] = row  # Modif Mohamed
            isin = (row.get("isin") or "").strip().upper()  # Modif Mohamed
            if isin and isin not in sbti_by_isin:  # Modif Mohamed
                sbti_by_isin[isin] = row  # Modif Mohamed
    for our_isin, sbti_id in SBTI_NAME_MATCHES.items():  # Modif Mohamed
        if sbti_id in sbti_by_id:  # Modif Mohamed
            sbti_by_isin[our_isin] = sbti_by_id[sbti_id]  # Modif Mohamed
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

    # Données SBTi (jointure par ISIN + rapprochements par nom vérifiés)  # Modif Mohamed
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
    # Options à faire valider par le groupe (décommenter aussi la classe dans src/filters.py et son import) :  # Modif Mohamed
    # thematic_filter = HealthTechAIScopeFilterV3()   # V3 : Santé + Tech IA  # Modif Mohamed
    # thematic_filter = HealthTechAIScopeFilterV6b()  # V6b : V3 + industriels choisis  # Modif Mohamed
    financial_filter = FinancialQualityFilter(companies, vol_percentile=0.90)  # Modif Mohamed
    # financial_filter = FinancialQualityFilterDaphne()  # ancienne version (Sharpe et rendement 5 ans)  # Modif Mohamed

    if verbose:  # Modif Mohamed
        sbti_counts = Counter(pos_contrib_filter.sbti_status(c) for c in companies)  # Modif Mohamed
        print(f"[Données SBTi] {len(sbti_by_isin)} ISIN reliés à une fiche SBTi (dont {len(SBTI_NAME_MATCHES)} rapprochements par nom vérifiés)")  # Modif Mohamed
        print(f"   Jointure avec notre univers : {total_initial - sbti_counts['Absent de la base SBTi']} valeurs trouvées")  # Modif Mohamed
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
