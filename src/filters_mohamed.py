"""
MODULE DE FILTRAGE ORIENTÉ OBJET (POO) - SÉLECTION SFDR ARTICLE 9 & PAB - VERSION MOHAMED
-----------------------------------------------------------------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry BÉCHU & Jean JARDEL (Kanopy AM)

Version Mohamed, conservée à côté de la version officielle (src/filters.py de Daphné).
Elle est utilisée par src/run_tri_mohamed.py.

Basé sur le cours 'Finance Durable - Approche Quantitative' (Jean Jardel, 2026),
règles appliquées telles qu'elles sont en vigueur à la date des données (31/12/2024) :
  - Slide 13 : SFDR Article 2(17) = Bonne gouvernance ET DNSH ET contribution positive
               (>= 20% du CA dans des activités durables OU objectif de réduction validé par SBTi)
  - Slide 41 : Article 9 - Bonne gouvernance (Exclusion des notes ESG < BB : B et CCC)
  - Slide 42 : Article 9 - DNSH (Exclusion des notes de controverse E, S ou G < 2/10)
  - Slide 43 & 50 : Accord de Paris - Température (Exclusion ITR >= Q80%, règle en vigueur depuis février 2024)
  - Slide 44 : Dénomination du fonds - Exclusions PAB (Armes controversées, Pétrole, Charbon, Tabac)
  - Slide 45 & 50 : Pilier E - Exclusion des notes strictement inférieures au quantile à 5% (E < Q5%, 3/10)
  - Slide 46 : Empreinte ET intensité carbone Scope 1+2+3 (Exclusion du pire décile de chaque secteur)
  - Slide 47 : ODD 7, 12 et 13 (Exclusion des entreprises non alignées : score = -10)
  - Slide 50 (note 1) : les entreprises sans donnée sont éliminées pour chaque filtre
  - Slide 62 : Intersection des 3 univers (Venn) :
               Univers Financier Quantitatif ∩ Univers Extra-Financier ∩ Univers Thématique Discrétionnaire
"""  # Modif Mohamed

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from collections import defaultdict


# Champs utilisés par les filtres extra-financiers  # Modif Mohamed
CONTROVERSY_FIELDS = ("ENVIRONMENT_CONTROVERSY_SCORE", "SOCIAL_CONTROVERSY_SCORE", "GOVERNANCE_CONTROVERSY_SCORE")  # Modif Mohamed
INTENSITY_FIELDS = ("INTENSITY_SCOPE_1", "INTENSITY_SCOPE_2", "INTENSITY_SCOPE_3")  # Modif Mohamed
FOOTPRINT_FIELDS = ("FOOTPRINT_SCOPE_1", "FOOTPRINT_SCOPE_2", "FOOTPRINT_SCOPE_3")  # Modif Mohamed
CLIMATE_SDGS = (7, 12, 13)  # Modif Mohamed

# Statuts officiels de la base SBTi (Target Dashboard, fichier "companies") ; les statuts de la photo  # Modif Mohamed
# du 13/01/2025 sont traduits dans ce vocabulaire par load_sbti_snapshot_by_isin (run_tri_mohamed.py)  # Modif Mohamed
SBTI_STATUS_FIELDS = ("near_term_status", "long_term_status", "net_zero_status")  # Modif Mohamed
SBTI_VALIDATION_FIELDS = ("near_term_status", "long_term_status")  # seuls ces statuts valent validation  # Modif Mohamed
SBTI_VALIDATED = "Validated Targets"           # objectif validé par SBTi  # Modif Mohamed
SBTI_COMMITTED = "Commitment to Set Targets"   # simple engagement, pas encore validé  # Modif Mohamed
SBTI_REMOVED = "Commitment Removed"            # engagement retiré ou expiré  # Modif Mohamed


def quantile(values: List[float], q: float) -> float:  # Modif Mohamed
    """Quantile par interpolation linéaire (même convention que numpy / pandas)."""  # Modif Mohamed
    xs = sorted(values)  # Modif Mohamed
    h = (len(xs) - 1) * q  # Modif Mohamed
    lo = int(h)  # Modif Mohamed
    hi = min(lo + 1, len(xs) - 1)  # Modif Mohamed
    t = h - lo  # Modif Mohamed
    if t >= 0.5:  # Modif Mohamed
        return xs[hi] - (xs[hi] - xs[lo]) * (1 - t)  # Modif Mohamed
    return xs[lo] + (xs[hi] - xs[lo]) * t  # Modif Mohamed


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
        self.carbon_intensity_s123 = self.carbon_intensity_s12 + self.intensity_s3  # Modif Mohamed
        self.footprint_s1 = self._parse_float("FOOTPRINT_SCOPE_1")  # Modif Mohamed
        self.footprint_s2 = self._parse_float("FOOTPRINT_SCOPE_2")  # Modif Mohamed
        self.footprint_s3 = self._parse_float("FOOTPRINT_SCOPE_3")  # Modif Mohamed
        self.carbon_footprint_s123 = self.footprint_s1 + self.footprint_s2 + self.footprint_s3  # Modif Mohamed

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

    def is_missing(self, *fields: str) -> bool:  # Modif Mohamed
        """True si au moins un des champs est vide (donnée manquante => exclusion, slide 50)."""  # Modif Mohamed
        return any(self._raw_data.get(f, "").strip() in ("", "NA", "N/A") for f in fields)  # Modif Mohamed

    def get_sdg(self, number: int) -> float:
        return self.sdg_scores.get(number, 0.0)

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
    - Armes controversées (CWEAP_TIE = 1 ; champ renseigné uniquement pour les entreprises impliquées)
    - Tabac (TOB_PRODUCER = 1 ; donnée manquante => exclusion)
    - Pétrole & charbon : le fichier ne donne pas la part du CA fossile, proxy = secteur Energy exclu
    """  # Modif Mohamed

    def __init__(self):
        super().__init__(
            name="Exclusions PAB & Combustibles Fossiles",
            slide_ref="Slide 44 & 50",
            description="Exclut les armes controversées, le tabac et les entreprises du secteur Énergie."
        )

    def evaluate(self, company: Company) -> bool:
        if company.cweap_tie:
            return False
        if company.tob_producer or company.is_missing("TOB_PRODUCER"):  # Modif Mohamed
            return False
        if company.sector == "Energy":
            return False
        return True


class DNSHControversyFilter(AbstractFilter):
    """
    Slide 42 & 50 : Principe DNSH (Do No Significant Harm).
    Exclusion des controverses sévères sur les 3 piliers Environnement, Social et Gouvernance.
    Critère : note de controverse >= 2.0 (les scores 0 et 1 correspondent aux alertes rouges MSCI).
    Donnée de controverse manquante => exclusion.
    """  # Modif Mohamed

    def __init__(self):
        super().__init__(
            name="DNSH - Filtrage des Controverses Sévères",
            slide_ref="Slide 42 & 50",
            description="Exclut les entreprises ayant des controverses environnementales, sociales ou de gouvernance sévères (score < 2)."
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing(*CONTROVERSY_FIELDS):  # Modif Mohamed
            return False  # Modif Mohamed
        return (
            company.env_controversy >= 2.0
            and company.soc_controversy >= 2.0
            and company.gov_controversy >= 2.0
        )


class GoodGovernanceAndRatingFilter(AbstractFilter):
    """
    Slide 41 & 50 : Article 9 - Bonne Gouvernance (SFDR Art. 2(17)).
    - Exclusion des notes ESG < BB (notes 'B' et 'CCC')
    - Note ESG manquante => exclusion
    """  # Modif Mohamed

    def __init__(self):
        super().__init__(
            name="Bonne Gouvernance - Notation ESG >= BB",  # Modif Mohamed
            slide_ref="Slide 41 & 50",  # Modif Mohamed
            description="Exclut les notations ESG inférieures à BB (B, CCC) et les entreprises non notées."  # Modif Mohamed
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing("IVA_COMPANY_RATING"):  # Modif Mohamed
            return False  # Modif Mohamed
        if company.rating in ["CCC", "B"]:
            return False
        return True


class ParisAlignmentITRFilter(AbstractFilter):
    """
    Slide 43 & 50 : Accord de Paris - Exclusions de température.
    Règle en vigueur depuis février 2024 (donc à la date des données, 31/12/2024) :
    exclusion des 20% d'entreprises les plus chaudes, c'est-à-dire ITR >= Q80% de l'univers.
    (L'ancienne règle « ITR > 2°C » n'est plus appliquée.) ITR manquant => exclusion.
    """  # Modif Mohamed

    def __init__(self, companies: List[Company], quantile_level: float = 0.80):  # Modif Mohamed
        self.max_itr = quantile([c.itr for c in companies if not c.is_missing("ITR")], quantile_level)  # Modif Mohamed
        super().__init__(
            name=f"Accord de Paris - ITR < Q{int(quantile_level * 100)}% ({self.max_itr:.1f}°C)",  # Modif Mohamed
            slide_ref="Slide 43 & 50",
            description=f"Exclut les entreprises dont l'ITR est supérieur ou égal à {self.max_itr:.1f}°C (Q{int(quantile_level * 100)}%)."  # Modif Mohamed
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing("ITR"):  # Modif Mohamed
            return False  # Modif Mohamed
        return company.itr < self.max_itr  # Modif Mohamed


class EnvironmentalPillarFilter(AbstractFilter):  # Modif Mohamed
    """
    Slide 45 & 50 : Exclusions complémentaires - Pilier E.
    Règle « Note du pilier E < Q5% » (slide 50) : exclusion des notes du pilier Environnement
    strictement inférieures au quantile à 5% (3/10) ; une note égale au quantile est conservée.
    Pilier E manquant => exclusion.
    """  # Modif Mohamed

    def __init__(self, companies: List[Company], quantile_level: float = 0.05):  # Modif Mohamed
        self.min_score = quantile([c.env_pillar for c in companies if not c.is_missing("ENVIRONMENTAL_PILLAR_SCORE")],  # Modif Mohamed
                                  quantile_level)  # Modif Mohamed
        super().__init__(  # Modif Mohamed
            name=f"Pilier E >= Q{int(quantile_level * 100)}% ({self.min_score:.1f}/10)",  # Modif Mohamed
            slide_ref="Slide 45 & 50",  # Modif Mohamed
            description=f"Exclut les notes du pilier E strictement inférieures à {self.min_score:.1f}/10."  # Modif Mohamed
        )  # Modif Mohamed

    def evaluate(self, company: Company) -> bool:  # Modif Mohamed
        if company.is_missing("ENVIRONMENTAL_PILLAR_SCORE"):  # Modif Mohamed
            return False  # Modif Mohamed
        return company.env_pillar >= self.min_score  # Modif Mohamed


class SectorCarbonIntensityFilter(AbstractFilter):
    """
    Slide 46 & 50 : Intensité Carbone Sectorielle (tCO2e / M$ de chiffre d'affaires).
    Exclusion des 10% d'entreprises les plus émettrices (Scope 1+2+3) au sein de chaque secteur GICS.
    Seuils calculés sur l'univers complet. Donnée carbone manquante => exclusion.
    """  # Modif Mohamed

    fields = INTENSITY_FIELDS  # Modif Mohamed
    label = "Intensité"  # Modif Mohamed

    def __init__(self, companies: List[Company], percentile: float = 0.90):
        super().__init__(
            name=f"{self.label} Carbone Sectorielle S1+2+3 (Top 10% exclus)",  # Modif Mohamed
            slide_ref="Slide 46 & 50",
            description=f"Exclut le décile supérieur (pire 10%) en {self.label.lower()} carbone Scope 1+2+3 au sein de chaque secteur."  # Modif Mohamed
        )
        self.sector_thresholds = self._compute_thresholds(companies, percentile)

    def value(self, company: Company) -> float:  # Modif Mohamed
        return company.carbon_intensity_s123  # Modif Mohamed

    def _compute_thresholds(self, companies: List[Company], percentile: float) -> Dict[str, float]:
        by_sec = defaultdict(list)
        for c in companies:
            if not c.is_missing(*self.fields):  # Modif Mohamed
                by_sec[c.sector].append(self.value(c))  # Modif Mohamed
        return {sec: quantile(vals, percentile) for sec, vals in by_sec.items()}  # Modif Mohamed

    def evaluate(self, company: Company) -> bool:
        if company.is_missing(*self.fields):  # Modif Mohamed
            return False  # Modif Mohamed
        thresh = self.sector_thresholds.get(company.sector, float("inf"))
        return self.value(company) <= thresh  # Modif Mohamed


class SectorCarbonFootprintFilter(SectorCarbonIntensityFilter):  # Modif Mohamed
    """
    Slide 46 & 50 : Empreinte Carbone Sectorielle (tCO2e / M$ investi, rapportée à la valeur d'entreprise).
    Même règle que l'intensité : exclusion du pire décile Scope 1+2+3 de chaque secteur.
    """  # Modif Mohamed

    fields = FOOTPRINT_FIELDS  # Modif Mohamed
    label = "Empreinte"  # Modif Mohamed

    def value(self, company: Company) -> float:  # Modif Mohamed
        return company.carbon_footprint_s123  # Modif Mohamed


class ClimateSDGFilter(AbstractFilter):
    """
    Slide 47 & 50 : ODD Climatiques et Environnementaux.
    Exclusion des entreprises non alignées aux ODD climatiques 7, 12 ou 13
    (ODD 7: Énergie propre, ODD 12: Consommation responsable, ODD 13: Climat).
    Critère du cours : score net d'alignement = -10 sur l'un des trois ODD. Score manquant => exclusion.
    """  # Modif Mohamed

    def __init__(self):
        super().__init__(
            name="ODD Environnementaux (ODD 7, 12, 13)",
            slide_ref="Slide 47 & 50",
            description="Exclut les entreprises non alignées aux ODD climatiques (score = -10) ou sans donnée."  # Modif Mohamed
        )

    def evaluate(self, company: Company) -> bool:
        if company.is_missing(*(f"SDG_{k:02d}_NET_ALIGNMENT_SCORE" for k in CLIMATE_SDGS)):  # Modif Mohamed
            return False  # Modif Mohamed
        return all(company.get_sdg(k) > -10.0 for k in CLIMATE_SDGS)  # Modif Mohamed


class PositiveContributionFilter(AbstractFilter):
    """
    Slide 13 : SFDR Article 2(17) - Contribution positive.
    Un investissement durable = Bonne gouvernance (filtre slide 41) ET DNSH (filtre slide 42)
    ET contribution positive. Ce filtre vérifie la contribution positive :
    - Au moins 20% du chiffre d'affaires dans des activités durables
      (proxy : CA aligné Taxonomie UE, EST_EU_TAXONOMY_MAX_REV >= 20)
    - OU un objectif de réduction des émissions validé par SBTi au 31/12/2024
      (photo SBTi du 13/01/2025 déjà jointe à notre univers : data/sbti/msci_world_jointure_sbti_2025-01-13.csv,
      lue par load_sbti_snapshot_by_isin dans run_tri_mohamed.py ; option commentée : base de novembre 2026
      data/sbti/companies-excel.csv + rapprochements par nom SBTI_NAME_MATCHES - Modif Mohamed)
    Règle de validation SBTi : near_term_status == 'Validated Targets' OU long_term_status == 'Validated Targets'.
    Un simple engagement ('Commitment to Set Targets'), un engagement retiré ('Commitment Removed'),
    une absence de la base SBTi ou une donnée manquante ne sont jamais considérés comme une validation.
    """  # Modif Mohamed

    def __init__(self, sbti_by_isin: Dict[str, Dict[str, str]], min_taxonomy_rev: float = 20.0):  # Modif Mohamed
        super().__init__(
            name="Contribution Positive (Taxo >= 20% ou SBTi validé)",  # Modif Mohamed
            slide_ref="Slide 13",  # Modif Mohamed
            description="Exige >= 20% du CA aligné Taxonomie UE ou un objectif de réduction des émissions validé par SBTi."  # Modif Mohamed
        )
        self.sbti_by_isin = sbti_by_isin  # Modif Mohamed
        self.min_taxonomy_rev = min_taxonomy_rev  # Modif Mohamed

    def sbti_status(self, company: Company) -> str:  # Modif Mohamed
        """Statut SBTi de l'entreprise, retrouvée par son ISIN."""  # Modif Mohamed
        record = self.sbti_by_isin.get(company.isin.upper())  # Modif Mohamed
        if record is None:  # Modif Mohamed
            return "Absent de la base SBTi"  # Modif Mohamed
        if any(record.get(f, "").strip() == SBTI_VALIDATED for f in SBTI_VALIDATION_FIELDS):  # Modif Mohamed
            return "Objectif validé"  # Modif Mohamed
        statuses = [record.get(f, "").strip() for f in SBTI_STATUS_FIELDS]  # Modif Mohamed
        if SBTI_VALIDATED in statuses:  # Modif Mohamed
            return "Net zéro validé seul (non retenu)"  # Modif Mohamed
        if SBTI_COMMITTED in statuses:  # Modif Mohamed
            return "Engagement seulement (non validé)"  # Modif Mohamed
        if SBTI_REMOVED in statuses:  # Modif Mohamed
            return "Engagement retiré"  # Modif Mohamed
        return "Statut non renseigné"  # Modif Mohamed

    def has_sbti_validated_target(self, company: Company) -> bool:  # Modif Mohamed
        return self.sbti_status(company) == "Objectif validé"  # Modif Mohamed

    def has_sustainable_revenue(self, company: Company) -> bool:  # Modif Mohamed
        if company.is_missing("EST_EU_TAXONOMY_MAX_REV"):  # Modif Mohamed
            return False  # Modif Mohamed
        return company.eu_taxonomy_rev >= self.min_taxonomy_rev  # Modif Mohamed

    def evaluate(self, company: Company) -> bool:
        return self.has_sustainable_revenue(company) or self.has_sbti_validated_target(company)  # Modif Mohamed


class HealthTechAIScopeFilter(AbstractFilter):
    """
    Slide 62 : Univers Thématique Discrétionnaire (Notre Scope : HealthTech & AI).
    Sélectionne les entreprises qui participent à la convergence de la santé et de l'intelligence artificielle :
    1. Secteur Health Care : Biotechnologies, Pharmaceutiques, Dispositifs médicaux, Diagnostics, Robotique chirurgicale.
    2. Secteur Information Technology : Fournisseurs de capacités d'IA, semi-conducteurs spécialisés, calcul haute performance,
       logiciels de bio-informatique et simulation moléculaire (alignement ODD 9 >= 1.0 ou ODD 3 >= 1.0).
    3. Secteur Industrials : Équipements de laboratoire, filtration d'eau et fluides critiques pour la biopharmacie.
    4. Secteur Consumer Staples : Hygiène préventive et nutrition médicale (ODD 3 >= 2.0).
    Choix discrétionnaire (Modif Mohamed, identique à la version officielle) : Ansys, sous offre de rachat de
    Synopsys au 31/12/2024, est écartée et remplacée par PTC (logiciels de conception et de simulation).
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

        # 0. Titre sous offre de rachat définitive au 31/12/2024, écarté car il va quitter la cote :  # Modif Mohamed
        #    Ansys (rachat par Synopsys annoncé le 16/01/2024, finalisé en juillet 2025 : plus aucun cours ensuite)  # Modif Mohamed
        if any(t in name for t in ["ansys"]):  # Modif Mohamed
            return False  # Modif Mohamed

        # 1. Santé au sens large (Pharma, Biotech, Dispositifs médicaux)
        if sec == "Health Care":
            return True

        # 2. Technologies & Enablers d'IA médicale
        if sec == "Information Technology":
            if s3 >= 1.0:
                return True
            if s9 >= 1.0 and any(t in ind for t in ["software", "semiconductors", "computers", "electronics"]):
                return True
            # Remplaçant d'Ansys : PTC, logiciels de conception (CAO, PLM) et de simulation comme Ansys,  # Modif Mohamed
            # utilisés par les fabricants de dispositifs médicaux (même choix que la version officielle)  # Modif Mohamed
            if any(t in name for t in ["ptc inc"]):  # Modif Mohamed
                return True  # Modif Mohamed

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


# ------------------------------------------------------------------------------------------------  # Modif Mohamed
# OPTIONS DE FILTRE THÉMATIQUE À FAIRE CHOISIR PAR LE GROUPE (désactivées)                          # Modif Mohamed
# Pour activer une option :                                                                         # Modif Mohamed
#   1. décommenter la classe choisie ci-dessous (pour V6b, décommenter aussi V3 : V6b en hérite),   # Modif Mohamed
#   2. dans src/run_tri_mohamed.py, décommenter son import et remplacer thematic_filter = ... (lignes prêtes). # Modif Mohamed
# Résultats simulés (données et SBTi au 31/12/2024, filtre financier qualité, même optimiseur) :   # Modif Mohamed
#   - V3  : 32 lignes, Santé 65,2% / Tech 34,8%                                                     # Modif Mohamed
#   - V6b : 35 lignes, Santé 54,0% / Tech 32,5% / Industrie 13,5%                                   # Modif Mohamed
# ------------------------------------------------------------------------------------------------  # Modif Mohamed

# class HealthTechAIScopeFilterV3(AbstractFilter):  # Modif Mohamed
#     """
#     Slide 62 : Univers Thématique - Option V3 « Santé + Tech IA ».
#     1. Santé : tout le secteur Health Care.
#     2. Tech IA : secteur Information Technology, uniquement les semi-conducteurs (calcul IA)
#        et une liste discrétionnaire de logiciels de conception de puces et de simulation.
#     Industrie et Consommation de base exclues.
#     """  # Modif Mohamed
#
#     AI_SOFTWARE = ["cadence design", "synopsys", "dassault systemes", "ptc inc"]  # liste discrétionnaire (Microsoft à discuter ; PTC remplace Ansys, rachetée)  # Modif Mohamed
#
#     def __init__(self):  # Modif Mohamed
#         super().__init__(  # Modif Mohamed
#             name="Univers Thématique V3 - Santé + Tech IA",  # Modif Mohamed
#             slide_ref="Slide 62 (Univers Thématique)",  # Modif Mohamed
#             description="Santé (secteur Health Care) + semi-conducteurs et logiciels de conception / simulation."  # Modif Mohamed
#         )  # Modif Mohamed
#
#     def evaluate(self, company: Company) -> bool:  # Modif Mohamed
#         # 1. Santé : tout le secteur Health Care  # Modif Mohamed
#         if company.sector == "Health Care":  # Modif Mohamed
#             return True  # Modif Mohamed
#         # 2. Tech IA : semi-conducteurs + logiciels de conception / simulation  # Modif Mohamed
#         if company.sector == "Information Technology":  # Modif Mohamed
#             if company.industry_group == "Semiconductors":  # Modif Mohamed
#                 return True  # Modif Mohamed
#             if any(n in company.name.lower() for n in self.AI_SOFTWARE):  # Modif Mohamed
#                 return True  # Modif Mohamed
#         return False  # Modif Mohamed


# class HealthTechAIScopeFilterV6b(HealthTechAIScopeFilterV3):  # Modif Mohamed
#     """
#     Slide 62 : Univers Thématique - Option V6b « V3 + industriels choisis ».
#     Option V3, plus une liste discrétionnaire d'industriels liés à la santé ou à l'infrastructure de l'IA :
#     - Santé : Lifco (dentaire), Wolters Kluwer (UpToDate, aide à la décision clinique),
#       RELX (Elsevier, données médicales et scientifiques)
#     - Infrastructure IA : Schneider Electric et Legrand (alimentation des data centers),
#       VAT Group (vannes pour la fabrication de puces)
#     """  # Modif Mohamed
#
#     INDUSTRIALS = ["lifco", "wolters kluwer", "relx", "schneider electric", "legrand", "vat group"]  # liste discrétionnaire  # Modif Mohamed
#
#     def __init__(self):  # Modif Mohamed
#         super().__init__()  # Modif Mohamed
#         self.name = "Univers Thématique V6b - Santé + Tech IA + Industrie choisie"  # Modif Mohamed
#         self.description = "Option V3 + industriels liés à la santé ou à l'infrastructure de l'IA (liste discrétionnaire)."  # Modif Mohamed
#
#     def evaluate(self, company: Company) -> bool:  # Modif Mohamed
#         if super().evaluate(company):  # Modif Mohamed
#             return True  # Modif Mohamed
#         # 3. Industrie : uniquement la liste choisie  # Modif Mohamed
#         return company.sector == "Industrials" and any(n in company.name.lower() for n in self.INDUSTRIALS)  # Modif Mohamed


# ------------------------------------------------------------------------------------------------  # Modif Mohamed
# FILTRE FINANCIER - nouvelle version (la version d'origine est conservée plus bas,                 # Modif Mohamed
# sous le nom FinancialQualityFilterDaphne). Pourquoi ces changements :                              # Modif Mohamed
#  - Plus de sélection sur la performance boursière passée (Sharpe et rendement 5 ans) : c'était    # Modif Mohamed
#    un filtre de momentum (17 exclusions sur 24 dues à la seule performance passée : CSL,           # Modif Mohamed
#    Coloplast, Zimmer Biomet...), source de biais in-sample avec le backtest sur la même période,    # Modif Mohamed
#    et un message contraire à la mention AMF « les performances passées ne préjugent pas des        # Modif Mohamed
#    performances futures ».                                                                         # Modif Mohamed
#  - Le FCF (annoncé « Jensen FCF » mais jamais utilisé) est réellement appliqué : FCF yield > 0.    # Modif Mohamed
#    Cummins, Lonza et Elevance avaient un FCF négatif et étaient en portefeuille.                    # Modif Mohamed
#  - Le ROE est retiré : non fiable dans les données (jusqu'à 22 574 % avec des fonds propres ~ 0).  # Modif Mohamed
#  - Un critère de risque remplace la performance : exclusion des 10 % de titres les plus volatils.  # Modif Mohamed
#  - Donnée manquante => exclusion (même règle que les filtres extra-financiers, slide 50).          # Modif Mohamed
#  - Marketing : « durabilité financière » (slide 5 : double durabilité extra-financière et          # Modif Mohamed
#    financière) = entreprises rentables, qui génèrent du cash et peu endettées.                     # Modif Mohamed
# ------------------------------------------------------------------------------------------------  # Modif Mohamed
class FinancialQualityFilter(AbstractFilter):  # Modif Mohamed
    """
    Slide 59 & 62 : Univers Financier Quantitatif (« durabilité financière », slide 5).
    - Rentabilité : ROIC > 5% OU marge nette > 5%
    - Génération de cash : FCF yield > 0
    - Solvabilité : Debt/Assets < 65%
    - Risque : exclusion des 10% de titres les plus volatils du MSCI World (volatilité 5 ans)
    - Donnée manquante => exclusion
    """  # Modif Mohamed

    fields = ("ROIC", "Net margin", "FCF yield", "Debt assets", "Volatility 5Y")  # Modif Mohamed

    def __init__(self, companies: List[Company], vol_percentile: float = 0.90):  # Modif Mohamed
        self.max_volatility = quantile([c.volatility_5y for c in companies if not c.is_missing("Volatility 5Y")],  # Modif Mohamed
                                       vol_percentile)  # Modif Mohamed
        super().__init__(  # Modif Mohamed
            name="Univers Financier Quantitatif (Qualité & Cash)",  # Modif Mohamed
            slide_ref="Slide 59 & 62",  # Modif Mohamed
            description=f"Garde les entreprises rentables, à FCF positif, peu endettées et de volatilité <= {self.max_volatility:.1%}."  # Modif Mohamed
        )  # Modif Mohamed

    def evaluate(self, company: Company) -> bool:  # Modif Mohamed
        if company.is_missing(*self.fields):  # donnée manquante => exclusion  # Modif Mohamed
            return False  # Modif Mohamed
        is_profitable = (company.roic > 5.0) or (company.net_margin > 5.0)  # ROE retiré (non fiable)  # Modif Mohamed
        generates_cash = company.fcf_yield > 0.0  # FCF réellement appliqué  # Modif Mohamed
        is_solvent = company.debt_assets < 65.0  # règle inchangée  # Modif Mohamed
        not_too_volatile = company.volatility_5y <= self.max_volatility  # risque au lieu de la performance passée  # Modif Mohamed
        return is_profitable and generates_cash and is_solvent and not_too_volatile  # Modif Mohamed


# Version d'origine (Daphne), conservée pour mémoire : elle n'est plus utilisée par le pipeline.  # Modif Mohamed
# Pour la réactiver : dans src/run_tri_mohamed.py, utiliser la ligne commentée financial_filter = FinancialQualityFilterDaphne().  # Modif Mohamed
class FinancialQualityFilterDaphne(AbstractFilter):  # ancienne FinancialQualityFilter, renommée  # Modif Mohamed
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
