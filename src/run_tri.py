#!/usr/bin/env python3
"""Entonnoir ESG, thématique et financier, paramétré par mode de filtrage.

Les classes et l'ordre de sélection historiques sont conservés. Chaque mode
exporte son univers, ses effectifs et la traçabilité SBTi dans results/.
"""

import argparse
import csv
from pathlib import Path

try:
    from .filters import (
        Company, PABExclusionFilter, DNSHControversyFilter,
        GoodGovernanceAndRatingFilter, ParisAlignmentITRFilter,
        EnvironmentalPillarFilter, SectorCarbonFootprintFilter,
        SectorCarbonIntensityFilter, ClimateSDGFilter,
        PositiveContributionFilter, HealthTechAIScopeFilter,
        FinancialQualityFilter, FILTER_MODES, validate_filter_mode,
        SBTI_STATUS_FIELDS, SBTI_VALIDATED, SBTI_COMMITTED, SBTI_REMOVED,
    )
except ImportError:  # Exécution directe : python src/run_tri.py
    from filters import (
        Company, PABExclusionFilter, DNSHControversyFilter,
        GoodGovernanceAndRatingFilter, ParisAlignmentITRFilter,
        EnvironmentalPillarFilter, SectorCarbonFootprintFilter,
        SectorCarbonIntensityFilter, ClimateSDGFilter,
        PositiveContributionFilter, HealthTechAIScopeFilter,
        FinancialQualityFilter, FILTER_MODES, validate_filter_mode,
        SBTI_STATUS_FIELDS, SBTI_VALIDATED, SBTI_COMMITTED, SBTI_REMOVED,
    )


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "all_data.csv"
DEFAULT_SBTI = PROJECT_ROOT / "data" / "raw" / "sbti" / "msci_world_jointure_sbti_2025-01-13.csv"


def resolve_project_root():
    return str(PROJECT_ROOT)


def load_data(filepath):
    with Path(filepath).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames
        companies = [Company(row) for row in reader]
    if not companies or not headers:
        raise ValueError(f"Univers vide ou sans en-tête : {filepath}")
    isins = [c.isin for c in companies]
    if any(not isin for isin in isins) or len(set(isins)) != len(isins):
        raise ValueError("L'univers doit contenir un ISIN unique et renseigné par ligne.")
    return companies, headers


def export_to_csv(filepath, companies, headers, verbose=True):
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(c.to_dict() for c in companies)
    if verbose:
        print(f"-> {path} ({len(companies)} entreprises)")


def load_sbti_snapshot_by_isin(filepath):
    """Photo du 13/01/2025 ; publications confirmées avant le 31/12/2024.

    Seuls les rapprochements MATCHED sont retenus. Un statut Targets Set sans
    confirmation de publication au cutoff ne vaut pas validation. Une source
    absente est une erreur, pas une absence générale de validation des sociétés.
    """
    snapshot_to_dashboard = {"Committed": SBTI_COMMITTED, "Removed": SBTI_REMOVED}
    sbti_by_isin = {}
    with Path(filepath).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"isin", "sbti_match_status", "sbti_near_term_status_snapshot",
                    "sbti_near_term_validation_published_by_cutoff_confirmed"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Colonnes manquantes dans la source SBTi : {filepath}")
        for row in reader:
            isin = (row.get("isin") or "").strip().upper()
            if not isin or row["sbti_match_status"] != "MATCHED":
                continue
            snapshot = (row["sbti_near_term_status_snapshot"] or "").strip()
            confirmed = row["sbti_near_term_validation_published_by_cutoff_confirmed"] == "1"
            if confirmed:
                near_term = SBTI_VALIDATED
            elif snapshot == "Targets Set":
                near_term = "Targets Set (publication non confirmée au 31/12/2024)"
            else:
                near_term = snapshot_to_dashboard.get(snapshot, snapshot)
            if isin in sbti_by_isin:
                raise ValueError(f"ISIN dupliqué dans la source SBTi : {isin}")
            sbti_by_isin[isin] = {
                "company_name": row.get("sbti_company_name", ""),
                "near_term_status": near_term,
                "match_method": row.get("sbti_match_method", ""),
                "validation_confirmed_by_cutoff": "1" if confirmed else "0",
            }
    return sbti_by_isin


def export_sbti_join(filepath, companies, contrib_filter, verbose=True):
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["ticker", "name", "isin", "sbti_company_name", "statut_sbti"]
    fields += list(SBTI_STATUS_FIELDS)
    fields += ["source_snapshot", "cutoff", "match_method", "validation_confirmed_by_cutoff",
               "filter_mode", "ca_aligne_taxonomie_pct", "contribution_positive_sfdr"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for company in companies:
            record = contrib_filter.sbti_by_isin.get(company.isin.upper(), {})
            row = {
                "ticker": company.ticker, "name": company.name, "isin": company.isin,
                "sbti_company_name": record.get("company_name", ""),
                "statut_sbti": contrib_filter.sbti_status(company),
                "source_snapshot": "2025-01-13", "cutoff": "2024-12-31",
                "match_method": record.get("match_method", ""),
                "validation_confirmed_by_cutoff": record.get("validation_confirmed_by_cutoff", "0"),
                "filter_mode": contrib_filter.filter_mode,
                "ca_aligne_taxonomie_pct": company.to_dict().get("EST_EU_TAXONOMY_MAX_REV", ""),
                "contribution_positive_sfdr": "Oui" if contrib_filter.evaluate(company) else "Non",
            }
            row.update({field: record.get(field, "") for field in SBTI_STATUS_FIELDS})
            writer.writerow(row)
    if verbose:
        print(f"-> {path} ({len(companies)} entreprises)")


def build_filters(companies, sbti_by_isin, filter_mode="daphne"):
    """Construit l'entonnoir, seuils relatifs calculés sur l'univers complet."""
    validate_filter_mode(filter_mode)
    return [
        PABExclusionFilter(), DNSHControversyFilter(), GoodGovernanceAndRatingFilter(),
        ParisAlignmentITRFilter(companies=companies, filter_mode=filter_mode),
        EnvironmentalPillarFilter(companies, filter_mode=filter_mode),
        SectorCarbonFootprintFilter(companies), SectorCarbonIntensityFilter(companies),
        ClimateSDGFilter(), PositiveContributionFilter(sbti_by_isin, filter_mode=filter_mode),
        HealthTechAIScopeFilter(), FinancialQualityFilter(companies),
    ]


def run_pipeline(filter_mode="daphne", input_path=None, output_path=None,
                 sbti_output_path=None, funnel_output_path=None,
                 sbti_input_path=None, verbose=True):
    """Sélectionne et exporte un univers ; renvoie la liste des Company retenues."""
    validate_filter_mode(filter_mode)
    input_path = Path(input_path) if input_path is not None else DEFAULT_INPUT
    default_dir = PROJECT_ROOT / "results" / f"{filter_mode}_esg_risk"
    output_path = Path(output_path) if output_path is not None else default_dir / "actifs_selectionnes.csv"
    sbti_output_path = Path(sbti_output_path) if sbti_output_path is not None else output_path.parent / "jointure_sbti.csv"
    funnel_output_path = Path(funnel_output_path) if funnel_output_path is not None else output_path.parent / "entonnoir.csv"
    companies, headers = load_data(input_path)
    sbti_by_isin = load_sbti_snapshot_by_isin(sbti_input_path or DEFAULT_SBTI)
    filters = build_filters(companies, sbti_by_isin, filter_mode)
    rows = [{"etape": 0, "filtre": "Univers initial MSCI World", "reference": "",
             "entrees": len(companies), "retenues": len(companies), "exclues": 0,
             "filter_mode": filter_mode}]
    selected = companies
    if verbose:
        print(f"\nSélection {filter_mode} : {len(companies)} titres, {len(sbti_by_isin)} rapprochements SBTi sûrs")
    for step, selection_filter in enumerate(filters, start=1):
        incoming = len(selected)
        selected = selection_filter.filter(selected)
        rows.append({"etape": step, "filtre": selection_filter.name,
                     "reference": selection_filter.slide_ref, "entrees": incoming,
                     "retenues": len(selected), "exclues": incoming - len(selected),
                     "filter_mode": filter_mode})
        if verbose:
            print(f"[{step:2}] {selection_filter.name:<64} : {len(selected):4} (-{incoming - len(selected):3})")
    if not selected:
        raise ValueError(f"Aucun titre sélectionné pour le mode {filter_mode}.")
    export_to_csv(output_path, selected, headers, verbose)
    contribution_filter = next(f for f in filters if isinstance(f, PositiveContributionFilter))
    export_sbti_join(sbti_output_path, companies, contribution_filter, verbose)
    funnel_output_path.parent.mkdir(parents=True, exist_ok=True)
    with funnel_output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=FILTER_MODES, default="daphne")
    args = parser.parse_args()
    run_pipeline(filter_mode=args.mode)
