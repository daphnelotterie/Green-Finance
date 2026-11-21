# Méthodologie, modifications et chronologie

Ce document regroupe les anciennes notes de stratégie, de réglementation, de filtres et de modifications. Il conserve les choix et les étapes du travail de Daphné et Mohamed, tout en distinguant les chiffres historiques des résultats recalculés dans [Résultats](resultats.md).

## 1. Objectif et périmètre

Synapse HealthTech & AI est un projet de fonds actions international du Master 272, encadré par les cours de Thierry Béchu et Jean Jardel. La thèse relie les besoins de santé, les outils de diagnostic, les biotechnologies et les capacités de calcul ou de simulation nécessaires à leur développement. Les ODD 3 (santé) et 9 (innovation) servent de repères.

La construction reprend l'intersection des trois univers du cours : éligibilité extra-financière, périmètre thématique discrétionnaire et qualité financière. L'allocation intervient après cette sélection.

L'objectif Article 9 figurait dans les premières notes comme une conformité acquise. Il doit être lu comme l'ambition pédagogique du fonds : contribution positive, absence de préjudice important et bonne gouvernance sont approchées par les variables disponibles. Une note ODD, un ITR ou un statut SBTi ne suffisent pas à prouver seuls ces exigences. Le seuil de 20 % de revenus alignés Taxonomie est une règle du modèle retenue dans le projet, pas une certification juridique. L'exclusion du secteur `Energy` constitue un proxy des exclusions fossiles ; le dépôt ne démontre pas une conformité complète PAB, DNSH, PAI, AMF ou UCITS.

## 2. Données et dates

| Source | Contenu et rôle |
|---|---|
| `data/raw/all_data.csv` | 1 247 valeurs, 100 colonnes ; photographie financière et extra-financière de référence au 31/12/2024 |
| `data/raw/sbti/msci_world_jointure_sbti_2025-01-13.csv` | Rapprochement de cet univers avec la photographie SBTi du 13/01/2025, statut à fin 2024 et méthode de rapprochement |
| `data/raw/sbti/references/sbti_2025-01-13_plan_b.csv` | Photographie SBTi complète de 10 534 entreprises, conservée pour traçabilité |
| `data/raw/sbti/references/companies-excel.csv` et `.xlsx` | Sources SBTi de novembre 2026, conservées pour l'historique du rapprochement ; elles ne déterminent pas l'éligibilité à fin 2024 |
| `data/cache/prices/` | Prix ajustés locaux, taux de change et prix convertis en EUR, réutilisés pour les optimisations et backtests |

La photographie SBTi historique provient d'une archive de l'export officiel, dans le dépôt `CalibreFinancialTechnology/sbti-cta`. C'est une source secondaire de conservation de l'export ; le décalage entre le 31 décembre et le 13 janvier impose un contrôle de date. Seuls les rapprochements sûrs et les validations dont la publication avant le 31/12/2024 est confirmée sont retenus. Les notes antérieures dénombrent 506 valeurs avec validation confirmée et 11 cas à revoir écartés.

Une validation exige `Validated Targets` sur l'objectif de court ou de long terme. Un engagement simple, retiré ou absent, une information manquante et un statut net zéro seul ne sont pas assimilés à une validation. L'ancienne base de novembre 2026 aurait ajouté 89 validations postérieures à la date de référence et perdu 10 validations présentes fin 2024 : elle a donc été remplacée pour éviter ce décalage temporel.

Le premier rapprochement avec la base 2026 avait nécessité 75 correspondances par nom vérifiées à la main, notamment pour les ISIN absents, anciens ou correspondant à une autre classe d'actions. Dix-sept rapprochements trompeurs avaient été rejetés (homonymes, filiales ou mauvaise entité juridique). Ce travail explique l'historique des sources ; ces correspondances ne remplacent pas la jointure historique contrôlée utilisée aujourd'hui.

Les prix sont convertis en euros ; les cotations londoniennes en pence doivent être ramenées en livres avant change. Les jours fériés diffèrent selon les places : le dernier cours connu peut prolonger une cotation après son apparition dans l'historique, sans créer de cours avant la première observation. Essity ne dispose d'un historique propre que depuis sa scission de 2017. Les prix récents restent à contrôler, notamment le saut de PTC du 05/10/2026 signalé dans les notes initiales.

## 3. Un module de filtres, trois sélections

`src/filters.py` contient les classes partagées ; `src/run_tri.py` construit l'entonnoir selon le mode. Le mode `daphne` correspond à la version consolidée réellement présente au début de cette reprise : il inclut déjà les corrections SBTi, le filtre financier qualité, PTC et le seuil ODD 3 à 4. Il ne réactive pas le premier filtre financier fondé sur le rendement et le Sharpe. Le mode `recalibree` (stratégie A, section 9) combine les règles du cours du mode Mohamed pour la température et le pilier E, la contribution hybride du mode Daphné, le même thème et un filtre financier allégé.

Les quantiles sont calculés sur l'univers de référence, avec interpolation linéaire, et non recalculés après chaque exclusion. Les données manquantes nécessaires à un filtre entraînent l'exclusion ; une voie de contribution positive non renseignée ne vaut jamais validation.

| Étape | Règle commune ou différence |
|---|---|
| Exclusions sectorielles | Armes controversées, producteurs de tabac et secteur `Energy` exclus ; absence de donnée tabac excluante |
| Controverses | Notes environnement, social et gouvernance au moins égales à 2 ; données manquantes excluantes |
| Notation ESG | Notes `B`, `CCC` ou absentes exclues ; l'ancien seuil sur le pilier G n'est plus un filtre actif |
| Température Daphné | `ITR <= 2 °C` |
| Température Mohamed | `ITR < Q80` de l'univers, soit 3,1 °C dans les données actuelles |
| Pilier E Daphné | `E > Q5` ; l'égalité au seuil de 3,0 est exclue |
| Pilier E Mohamed | `E >= Q5` ; l'égalité à 3,0 est admise |
| Carbone | Exclusion du pire décile par secteur pour l'empreinte et pour l'intensité, chacune sur les scopes 1+2+3 |
| ODD climat | Absence de données ou score de −10 sur l'un des ODD 7, 12 et 13 excluants |
| Contribution Daphné | Voie hybride climat ou sociale, détaillée ci-dessous |
| Contribution Mohamed | Revenus alignés Taxonomie >= 20 % ou cible SBTi validée à fin 2024 |
| Thématique | Même règle HealthTech & AI dans les trois modes |
| Qualité financière | Même règle de rentabilité, FCF, dette et volatilité pour Daphné et Mohamed |
| Mode recalibré (A) | ITR < Q80 et pilier E >= Q5 comme Mohamed ; contribution hybride comme Daphné ; même thème ; filtre financier allégé : ROIC ou marge nette > 5 % et dette/actifs < 65 % |

La voie hybride Daphné retient au moins un des critères suivants : revenus Taxonomie >= 20 %, objectif SBTi validé, revenus Clean Tech >= 10 %, ITR <= 1,5 °C, ODD 3 ou 9 >= 1, ou ODD 1, 2, 4, 6 ou 11 >= 1,5. Elle permet une contribution sociale que la règle climatique stricte ne mesure pas directement. Elle reste un choix de modélisation à justifier.

Le filtre thématique conserve :

- tout le secteur santé ;
- en technologie, un ODD 3 >= 1, ou un ODD 9 >= 1 dans les logiciels, semi-conducteurs, informatique et électronique, ainsi que PTC retenue discrétionnairement ;
- en industrie, un ODD 3 >= 1 ou la liste Pentair, Mettler, Halma, Cummins, Siemens ;
- en consommation de base, un ODD 3 >= 4, pour limiter cette poche à une contribution forte à la santé.

Ansys est écartée dans les deux modes et remplacée par PTC dans le périmètre discrétionnaire. Les notes justifient ce choix par l'offre de rachat annoncée avant fin 2024 et par la disparition de la cotation en 2025. PTC est un éditeur de logiciels de conception et de simulation utilisé, entre autres, par les fabricants de dispositifs médicaux. Ce choix élargit la définition des fournisseurs de la santé ; il ne prouve pas que toute leur activité relève de l'IA médicale.

Le filtre financier exige `ROIC > 5 %` ou marge nette > 5 %, `FCF yield > 0`, dette/actifs < 65 %, volatilité cinq ans <= Q90 de l'univers (environ 46,9 %) et présence de toutes ces données. Le ROE est retiré en raison d'observations extrêmes dans le jeu de données. Le rendement et le Sharpe passés ne constituent plus des critères de sélection.

Le filtre financier allégé du mode recalibré retire le plafond de volatilité et l'exigence de FCF positif. Le premier excluait mécaniquement les leaders volatils (NVIDIA, AMD) alors que le risque est piloté au niveau du portefeuille ; le second écartait la pharma qui investit (Eli Lilly). Il garde 81 % du MSCI World, proche des 85 % de l'univers financier quantitatif de la slide 62 (942 sur 1 109).

À règles conservées, on obtient 56 valeurs sélectionnables dans le mode Daphné, 47 dans le mode Mohamed et 88 dans le mode recalibré (entonnoir : 1 247 → 819 après l'ITR < Q80 → 692 après les filtres ESG → 582 après la contribution hybride → 102 après le thème → 88 après le filtre financier allégé). Les anciennes notes mentionnant 45 valeurs Mohamed désignaient les positions réellement investies après une exclusion supplémentaire de l'ancien optimiseur, pas l'univers sélectionné.

## 4. Trois allocations explicites

Les quatre modes de la commande principale associent les sélections aux allocations :

| Mode pipeline | Filtrage | Optimiseur |
|---|---|---|
| `daphne_original` | Daphné consolidé | Pedersen d'origine, corrigé |
| `daphne_esg_risk` | Daphné consolidé | Budgets de risque ESG |
| `mohamed_esg_risk` | Mohamed | Budgets de risque ESG |
| `thematique_recalibree` | Recalibré (stratégie A) | 50 % tracking error minimale + 50 % diversification maximale (`te_div`) |

L'objectif de l'optimiseur d'origine reste :

$$\min_w \frac{\gamma}{2} w^T\Sigma w - w^T\mu - \theta w^T S.$$

Il utilise le rendement cinq ans du fichier source comme rendement espéré, avec `gamma = 3` et `theta = 0,04`. La covariance conserve les volatilités cinq ans et les corrélations paramétrées d'origine : 0,50 au sein d'un secteur et 0,28 entre secteurs. Cette simplification est conservée pour mesurer l'effet du changement d'optimiseur ; elle ne transforme pas les rendements historiques en prévisions fiables. Dans l'historique trimestriel, rendement et volatilité sont réestimés avec les seuls cours passés ; les règles et les scores ESG demeurent ceux de fin 2024.

Les deux optimiseurs partagent le score d'impact `S = 0,40 z(ODD3) + 0,25 z(ODD9) - 0,20 z(ITR) + 0,15 z(Gouvernance)`, standardisé sur l'univers effectivement utilisé.

L'optimiseur ESG risque ne prévoit aucun rendement. Il répartit des budgets de risque en fonction du rang de ce score d'impact : `b_i` est proportionnel à `0,5 + rang_percentile(S_i)`, avec rang moyen en cas d'égalité. La covariance est estimée sur les 156 derniers rendements hebdomadaires disponibles avant la date d'allocation, régularisée par Ledoit-Wolf et annualisée sur 52 semaines. Le prolongement des derniers cours connus est limité à dix lignes pour cette estimation. Les semaines étiquetées après la date d'allocation sont exclues, y compris une semaine partielle ; au 31/12/2024, les rendements retenus vont du 07/01/2022 au 27/12/2024. Un titre sans historique complet sur la fenêtre est écarté avec sa raison dans les diagnostics, puis la faisabilité est à nouveau contrôlée.

Son objectif est `min_y 0,5 y'Σy - somme(b_i log(y_i))`, puis `w = y / somme(y)`. Les contraintes sur les poids sont réécrites sur `y` avant la résolution. Cet objectif rapproche les contributions au risque des budgets ESG ; lorsque des contraintes deviennent actives, l'égalité exacte entre contribution et budget n'est plus garantie. Les écarts sont exportés. Il ne faut donc pas présenter cet optimiseur comme un simple portefeuille de variance minimale, ni comme HRP.

Les deux allocations imposent le plein investissement, l'absence de vente à découvert, un plafond de 4,5 % par titre, une poche santé entre 50 et 65 %, une poche technologie entre 28 et 40 %, les autres secteurs ensemble à 15 % maximum et un ITR moyen au plus égal à 1,8 °C. Pedersen conserve son minimum de 1 % par titre ; ESG risque conserve l'absence de minimum de poids, les budgets positifs intervenant dans l'objectif logarithmique. Ces contraintes sont appliquées aux dates de décision et de rebalancement ; après fin 2024, les poids dérivent sans rebalancement et peuvent dépasser ces bornes. Un contrôle de faisabilité précède l'optimisation ; une contrainte ne doit pas être abandonnée silencieusement. Le fichier `diagnostics_optimisation.json` de chaque mode consigne convergence, contraintes, covariance et exclusions éventuelles.

L'optimiseur `te_div` de la stratégie A ne prévoit pas non plus de rendement. Il calcule deux portefeuilles sous les mêmes contraintes, puis prend leur moyenne :

- **tracking error minimale** contre le MSCI World : minimiser la volatilité de l'écart de rendement avec l'ETF IWDA, à partir d'une covariance Ledoit-Wolf jointe titres + indice sur les mêmes 156 semaines. C'est l'objectif de la slide 63 du cours, qui fait coller le fonds au marché autant que les contraintes le permettent ;
- **diversification maximale** (Choueifaty et Coignard, 2008) : maximiser le rapport entre la moyenne pondérée des volatilités et la volatilité du portefeuille, sur la covariance des seuls titres. Il répartit le risque entre titres peu corrélés.

La moyenne de deux portefeuilles admissibles reste admissible, car toutes les contraintes sont linéaires. Elle réduit le risque de méthode : seule, chaque solution dépend fortement de la lecture retenue après 2024 (section 9).

Les contraintes sont celles des autres modes : plein investissement, 0 à 4,5 % par titre, santé 50-65 %, technologie 28-40 %, autres secteurs <= 15 %, ITR <= 1,8 °C. Deux s'y ajoutent :

- une intensité carbone S1+2+3 au plus égale à 50 % de celle du MSCI World (854 tCO₂e/M$ de chiffre d'affaires, poids de l'indice renormalisés sur la couverture) ;
- **un plafond de 12 % par sous-secteur.** Un sous-secteur est défini comme le couple secteur GICS + `industry_group` de `all_data.csv`, car certains libellés existent dans plusieurs secteurs. On en compte 16 dans l'univers de A.

Ces deux contraintes sont optionnelles dans `ThematicConstraints` et ne sont actives que pour ce mode. Le plafond de 12 % est une règle de diversification fixée a priori : au plus un huitième du fonds par segment. Ce n'est pas un réglage de performance (section 9). Avec le plancher de 50 % de santé, il fixe presque mécaniquement la poche santé : pharma, biotech, matériel médical et services de santé sont chacun à 12 %, soit 48 %, et la santé est exactement à 50 % à chaque rebalancement. Si le plafond devenait incompatible avec les autres contraintes, le calcul s'arrêterait avec une erreur au lieu de relâcher silencieusement une règle.

L'ITR individuel de 2,5 °C, ancien filtre caché dans l'optimiseur, est supprimé. L'éligibilité des titres dépend des filtres ; la température moyenne dépend de la contrainte du portefeuille. Les pénalités sectorielles de l'ancien solveur sont remplacées par des contraintes imposées, avec vérification de convergence et des poids finaux.

Les anciennes notes envisageaient aussi variance minimale sous contraintes d'impact, HRP avec ajustement ESG et Black-Litterman. Ces pistes restent des éléments de recherche : elles ne constituent pas des modes supplémentaires implémentés. Les cibles exploratoires ODD 3 >= 2,5, ITR <= 1,5 °C ou les ventilations sectorielles alternatives ne doivent pas être confondues avec les contraintes effectivement appliquées.

## 5. Backtest et interprétation

Les premières tables de performance combinaient des statistiques individuelles à un, cinq et dix ans de `all_data.csv`. Elles n'utilisaient pas de trajectoire de cours et ne constituaient pas un backtest de portefeuille. Les rendements annuels de 16,91 %, 18,85 % ou 14,93 % figurant dans les anciennes notes ne sont donc pas des résultats de la nouvelle exécution. Une moyenne des volatilités, drawdowns ou quantiles individuels n'est pas la statistique correspondante du portefeuille.

Le moteur terminé calcule les performances sur les séries de prix en EUR et compare chaque allocation à une équipondération du même univers ainsi qu'à l'ETF `IWDA.AS`. Cet ETF est un proxy investissable du MSCI World, avec ses frais et sa cotation propres ; les caractéristiques ESG du MSCI World sont calculées séparément à partir de l'univers source pondéré.

Il faut distinguer deux lectures :

- l'historique avant 2025 réestime les allocations avec les cours alors disponibles, mais sur un univers choisi avec les informations de fin 2024 ; il conserve donc un biais de sélection et ne constitue pas un historique intégralement sans anticipation ;
- la période à partir de 2025 utilise la décision de fin 2024 et permet une comparaison postérieure à la photographie de référence ; les données ne fournissent toutefois ni historique complet de composition de l'indice ni preuve exhaustive des dates de disponibilité des fondamentaux.

Après 2024, deux lectures sont produites pour chaque mode. `hors_echantillon` conserve le nombre de parts acheté le 31/12/2024. `hors_echantillon_rebalance` simule une gestion active : poids de constitution, puis réoptimisation à chaque fin de trimestre avec les seuls cours connus à la date, frais de 10 pb. L'univers et les scores ESG restent ceux de fin 2024, faute de données plus récentes. Les rendements mensuels de chaque période sont exportés (`performances_mensuelles.csv` par mode, `performances_mensuelles_modes.csv` pour la comparaison).

L'historique prévoit une réoptimisation trimestrielle et 10 points de base de frais sur les montants achetés et vendus, hors investissement initial ; il ne comprend pas de frais de gestion. La période après 2024 conserve le nombre de parts acheté à la constitution : les poids dérivent ensuite avec les cours, sans rebalancement. La performance annualisée utilise la durée calendaire, la volatilité et les indicateurs relatifs utilisent les rendements hebdomadaires annualisés sur 52 semaines ; le drawdown est calculé sur les valorisations quotidiennes. Le taux sans risque de 2 % est une hypothèse fixe du ratio de Sharpe.

Les taxes, la liquidité, la disponibilité réelle des titres et les effets des choix de traitement des cours limitent l'interprétation. Les scores ESG et l'ITR présentés sont des caractéristiques à la date de constitution, pas une mesure de leur évolution ni une preuve d'impact causé par l'investissement.

## 6. Chronologie des contributions

| Étape | Évolution et raison |
|---|---|
| Première version Daphné | Thèse HealthTech & AI, classes de filtres, optimiseur rendement/risque/impact et comparaison de statistiques source. Référence historique de 50 titres, avec plusieurs documents exploratoires indiquant aussi 35, 57 ou 77 valeurs selon l'étape. |
| 20/11/2026, Mohamed | Alignement des filtres sur les slides 41 à 50 : données manquantes excluantes, pilier E, carbone scopes 1+2+3, ODD climat à −10 ; contribution stricte Taxonomie/SBTi et rapprochements par ISIN/nom. |
| 21/11/2026, Daphné v2 | Reprise des règles communes, contribution hybride santé/climat et ITR individuel <= 2 °C. |
| 21/11/2026, SBTi historique | Remplacement de la base novembre 2026 par les statuts confirmés à fin 2024 ; la version officielle passe historiquement de 50 à 49 titres. |
| 21/11/2026, qualité financière | Remplacement du filtre rendement/Sharpe/ROE par rentabilité, FCF positif, dette et volatilité. Application réelle de la génération de cash et retrait des ROE peu fiables. |
| 21/11/2026, PTC et prix | PTC remplace Ansys dans la sélection ; ajout du chargeur de prix et du change. La version officielle atteint 61 titres. |
| 21/11/2026, cohérence thématique | ODD 3 relevé de 2 à 4 en consommation de base : exclusion de Kirin, Kao, Church & Dwight, Clorox et Orkla ; 56 valeurs Daphné. Eli Lilly et Vertex restent écartées par le FCF négatif, malgré leur rentabilité. |
| Reprise et nettoyage | Modules par personne fusionnés ; modes explicites ; sources, cache et sorties séparés ; orchestration des trois variantes, vérification des optimiseurs, backtests sur prix et graphiques ; documentation regroupée en trois Markdown. |
| 21/11/2026, recherche de performance et stratégie A | Cours de tout l'univers téléchargés hors dépôt, environ 1 600 configurations filtres × pondérations testées, diagnostic (Brinson, biais de survivance, changement de régime). Ajout du mode `thematique_recalibree` (ITR < Q80, filtre financier allégé, tracking error minimale + diversification maximale, carbone <= 50 % du MSCI), d'une lecture après 2024 rebalancée chaque trimestre pour tous les modes et des performances mensuelles. Sections 9 et 10. |
| 21/11/2026, plafond par sous-secteur | Tests des plafonds dynamiques (volatilité, volatilité baissière, ratio haussier/baissier) en walk-forward et en stress tests (choc instantané, krachs simulés, épisodes réels). Ajout dans A d'un plafond statique de 12 % par sous-secteur comme limite de concentration et export de `allocation_sous_secteurs.csv` pour tous les modes. |

Les anciens résultats successifs (49, 61, puis 56 positions officielles) sont conservés comme jalons des notes, sans prétendre reproduire à l'identique chaque état intermédiaire. Les prototypes de variance minimale cités dans ces notes, dont un rendement de +10,4 % après 2024, utilisaient une autre allocation : ils ne sont pas assimilés au mode ESG risque actuel.

Les commits cités par les notes d'origine permettent de retrouver les étapes antérieures :

| Commit | Contenu historique annoncé |
|---|---|
| `c18b2da` | Filtres du cours et contribution SBTi |
| `deef454` | Marquage des modifications de Mohamed |
| `2b60248` | Rapprochements par nom, pilier E et options thématiques V3/V6b |
| `43e9ce1` | Filtre financier qualité ; ancien filtre conservé pour comparaison |
| `14c3b5b` | Fusion des travaux, maintien de deux copies des modules |
| `4005abc` | Données SBTi à fin 2024 dans la version officielle |
| `f73ad69` | Chargeur de prix et premier cache |
| `cac047d` | Filtre qualité et PTC dans la version officielle |
| `ec813d3` | SBTi historique et PTC dans la variante Mohamed |
| `8373dd5` | Synthèse des filtres et réorganisation des notes |

Les options thématiques V3 et V6b avaient été préparées en commentaires : V3 gardait santé, semi-conducteurs et logiciels choisis ; V6b ajoutait une liste d'industriels. Leurs anciens décomptes de 32 et 35 titres relevaient d'études exploratoires. Elles ne sont pas activées dans les trois modes demandés. La question d'ajouter Microsoft et l'assouplissement éventuel du FCF pour Eli Lilly ou Vertex restent des décisions de recherche, sans modification implicite des règles actuelles.

## 7. Ce que le nettoyage change

- `filters_mohamed.py` et `run_tri_mohamed.py` sont remplacés par des paramètres de mode dans les modules communs ; on ne commente plus les imports pour choisir une variante.
- `run_pipeline.py` enchaîne sélection, prix disponibles, allocation, backtest, graphiques et comparaison des trois modes.
- Les sources sont regroupées dans `data/raw/`, les prix dans `data/cache/prices/` et les résultats dans `results/`, séparés par mode.
- Les anciens CSV calculés à la racine de `data/` ne servent plus de sortie universelle écrasée à chaque variante.
- Les anciens CSV calculés et les deux PDF de documentation devenus obsolètes sont retirés ; les supports de cours et le sujet restent conservés. Les sources SBTi inutilisées par le calcul sont rangées sous `data/raw/sbti/references/`.
- Les huit anciens Markdown sont ramenés à trois : guide d'exécution, présente méthode/chronologie et analyse des résultats exécutés. Les liens locaux propres à un ordinateur et les déclarations de conformité non démontrées sont retirés.
- Les classes et les étapes de calcul restent reconnaissables ; les corrections portent sur les erreurs d'implémentation, la traçabilité des variantes et la distinction entre statistiques de source et performances réellement calculées.

## 8. Préparer la soutenance

La trame initiale de dix diapositives reste utilisable : identité du fonds ; besoin de santé et thèse ; objectif durable et limites des proxys ; entonnoir ; qualité financière ; composition du portefeuille ; exemples de valeurs réellement retenues ; deux méthodes d'allocation ; résultats financiers et ESG avec sensibilité entre modes ; limites et conclusion.

Les résultats à citer doivent provenir de la dernière exécution, avec la période, le benchmark, les frais éventuels et le nombre de positions correspondants. Présenter le choix hybride face à la règle stricte comme une comparaison méthodologique ; une meilleure performance passée ne valide pas à elle seule un critère durable. Les livrables Excel/PowerPoint évoqués dans le sujet restent distincts de la production de CSV, de graphiques et de cette documentation.

## 9. Stratégie A, thématique recalibrée : recherche et choix

**Point de départ.** Après 2024, les trois premiers modes font +7 à +9 % contre +17,8 % pour le MSCI World (ETF IWDA) et +12,8 % pour l'ETF MSCI World SRI PAB (Amundi WSRI, proche du benchmark du fonds K Investor Friendly du cours). L'attribution de Brinson de Daphné risque ESG contre le MSCI World reconstitué donne un effet d'allocation sectorielle de +3,0 points et un effet de sélection de −12,2 points. La surpondération santé n'est donc pas en cause : l'ETF MSCI World Health Care fait +21,8 % sur la période. Le problème est à l'intérieur des secteurs :

- la poche tech comptait 12,4 % de logiciels pour 4,1 % de semi-conducteurs ; dans le MSCI, les logiciels font −6 % et les semi-conducteurs +31 % ;
- la pharma détenue fait +17 % contre +40 % pour celle du MSCI, car Lilly, J&J et AbbVie sont exclues et Novo Nordisk chute de 54 %.

**Recherche.** Elle a été menée hors dépôt, avec les cours Yahoo de 1 242 titres du MSCI World. Le moteur de recherche a d'abord été validé contre le dépôt : mêmes sélections, mêmes poids, mêmes performances après 2024. Environ 1 600 configurations ont ensuite été testées en croisant :

- la règle de température (ITR ≤ 2 °C ou < Q80) ;
- la contribution positive (hybride, stricte ou aucune) ;
- le thème (actuel, élargi à toute la tech, aucun) ;
- le filtre financier (qualité, sans plafond de volatilité, allégé, aucun) ;
- dix méthodes de pondération (équipondéré, capitalisation, variance minimale, tracking error minimale, budgets de risque ESG, diversification maximale, momentum et score « type KIF » sous budget de tracking error, Pedersen) ;
- plusieurs jeux de contraintes.

Chaque configuration est mesurée sur 2018-2024 et après 2024, à poids figés et rebalancée.

**Trois enseignements de méthode.**

1. *Biais de survivance.* Le MSCI World reconstitué avec les titres présents fin 2024 fait 14,6 %/an sur 2018-2024, contre 12,7 % pour IWDA. Environ 2 points par an de surperformance historique sont donc artificiels, pour tous les modes.
2. *L'historique ne prédit pas l'après-2024.* La corrélation de rang entre les rendements 2018-2024 et post-2024 des configurations va de −0,3 (rebalancé) à −0,6 (poids figés). Le marché change de régime : croissance et méga-capitalisations tech jusqu'en 2024 ; valeurs « value », défensives et semi-conducteurs mémoire ensuite, puis krach IA en octobre-novembre 2026.
3. *Bruit.* Avec 8 à 12 % de tracking error, l'incertitude (1 écart-type) sur l'écart cumulé à l'indice après 23 mois est de ±11 à ±16 points. Les règles ont donc été retenues pour leur justification a priori et leur tenue sur les deux périodes, pas pour leur rang en 2025-2026.

**Ce que rapporte chaque décision.** Mêmes thème et bornes, 4,5 % par ligne ; chiffres du prototype de recherche.

| Étape | Historique 2018-2024 /an | Après 2024, rebalancé | Après 2024, poids figés |
|---|---:|---:|---:|
| Fonds actuel (Daphné · risque ESG) | 13,5 % | +8,6 % | +9,1 % |
| + ITR < Q80 (règle du cours) | 13,8 % | +12,4 % | +10,7 % |
| + filtre financier allégé | 14,5 % | +14,2 % | +11,7 % |
| + tracking error minimale | 15,7 % | +19,7 % | +8,8 % |
| + diversification maximale (à la place) | 15,4 % | +14,4 % | +22,5 % |
| + mélange 50/50 des deux et carbone −50 % | 15,6 % | +16,9 % | +15,5 % |
| + plafond de 12 % par sous-secteur (A, version du dépôt) | 15,0 % | +21,7 % | +13,4 % |

La dernière ligne provient de la pipeline du dépôt. Son historique est réduit d'environ 0,1 point par l'artefact du premier trimestre 2018 (section 10).

**Ce qui a été écarté, et pourquoi.**

- *Supprimer le filtre financier* donne +19 à +22 % après 2024, mais 7,4 points sur 19,4 viennent de Western Digital seule, puis de Seagate et Moderna : ce sont des billets de loterie, et la pertinence du filtre financier est un critère de notation.
- *La variance minimale sur l'univers large* donne +33 à +42 % après 2024, mais seulement 9 %/an sur l'historique. C'est un portefeuille de banques et de défensives, autrement dit un pari de régime.
- *Le score « type KIF »* (qualité, valorisation, rendement, momentum) sous budget de tracking error donne +32 à +40 %, mais avec 20 à 28 lignes et environ 100 % de rotation. Son historique est faible et biaisé, car les fondamentaux de 2024 y servent à choisir en 2018.
- *La pondération par capitalisation* a le meilleur historique (18 à 22 %/an) mais fait +4 à +15 % après 2024, rattrapée par le krach IA.
- *Élargir le thème à toute la tech et à Alphabet* donne un résultat équivalent (+16,0 %) : NVIDIA, Microsoft et Alphabet n'entrent qu'à 1 ou 2 %.
- *Un plafond fixe de 12 % par sous-secteur, vu comme un levier de performance.* Il donne +21,7 % après 2024, mais le gain n'apparaît qu'au plafond le plus serré encore faisable : +17,4 % à 15 %, aucun effet à partir de 20 %. Sur l'historique, l'absence de plafond est meilleure. Ce gain n'est donc pas un argument : le plafond a été finalement **retenu pour une autre raison**, comme règle de diversification (paragraphe suivant).
- *Le rebalancement mensuel et le modèle de risque court* (52 semaines) font moins bien (+14,6 % et +5,0 %) : va-et-vient et frais.

**Plafond par sous-secteur : tests et décision.** Trois plafonds dynamiques recalculés chaque trimestre ont été comparés à l'absence de plafond et au plafond statique de 12 %, en walk-forward et avec des paramètres fixés a priori :

- Inverse Volatility ;
- Inverse Downside Volatility (semi-variance baissière EWMA, demi-vie de 63 séances) ;
- ratio de volatilité haussière sur volatilité baissière.

Constats :

- *En performance*, aucun plafond n'améliore significativement la robustesse. L'Inverse Downside Volatility coûte 0,6 point par an sur 2018-2024 et rapporte un gain non significatif après 2024. Le ratio haussier/baissier gagne après 2024 par un effet de tendance (capture des hausses de 99 %), mais il dégrade la capture des baisses et l'historique.
- *En stress tests* :
  - choc instantané de −30 % sur le plus gros sous-secteur : −3,6 % avec le plafond de 12 %, contre −5,6 % sans plafond ;
  - krachs progressifs simulés de 6 mois : l'Inverse Downside Volatility réduit l'exposition pendant le krach et fait mieux que l'absence de plafond dans 72 % des cas, avec un petit gain ;
  - krach de la santé entière : aucun plafond ne protège (−15 à −16 % pour le fonds, contre −3 % pour le MSCI), car c'est le plancher de 50 % de santé qui fixe ce risque ;
  - une Inverse Downside Volatility bornée à 12 % se comporte comme le plafond statique.

Le plafond statique de 12 % est retenu pour A comme **limite de concentration simple à expliquer** : aucun segment ne dépasse un huitième du fonds. Il est présenté comme une règle de gestion des risques, pas comme une source de performance. Son coût est connu : environ −0,5 point par an sur l'historique et un portefeuille du 31/12/2024 moins performant à poids figés (+13,4 % contre +15,6 % sans plafond).
**Comparaison avec la méthode du prof** (slides 62-63 du cours et rapport mensuel du fonds K Investor Friendly au 30/10/2026). A reprend son univers ESG (ITR < Q80 par titre : le KIF détient NVIDIA à 2,9 °C), un fonds sous 2 °C et l'objectif de tracking error de la slide 63. La différence est assumée : le KIF n'a pas de thème, ses secteurs restent proches de l'indice, et il ajoute une sélection qualité/valorisation/rendement/momentum. Une réplique sans thème (tracking error minimale, secteurs à ±5 points de l'indice, 50 lignes) fait +21,2 % rebalancée et +15,1 % à poids figés, mais ce ne serait plus un fonds HealthTech & IA.

## 10. Difficultés rencontrées

**Données de prix.**

- *Couverture.* Le cache du dépôt ne couvrait que les 64 titres des trois premiers modes. Tester d'autres filtres a exigé de télécharger tout l'univers, soit 1 243 tickers Yahoo. Vingt-sept sont introuvables, pour l'essentiel des sociétés rachetées ou retirées de la cote en 2025-2026 (Ansys, Hologic, Juniper, Hess, Walgreens, Kellanova…), plus quelques codes singapouriens au mauvais format (DBS, OCBC). Ces titres ne peuvent pas être simulés, ce qui crée un léger biais de survivance après 2024. Neuf autres cessent de coter pendant la période (CyberArk, Qorvo, Kenvue…).
- *Devises.* La colonne `currency` de `all_data.csv` ne correspond pas toujours à la place de cotation Yahoo :
  - quatre titres en `.SG` sont cotés à Stuttgart en EUR, et non en SGD ;
  - deux titres en `.L` sont cotés en EUR ;
  - les titres israéliens sont en agorot (`ILs`), unité que `src/prices.py` ne reconnaît pas (il gère `ILA`).

  Aucun de ces titres n'entre dans les quatre modes. Pour les 88 titres de la stratégie A, la vérification ne trouve aucun titre radié et aucune devise à risque. Le chargeur devra être corrigé si l'univers s'élargit.
- *Mouvements extrêmes non vérifiés.* Moderna +177 % le 19/08/2026, PTC +33 % le 05/10/2026, XP −48 % le 26/10/2026, et des scissions mal ajustées (Holcim/Amrize, Vivendi). Ils sont conservés sans correction arbitraire. Aucun n'est en portefeuille dans A au 31/12/2024, où PTC a un poids nul.
- *Premier rebalancement.* Le cache commence le 02/01/2015. Au premier rebalancement (29/12/2017), les titres sans cours la première semaine de 2015 (Tokyo fermée jusqu'au 5 janvier) n'ont pas 156 semaines complètes et sont écartés pendant un trimestre : 39 titres sur 56 pour Daphné. Cet artefact explique les petits écarts entre le dépôt et le prototype de recherche (13,31 % contre 13,50 %/an pour Daphné risque ESG, 15,5 % contre 15,6 % pour A). Il n'est pas corrigé, pour ne pas modifier les résultats des modes existants.

**Méthode.**

- *Biais de survivance et changement de régime* entre 2018-2024 et 2025-2026 : voir la section 9.
- *Date d'arrêt.* La période après 2024 se termine en plein krach IA (octobre-novembre 2026), si bien que les résultats dépendent beaucoup de la date retenue. Avant le plafond par sous-secteur, A faisait +14,0 % au 30/09/2026 contre +24,0 % pour le MSCI World, puis +16,9 % contre +17,8 % au 20/11/2026.
- *Sur-apprentissage.* La stratégie A a été conçue après avoir vu 2025-2026. Pour limiter ce risque, ses règles s'appuient sur le cours (ITR < Q80, slide 63) et sur la pratique du KIF. Le plafond de 12 % par sous-secteur a d'abord été écarté comme levier de performance, puis retenu uniquement comme limite de concentration. Sa performance après 2024 n'est donc pas une validation indépendante.
- *Niveau du plafond.* 12 % est le plafond le plus serré encore compatible avec le plancher de 50 % de santé : à 10 %, le problème devient infaisable. Il fixe donc presque entièrement la poche santé. Son effet dépend aussi de la classification `industry_group` de `all_data.csv`, de type Bloomberg et figée à fin 2024, dont certains libellés sont discutables (Cummins en « Auto Manufacturers », assureurs et laboratoires réunis dans « Healthcare-Services »).
