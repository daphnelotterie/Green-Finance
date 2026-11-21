"""Filtres de sélection communs aux modes Daphné et Mohamed.

Les classes et l'ordre de l'entonnoir historique sont conservés. Les trois
variantes de règles portent sur l'ITR, l'égalité au quantile du pilier E et la
contribution positive. Les seuils relatifs sont calculés sur l'univers initial.
Il s'agit de règles pédagogiques/proxys, pas d'une certification réglementaire.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from collections import defaultdict
from math import isfinite


FILTER_MODES = ("daphne", "mohamed")


def validate_filter_mode(filter_mode: str) -> str:
    if filter_mode not in FILTER_MODES:
        raise ValueError(f"Mode de filtrage inconnu : {filter_mode!r}. Choix : {', '.join(FILTER_MODES)}")
    return filter_mode


# Champs utilisés par les filtres extra-financiers
CONTROVERSY_FIELDS = ("ENVIRONMENT_CONTROVERSY_SCORE", "SOCIAL_CONTROVERSY_SCORE", "GOVERNANCE_CONTROVERSY_SCORE")
INTENSITY_FIELDS = ("INTENSITY_SCOPE_1", "INTENSITY_SCOPE_2", "INTENSITY_SCOPE_3")
FOOTPRINT_FIELDS = ("FOOTPRINT_SCOPE_1", "FOOTPRINT_SCOPE_2", "FOOTPRINT_SCOPE_3")
CLIMATE_SDGS = (7, 12, 13)

# Statuts officiels de la base SBTi (Target Dashboard)
SBTI_STATUS_FIELDS = ("near_term_status", "long_term_status", "net_zero_status")
SBTI_VALIDATION_FIELDS = ("near_term_status", "long_term_status")
SBTI_VALIDATED = "Validated Targets"
SBTI_COMMITTED = "Commitment to Set Targets"
SBTI_REMOVED = "Commitment Removed"


def quantile(values: List[float], q: float) -> float:
    """Quantile par interpolation linéaire (convention standard numpy / pandas)."""
    if not values or not 0.0 <= q <= 1.0:
        raise ValueError("Un quantile exige des données valides et un niveau compris entre 0 et 1.")
    xs = sorted(values)
    h = (len(xs) - 1) * q
    lo = int(h)
    hi = min(lo + 1, len(xs) - 1)
    t = h - lo
    if t >= 0.5:
        return xs[hi] - (xs[hi] - xs[lo]) * (1 - t)
    return xs[lo] + (xs[hi] - xs[lo]) * t


class Company:
    """
    Représente une entreprise cotée de l'univers MSCI World Developed Markets
    avec l'ensemble de ses données financières et extra-financières.
    """

    def __init__(self, data: Dict[str, str]):
        self._raw_data = data
        self.ticker = data.get("ticker", "").strip()
        self.name = data.get("name", "").strip()
        self.isin = data.get("isin", "").strip()
        self.country = data.get("country", "").strip()
        self.sector = data.get("gics_sector_name", "").strip()
        self.industry_group = data.get("industry_group", "").strip()
        self.weight_msci = self._parse_float("Weight in MSCI World")

        # Performance financière
        self.return_5y = self._parse_float("Annualized return 5Y")
        self.return_1y = self._parse_float("Annualized return 1Y")
        self.volatility_5y = self._parse_float("Volatility 5Y")
        self.sharpe_5y = self._parse_float("Sharpe 5Y")
        self.var_95_5y = self._parse_float("VaR 95% 5Y")
        self.cvar_95_5y = self._parse_float("CVaR 95% 5Y")
        self.max_drawdown_5y = self._parse_float("Max drawdown 5Y")

        # Ratios fondamentaux (Jensen 1986 & Qualité financière Slide 59/62)
        self.roe = self._parse_float("ROE")
        self.roa = self._parse_float("ROA")
        self.roic = self._parse_float("ROIC")
        self.net_margin = self._parse_float("Net margin")
        self.debt_assets = self._parse_float("Debt assets")
        self.pe_ratio = self._parse_float("PE ratio")
        self.fcf_yield = self._parse_float("FCF yield")

        # Notations et piliers ESG (Slide 41 & 45)
        self.rating = data.get("IVA_COMPANY_RATING", "").strip()
        self.env_pillar = self._parse_float("ENVIRONMENTAL_PILLAR_SCORE")
        self.soc_pillar = self._parse_float("SOCIAL_PILLAR_SCORE")
        self.gov_pillar = self._parse_float("GOVERNANCE_PILLAR_SCORE")

        # Controverses E, S, G (Slide 42)
        self.env_controversy = self._parse_float("ENVIRONMENT_CONTROVERSY_SCORE", default=10.0)
        self.soc_controversy = self._parse_float("SOCIAL_CONTROVERSY_SCORE", default=10.0)
        self.gov_controversy = self._parse_float("GOVERNANCE_CONTROVERSY_SCORE", default=10.0)

        # Climat, Taxonomie & Intensités (Slide 43, 44 & 46)
        self.itr = self._parse_float("ITR", default=10.0)
        self.eu_taxonomy_rev = self._parse_float("EST_EU_TAXONOMY_MAX_REV")
        self.cleantech_rev = self._parse_float("CT_TOTAL_MAX_REV")
        self.intensity_s1 = self._parse_float("INTENSITY_SCOPE_1")
        self.intensity_s2 = self._parse_float("INTENSITY_SCOPE_2")
        self.intensity_s3 = self._parse_float("INTENSITY_SCOPE_3")
        self.carbon_intensity_s12 = self.intensity_s1 + self.intensity_s2
        self.carbon_intensity_s123 = self.carbon_intensity_s12 + self.intensity_s3
        self.footprint_s1 = self._parse_float("FOOTPRINT_SCOPE_1")
        self.footprint_s2 = self._parse_float("FOOTPRINT_SCOPE_2")
        self.footprint_s3 = self._parse_float("FOOTPRINT_SCOPE_3")
        self.carbon_footprint_s123 = self.footprint_s1 + self.footprint_s2 + self.footprint_s3

        # Exclusions PAB (Slide 44)
        self.cweap_tie = data.get("CWEAP_TIE", "").strip() == "1"
        self.tob_producer = data.get("TOB_PRODUCER", "").strip() == "1"

        # Alignement net ODD (SDG 1 à 17)
        self.sdg_scores: Dict[int, float] = {}
        for i in range(1, 18):
            col = f"SDG_{i:02d}_NET_ALIGNMENT_SCORE"
            self.sdg_scores[i] = self._parse_float(col, default=0.0)

    def _parse_float(self, field: str, default: float = 0.0) -> float:
        val = self._raw_data.get(field, "")
        if not val or val.strip() in ("", "NA", "N/A"):
            return default
        try:
            number = float(val.strip())
            return number if isfinite(number) else default
        except (ValueError, TypeError):
            return default

    def get_sdg(self, number: int) -> float:
        return self.sdg_scores.get(number, 0.0)

    def is_missing(self, *fields: str) -> bool:
        for f in fields:
            val = self._raw_data.get(f)
            if val is None or val.strip() in ("", "NA", "N/A"):
                return True
            # Les champs numériques illisibles sont aussi des données manquantes.
            if f != "IVA_COMPANY_RATING":
                try:
                    if not isfinite(float(val)):
                        return True
                except (ValueError, TypeError):
                    return True
        return False

    def to_dict(self) -> Dict[str, str]:
        return self._raw_data


class AbstractFilter(ABC):
    """Classe de base abstraite pour l'application d'un filtre de sélection."""

    def __init__(self, name: str, slide_ref: str, description: str):
        self.name = name
        self.slide_ref = slide_ref
        self.description = description

    @abstractmethod
    def evaluate(self, company: Company) -> bool:
        """Retourne True si l'entreprise passe le filtre, False sinon."""
        pass

    def filter(self, companies: List[Company]) -> List[Company]:
        """Applique le filtre sur une liste d'entreprises."""
        return [c for c in companies if self.evaluate(c)]


class PABExclusionFilter(AbstractFilter):
    """
    Slide 44 & 50 : Dénomination du fonds & Exclusions relatives au Paris-Aligned Benchmark (PAB).
    - Armes controversées (CWEAP_TIE = 1)
    - Tabac (TOB_PRODUCER = 1 ; donnée manquante => exclusion, Slide 50 note 1)
    - Pétrole & charbon (secteur Energy exclu)
    """

    def __init__(self):
        super().__init__(
            name="Exclusions PAB & Combustibles Fossiles",
            slide_ref="Slide 44 & 50",
            description="Exclut les armes controversées, le tabac et les entreprises du secteur Énergie."
        )

    def evaluate(self, company: Company) -> bool:
        if company.cweap_tie:
            return False
        if company.tob_producer or company.is_missing("TOB_PRODUCER"):
            return False
        if company.sector == "Energy":
            return False
        return True


class DNSHControversyFilter(AbstractFilter):
    """
    Slide 42 & 50 : Principe DNSH (Do No Significant Harm).
    Exclusion des controverses sévères sur les 3 piliers Environnement, Social et Gouvernance.
    Critère : note de controverse >= 2.0. Donnée manquante => exclusion (Slide 50, note 1).
    """

    def __init__(self):
        super().__init__(
            name="DNSH - Filtrage des Controverses Sévères",
            slide_ref="Slide 42 & 50",
            description="Exclut les entreprises ayant des controverses environnementales, sociales ou de gouvernance sévères (score < 2) ou sans donnée."
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing(*CONTROVERSY_FIELDS):
            return False
        return (
            company.env_controversy >= 2.0
            and company.soc_controversy >= 2.0
            and company.gov_controversy >= 2.0
        )


class GoodGovernanceAndRatingFilter(AbstractFilter):
    """
    Slide 41 & 50 : Article 9 - Bonne Gouvernance & Notation ESG.
    - Exclusion des notes ESG < BB (notes 'B' et 'CCC' exclues)
    - Note ESG manquante => exclusion (Slide 50, note 1)
    """

    def __init__(self):
        super().__init__(
            name="Bonne Gouvernance - Notation ESG >= BB",
            slide_ref="Slide 41 & 50",
            description="Exclut les notations ESG inférieures à BB (B, CCC) et les entreprises non notées."
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing("IVA_COMPANY_RATING"):
            return False
        return company.rating not in ["CCC", "B"]


class ParisAlignmentITRFilter(AbstractFilter):
    """Daphné : ITR <= 2°C ; Mohamed : ITR < Q80 de l'univers initial."""

    def __init__(self, max_itr: float = 2.0, *, companies=None,
                 filter_mode: str = "daphne", quantile_level: float = 0.80):
        self.filter_mode = validate_filter_mode(filter_mode)
        if filter_mode == "mohamed":
            if companies is None:
                raise ValueError("Le mode mohamed exige l'univers initial pour calculer le quantile ITR.")
            max_itr = quantile([c.itr for c in companies if not c.is_missing("ITR")], quantile_level)
        self.max_itr = max_itr
        rule = (f"ITR < Q{int(quantile_level * 100)}% ({max_itr:.1f}°C)"
                if filter_mode == "mohamed" else f"ITR <= {max_itr:.1f}°C")
        super().__init__(
            name=f"Accord de Paris - {rule}",
            slide_ref="Slide 43 & 50",
            description=f"Conserve les entreprises respectant {rule} ; donnée manquante exclue."
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing("ITR"):
            return False
        if self.filter_mode == "mohamed":
            return company.itr < self.max_itr
        return company.itr <= self.max_itr


class EnvironmentalPillarFilter(AbstractFilter):
    """Pilier E : > Q5 pour Daphné, >= Q5 pour Mohamed (égalité conservée)."""

    def __init__(self, companies: List[Company], quantile_level: float = 0.05,
                 filter_mode: str = "daphne"):
        self.filter_mode = validate_filter_mode(filter_mode)
        valid_scores = [c.env_pillar for c in companies if not c.is_missing("ENVIRONMENTAL_PILLAR_SCORE")]
        self.min_score = quantile(valid_scores, quantile_level)
        operator = ">=" if filter_mode == "mohamed" else ">"
        super().__init__(
            name=f"Pilier E {operator} Q{int(quantile_level * 100)}% ({self.min_score:.1f}/10)",
            slide_ref="Slide 45 & 50",
            description=f"Exige une note E {operator} {self.min_score:.1f}/10 ; donnée manquante exclue."
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing("ENVIRONMENTAL_PILLAR_SCORE"):
            return False
        if self.filter_mode == "mohamed":
            return company.env_pillar >= self.min_score
        return company.env_pillar > self.min_score


class SectorCarbonIntensityFilter(AbstractFilter):
    """
    Slide 46 & 50 : Intensité Carbone Sectorielle (tCO2e / M$ de chiffre d'affaires).
    Exclusion des 10% d'entreprises les plus émettrices (Scope 1+2+3) au sein de chaque secteur GICS.
    Donnée carbone manquante => exclusion (Slide 50, note 1).
    """

    fields = INTENSITY_FIELDS
    label = "Intensité"

    def __init__(self, companies: List[Company], percentile: float = 0.90):
        self.percentile = percentile
        super().__init__(
            name=f"{self.label} Carbone Sectorielle S1+2+3 (Top 10% exclus)",
            slide_ref="Slide 46 & 50",
            description=f"Exclut le décile supérieur (pire 10%) en {self.label.lower()} carbone Scope 1+2+3 au sein de chaque secteur."
        )
        self.sector_thresholds = self._compute_thresholds(companies, percentile)

    def value(self, company: Company) -> float:
        return company.carbon_intensity_s123

    def _compute_thresholds(self, companies: List[Company], percentile: float) -> Dict[str, float]:
        by_sec = defaultdict(list)
        for c in companies:
            if not c.is_missing(*self.fields):
                by_sec[c.sector].append(self.value(c))

        thresholds = {}
        for sec, vals in by_sec.items():
            if vals:
                thresholds[sec] = quantile(vals, percentile)
        return thresholds

    def evaluate(self, company: Company) -> bool:
        if company.is_missing(*self.fields):
            return False
        thresh = self.sector_thresholds.get(company.sector, float("inf"))
        return self.value(company) <= thresh


class SectorCarbonFootprintFilter(SectorCarbonIntensityFilter):
    """
    Slide 46 & 50 : Empreinte Carbone Sectorielle (tCO2e / M$ investi, valeur d'entreprise).
    Même règle que l'intensité : exclusion du pire décile Scope 1+2+3 de chaque secteur GICS.
    """

    fields = FOOTPRINT_FIELDS
    label = "Empreinte"

    def value(self, company: Company) -> float:
        return company.carbon_footprint_s123


class ClimateSDGFilter(AbstractFilter):
    """
    Slide 47 & 50 : ODD Climatiques et Environnementaux (ODD 7, 12, 13).
    Exclusion des entreprises ayant un alignement négatif sévère (score = -10, obstruction MSCI).
    Donnée manquante => exclusion (Slide 50, note 1).
    """

    def __init__(self):
        super().__init__(
            name="ODD Environnementaux (ODD 7, 12, 13)",
            slide_ref="Slide 47 & 50",
            description="Exclut les entreprises en obstruction sévère sur les ODD 7, 12 ou 13 (score = -10) ou sans donnée."
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing(*(f"SDG_{k:02d}_NET_ALIGNMENT_SCORE" for k in CLIMATE_SDGS)):
            return False
        return all(company.get_sdg(k) > -10.0 for k in CLIMATE_SDGS)


class PositiveContributionFilter(AbstractFilter):
    """
    Contribution positive : hybride (daphne) ou Taxonomie/SBTi uniquement (mohamed).
    Slide 13 & SFDR Article 2(17), utilisée ici comme proxy pédagogique.
    Pour notre fonds thématique HealthTech & IA, l'entreprise doit obligatoirement contribuer
    de manière positive et mesurable :
    - Voie Sociale / Santé (Thèse HealthTech) : ODD 3 (Santé) >= 1.0 ou ODD 9 (Innovation IA) >= 1.0,
      ou ODD fondamentaux >= 1.5.
    - Voie Environnementale / Climat (Slide 13 & SBTi) : Taxonomie >= 20% OU Cible de réduction validée par SBTi
      ('Validated Targets') OU Clean Tech >= 10% OU trajectoire exemplaire ITR <= 1.5°C.
    """

    def __init__(self, sbti_by_isin: Optional[Dict[str, Dict[str, str]]] = None,
                 min_taxonomy_rev: float = 20.0, filter_mode: str = "daphne"):
        self.filter_mode = validate_filter_mode(filter_mode)
        super().__init__(
            name=("Contribution positive hybride Santé & Climat" if filter_mode == "daphne"
                  else "Contribution positive stricte (Taxo >= 20% ou SBTi validé)"),
            slide_ref="Slide 13 & SFDR Art. 2(17)",
            description="Exige une contribution sociale (ODD 3/9 >= 1.0) OU environnementale (Taxo >= 20%, SBTi validé, CleanTech >= 10%, ITR <= 1.5°C)."
        )
        self.sbti_by_isin = sbti_by_isin or {}
        self.min_taxonomy_rev = min_taxonomy_rev

    def sbti_status(self, company: Company) -> str:
        """Statut SBTi de l'entreprise, retrouvée par son ISIN."""
        record = self.sbti_by_isin.get(company.isin.upper())
        if record is None:
            return "Absent de la base SBTi"
        if any(record.get(f, "").strip() == SBTI_VALIDATED for f in SBTI_VALIDATION_FIELDS):
            return "Objectif validé"
        statuses = [record.get(f, "").strip() for f in SBTI_STATUS_FIELDS]
        if SBTI_VALIDATED in statuses:
            return "Net zéro validé seul (non retenu)"
        if SBTI_COMMITTED in statuses:
            return "Engagement seulement (non validé)"
        if SBTI_REMOVED in statuses:
            return "Engagement retiré"
        return "Statut non renseigné"

    def has_sbti_validated_target(self, company: Company) -> bool:
        return self.sbti_status(company) == "Objectif validé"

    def has_sustainable_revenue(self, company: Company) -> bool:
        if company.is_missing("EST_EU_TAXONOMY_MAX_REV"):
            return False
        return company.eu_taxonomy_rev >= self.min_taxonomy_rev

    def evaluate(self, company: Company) -> bool:
        if self.filter_mode == "mohamed":
            return self.has_sustainable_revenue(company) or self.has_sbti_validated_target(company)
        contrib_env = (
            self.has_sustainable_revenue(company)
            or self.has_sbti_validated_target(company)
            or company.cleantech_rev >= 10.0
            or company.itr <= 1.5
        )
        contrib_soc = (
            company.get_sdg(3) >= 1.0
            or company.get_sdg(9) >= 1.0
            or any(company.get_sdg(k) >= 1.5 for k in [1, 2, 4, 6, 11])
        )
        return contrib_env or contrib_soc


class HealthTechAIScopeFilter(AbstractFilter):
    """
    Slide 62 : Univers Thématique Discrétionnaire (Notre Scope : HealthTech & AI).
    Sélectionne les entreprises qui participent à la convergence de la santé et de l'intelligence artificielle :
    1. Secteur Health Care : Biotechnologies, Pharmaceutiques, Dispositifs médicaux, Diagnostics, Robotique chirurgicale.
    2. Secteur Information Technology : Fournisseurs de capacités d'IA, semi-conducteurs spécialisés, calcul haute performance,
       logiciels de bio-informatique et simulation moléculaire (alignement ODD 9 >= 1.0 ou ODD 3 >= 1.0).
    3. Secteur Industrials : Équipements de laboratoire, filtration d'eau et fluides critiques pour la biopharmacie.
    4. Secteur Consumer Staples : Hygiène et produits médicaux (ODD 3 >= 4.0 ; seuil relevé de 2 à 4).
    Choix discrétionnaire  : Ansys, sous offre de rachat de Synopsys au 31/12/2024, est écartée
    et remplacée par PTC (logiciels de conception et de simulation, comme Ansys).
    """

    def __init__(self):
        super().__init__(
            name="Univers Thématique HealthTech & AI",
            slide_ref="Slide 62 (Univers Thématique)",
            description="Sélectionne les valeurs de la chaîne de valeur Santé, MedTech, IA computationnelle et filtration."
        )

    def evaluate(self, company: Company) -> bool:
        sec = company.sector
        ind = company.industry_group.lower()
        name = company.name.lower()
        s3 = company.get_sdg(3)
        s9 = company.get_sdg(9)

        # 0. Titre sous offre de rachat définitive au 31/12/2024, écarté car il va quitter la cote :
        #    Ansys (rachat par Synopsys annoncé le 16/01/2024, finalisé en juillet 2025 : plus aucun cours ensuite)
        if any(t in name for t in ["ansys"]):
            return False

        # 1. Santé au sens large (Pharma, Biotech, Dispositifs médicaux)
        if sec == "Health Care":
            return True

        # 2. Technologies & Enablers d'IA médicale
        if sec == "Information Technology":
            if s3 >= 1.0:
                return True
            if s9 >= 1.0 and any(t in ind for t in ["software", "semiconductors", "computers", "electronics"]):
                return True
            # Remplaçant d'Ansys : PTC, logiciels de conception (CAO, PLM) et de simulation comme Ansys,
            # utilisés par les fabricants de dispositifs médicaux ; passe tous les filtres ESG et financiers
            if any(t in name for t in ["ptc inc"]):
                return True

        # 3. Équipements de précision industrielle, instrumentation & fluides biopharma
        if sec == "Industrials":
            if s3 >= 1.0:
                return True
            if any(t in name for t in ["pentair", "mettler", "halma", "cummins", "siemens"]):
                return True

        # 4. Hygiène et produits médicaux : on exige une contribution FORTE à la santé (ODD 3 >= 4, et non plus 2).
        #    Avec 2, entraient aussi la bière (Kirin), la lessive ou l'agroalimentaire, que l'optimiseur à variance
        #    minimale gonflait car peu volatils. Restent Kimberly-Clark, Essity et Unicharm (ODD 3 = 5).
        if sec == "Consumer Staples":
            if s3 >= 4.0:
                return True

        return False


class FinancialQualityFilter(AbstractFilter):
    """
    Slide 59 & 62 : Univers Financier Quantitatif (« durabilité financière », slide 5).
    - Rentabilité : ROIC > 5% OU marge nette > 5%
    - Génération de cash : FCF yield > 0
    - Solvabilité : Debt/Assets < 65%
    - Risque : exclusion des 10% de titres les plus volatils du MSCI World (volatilité 5 ans)
    - Donnée manquante => exclusion
    """

    fields = ("ROIC", "Net margin", "FCF yield", "Debt assets", "Volatility 5Y")

    def __init__(self, companies: List[Company], vol_percentile: float = 0.90):
        self.max_volatility = quantile([c.volatility_5y for c in companies if not c.is_missing("Volatility 5Y")],
                                       vol_percentile)
        super().__init__(
            name="Univers Financier Quantitatif (Qualité & Cash)",
            slide_ref="Slide 59 & 62",
            description=f"Garde les entreprises rentables, à FCF positif, peu endettées et de volatilité <= {self.max_volatility:.1%}."
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing(*self.fields):  # donnée manquante => exclusion
            return False
        is_profitable = (company.roic > 5.0) or (company.net_margin > 5.0)  # ROE retiré (non fiable)
        generates_cash = company.fcf_yield > 0.0  # FCF réellement appliqué
        is_solvent = company.debt_assets < 65.0  # règle inchangée
        not_too_volatile = company.volatility_5y <= self.max_volatility  # risque au lieu de la performance passée
        return is_profitable and generates_cash and is_solvent and not_too_volatile
