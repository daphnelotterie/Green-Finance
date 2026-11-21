"""
MODULE DE FILTRAGE ORIENTÉ OBJET (POO) - SÉLECTION SFDR ARTICLE 9 & PAB
------------------------------------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry BÉCHU & Jean JARDEL (Kanopy AM)

Basé sur le cours 'Finance Durable - Approche Quantitative' (Jean Jardel, 2026) :
  - Slide 24 : Définition SFDR Article 2(17) (Contribution positive, DNSH, Bonne gouvernance)
  - Slide 41 : Notations ESG & Bonne gouvernance (Exclusion notes CCC et B)
  - Slide 42 : DNSH - Notes de controverses E, S, G (Exclusion controverses sévères < 2.0)
  - Slide 43 : Accord de Paris - Trajectoire de température (ITR <= 2.0°C)
  - Slide 44 : Dénomination du fonds - Exclusions PAB (Armes controversées, Tabac, Énergie fossile)
  - Slide 45 : Pilier Gouvernance - Exclusion du quantile à 5% (Note G <= 3.0 / 10)
  - Slide 46 : Empreinte & Intensité carbone sectorielle (Exclusion pire décile 10% par secteur)
  - Slide 47 : ODD Climatiques (Exclusion atteintes ODD 7, 12, 13)
  - Slide 62 : Intersection des 3 univers (Venn) :
               Univers Financier Quantitatif ∩ Univers Extra-Financier ∩ Univers Thématique Discrétionnaire
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from collections import defaultdict


# Statuts officiels de la base SBTi (Target Dashboard)
SBTI_STATUS_FIELDS = ("near_term_status", "long_term_status", "net_zero_status")
SBTI_VALIDATION_FIELDS = ("near_term_status", "long_term_status")
SBTI_VALIDATED = "Validated Targets"
SBTI_COMMITTED = "Commitment to Set Targets"
SBTI_REMOVED = "Commitment Removed"


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
            return float(val.strip())
        except (ValueError, TypeError):
            return default

    def get_sdg(self, number: int) -> float:
        return self.sdg_scores.get(number, 0.0)

    def is_missing(self, *fields: str) -> bool:
        for f in fields:
            val = self._raw_data.get(f)
            if val is None or val.strip() in ("", "NA", "N/A"):
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
    - 0% armes controversées (mines antipersonnel, sous-munitions, armes chimiques/biologiques)
    - 0% producteurs de tabac
    - 0% combustibles fossiles / énergie fossile (secteur Energy exclu)
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
        if company.tob_producer:
            return False
        if company.sector == "Energy":
            return False
        return True


class DNSHControversyFilter(AbstractFilter):
    """
    Slide 42 & 50 : Principe DNSH (Do No Significant Harm).
    Exclusion des controverses sévères sur les 3 piliers Environnement, Social et Gouvernance.
    Critère : note de controverse >= 2.0 (les scores 0 et 1 correspondent aux alertes rouges MSCI).
    """

    def __init__(self):
        super().__init__(
            name="DNSH - Filtrage des Controverses Sévères",
            slide_ref="Slide 42 & 50",
            description="Exclut les entreprises ayant des controverses environnementales, sociales ou de gouvernance sévères (score < 2)."
        )

    def evaluate(self, company: Company) -> bool:
        return (
            company.env_controversy >= 2.0
            and company.soc_controversy >= 2.0
            and company.gov_controversy >= 2.0
        )


class GoodGovernanceAndRatingFilter(AbstractFilter):
    """
    Slide 41, 45 & 50 : Pratiques de Bonne Gouvernance (SFDR Art. 2(17) condition 3).
    - Exclusion des pires notations ESG globales (notes 'CCC' et 'B' exclues)
    - Exclusion du quantile inférieur à 5% sur le Pilier Gouvernance (note G <= 3.0 / 10 exclue)
    """

    def __init__(self):
        super().__init__(
            name="Bonne Gouvernance & Notation ESG",
            slide_ref="Slide 41, 45 & 50",
            description="Exclut les notations spéculatives (CCC, B) et les notes de gouvernance inférieures ou égales à 3/10."
        )

    def evaluate(self, company: Company) -> bool:
        if company.rating in ["CCC", "B"]:
            return False
        if company.gov_pillar <= 3.0:
            return False
        return True


class ParisAlignmentITRFilter(AbstractFilter):
    """
    Slide 43 & 50 : Accord de Paris - Trajectoire de Température.
    Exclusion des entreprises dont la trajectoire climatique implicite dépasse 2.0°C.
    Permet au portefeuille d'assurer une trajectoire globale rigoureusement alignée 1.5°C.
    """

    def __init__(self, max_itr: float = 2.0):
        super().__init__(
            name="Accord de Paris - Trajectoire ITR <= 2.0°C",
            slide_ref="Slide 43 & 50",
            description=f"Exclut les entreprises dont l'ITR est strictement supérieur à {max_itr}°C."
        )
        self.max_itr = max_itr

    def evaluate(self, company: Company) -> bool:
        return company.itr <= self.max_itr


class SectorCarbonIntensityFilter(AbstractFilter):
    """
    Slide 46 & 50 : Empreinte et Intensité Carbone Sectorielle.
    Exclusion des 10% d'entreprises les plus émettrices (Scope 1+2) au sein de chaque secteur GICS.
    Garantit la sélection des meilleurs élèves intra-sectoriels sans biaiser la représentativité sectorielle.
    """

    def __init__(self, companies: List[Company], percentile: float = 0.90):
        super().__init__(
            name="Intensité Carbone Sectorielle (Top 10% exclus)",
            slide_ref="Slide 46 & 50",
            description="Exclut le décile supérieur (pire 10%) en intensité carbone Scope 1+2 au sein de chaque secteur."
        )
        self.sector_thresholds = self._compute_thresholds(companies, percentile)

    def _compute_thresholds(self, companies: List[Company], percentile: float) -> Dict[str, float]:
        by_sec = defaultdict(list)
        for c in companies:
            by_sec[c.sector].append(c.carbon_intensity_s12)

        thresholds = {}
        for sec, vals in by_sec.items():
            vals_sorted = sorted(vals)
            idx = int(percentile * len(vals_sorted))
            idx = min(idx, len(vals_sorted) - 1)
            thresholds[sec] = vals_sorted[idx]
        return thresholds

    def evaluate(self, company: Company) -> bool:
        thresh = self.sector_thresholds.get(company.sector, float("inf"))
        return company.carbon_intensity_s12 <= thresh


class ClimateSDGFilter(AbstractFilter):
    """
    Slide 47 & 50 : ODD Climatiques et Environnementaux.
    Exclusion des entreprises ayant un alignement net fortement négatif sur les ODD 7, 12 ou 13
    (ODD 7: Énergie propre, ODD 12: Consommation responsable, ODD 13: Climat).
    Seuil : score net d'alignement >= -1.0.
    """

    def __init__(self):
        super().__init__(
            name="ODD Environnementaux (ODD 7, 12, 13)",
            slide_ref="Slide 47 & 50",
            description="Exclut les entreprises portant atteinte aux ODD climatiques (score < -1.0)."
        )

    def evaluate(self, company: Company) -> bool:
        s7 = company.get_sdg(7)
        s12 = company.get_sdg(12)
        s13 = company.get_sdg(13)
        return s7 >= -1.0 and s12 >= -1.0 and s13 >= -1.0


class PositiveContributionFilter(AbstractFilter):
    """
    Slide 13 & SFDR Article 2(17) : Contribution Positive Substantielle.
    Pour notre fonds thématique HealthTech & IA, l'entreprise doit obligatoirement contribuer
    de manière positive et mesurable :
    - Voie Sociale / Santé (Thèse HealthTech) : ODD 3 (Santé) >= 1.0 ou ODD 9 (Innovation IA) >= 1.0,
      ou ODD fondamentaux >= 1.5.
    - Voie Environnementale / Climat (Slide 13 & SBTi) : Taxonomie >= 20% OU Cible de réduction validée par SBTi
      ('Validated Targets') OU Clean Tech >= 10% OU trajectoire exemplaire ITR <= 1.5°C.
    """

    def __init__(self, sbti_by_isin: Optional[Dict[str, Dict[str, str]]] = None, min_taxonomy_rev: float = 20.0):
        super().__init__(
            name="Contribution Positive Substantielle (SFDR Art. 2(17) - Santé & Climat)",
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
    4. Secteur Consumer Staples : Hygiène préventive et nutrition médicale (ODD 3 >= 2.0).
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

        # 1. Santé au sens large (Pharma, Biotech, Dispositifs médicaux)
        if sec == "Health Care":
            return True

        # 2. Technologies & Enablers d'IA médicale
        if sec == "Information Technology":
            if s3 >= 1.0:
                return True
            if s9 >= 1.0 and any(t in ind for t in ["software", "semiconductors", "computers", "electronics"]):
                return True

        # 3. Équipements de précision industrielle, instrumentation & fluides biopharma
        if sec == "Industrials":
            if s3 >= 1.0:
                return True
            if any(t in name for t in ["pentair", "mettler", "halma", "cummins", "siemens"]):
                return True

        # 4. Nutrition et santé préventive
        if sec == "Consumer Staples":
            if s3 >= 2.0:
                return True

        return False


class FinancialQualityFilter(AbstractFilter):
    """
    Slide 59 & 62 : Univers Financier Quantitatif (Théorie du FCF de Jensen 1986).
    Élimine les entreprises spéculatives non rentables, surendettées ou destructrices de valeur :
    - Rentabilité économique : ROE > 5% OU ROIC > 5% OU marge nette > 5%
    - Maîtrise de la solvabilité : Debt/Assets < 65%
    - Efficience financière : Ratio de Sharpe 5Y >= 0.10 et rendement annualisé 5Y > 0%
    """

    def __init__(self):
        super().__init__(
            name="Univers Financier Quantitatif (Jensen FCF & Qualité)",
            slide_ref="Slide 59 & 62",
            description="Exclut les entreprises déficitaires, surendettées ou sans création de valeur financière pérenne."
        )

    def evaluate(self, company: Company) -> bool:
        is_profitable = (company.roe > 5.0) or (company.roic > 5.0) or (company.net_margin > 5.0)
        is_solvent = company.debt_assets < 65.0
        good_sharpe = company.sharpe_5y >= 0.10
        positive_return = company.return_5y > 0.0

        return is_profitable and is_solvent and good_sharpe and positive_return
