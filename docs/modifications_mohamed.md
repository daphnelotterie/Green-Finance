# Modifications de Mohamed (20-21/11/2026)

Branche Git : `filtres-slides-sbti`.
Depuis la fusion du 21/11 avec la version de Daphné, **les fichiers officiels `src/filters.py` et `src/run_tri.py` sont ceux de Daphné**. Ma version est conservée dans **`src/filters_mohamed.py`** et **`src/run_tri_mohamed.py`** (voir la partie 8).
Dans le code, chaque ligne modifiée par Mohamed porte le commentaire `# Modif Mohamed`.

Ce document décrit ma version (parties 1 à 7), la fusion (partie 8) et le passage aux données SBTi au 31/12/2024 (partie 9). Les parties 10 et 11 préparent la soutenance.

## Résumé

- Les **filtres extra-financiers** suivent maintenant les règles du cours (slides 13 et 41 à 50), dans leur version en vigueur à la date de nos données (31/12/2024).
- La **contribution positive (slide 13)** repose sur une règle explicite : CA aligné Taxonomie ≥ 20 % **ou** objectif climat validé par SBTi (données officielles SBTi).
- Le **filtre financier** sélectionne sur la qualité (rentabilité, cash, dette, risque) et plus sur la performance boursière passée.
- **Deux options de filtre thématique** (V3 et V6b) sont prêtes en commentaire, en attente d'une décision du groupe.
- Un **module de prix historiques** (`src/prices.py`) prépare le futur backtest.
- Résultat (ma version) : **57 lignes** en portefeuille (contre 50), **toutes avec un objectif SBTi validé**.
- Version officielle (Daphné), avec les données SBTi au 31/12/2024 branchées le 21/11 : **49 lignes** (partie 9).

## 1. Filtres extra-financiers (`src/filters_mohamed.py`)

| Filtre | Avant (v1) | Maintenant | Pourquoi |
|---|---|---|---|
| PAB (slide 44) | armes, tabac, secteur Energy | idem + tabac sans donnée exclu | règle des données manquantes (slide 50) |
| DNSH (slide 42) | controverse E, S ou G < 2 exclue | idem + donnée manquante exclue | règle des données manquantes |
| Bonne gouvernance (slide 41) | notes B/CCC exclues + pilier G ≤ 3 exclu | notes B/CCC et notes manquantes exclues ; pilier G retiré | le pilier G n'est pas dans le cours (la slide 45 parle du pilier E) |
| Température (slides 43 et 50) | ITR ≤ 2 °C | ITR < Q80 % de l'univers (3,1 °C) | la règle « ITR > 2 °C » a été abandonnée en février 2024 ; nos données sont au 31/12/2024 |
| Pilier E (slides 45 et 50) | absent | E ≥ Q5 % (3,0/10) ; E < Q5 % exclu | règle « Note du pilier E < Q5 % » de la slide 50 |
| Carbone (slide 46) | intensité scopes 1+2, pire décile par secteur | empreinte **et** intensité scopes 1+2+3, pire décile par secteur | la slide 46 utilise les deux mesures ; les niveaux de la figure correspondent aux scopes 1+2+3 |
| ODD 7, 12, 13 (slide 47) | score < −1 exclu | score = −10 exclu | le cadre de la slide 47 n'entoure que « −10 » et « No data » (82 exclus chez nous, 80 sur la slide 50) |
| Données manquantes | remplacées par des valeurs par défaut | exclusion, pour chaque filtre | note 1 de la slide 50 |

Après ces 8 filtres : 1 247 → **692 titres** (555 exclus, soit 44,5 %).
Pour comparaison, la slide 50 (données Kanopy au 30/09/2026, 1 109 titres) indique 539 exclus (49 %).

## 2. Contribution positive, slide 13 (`src/filters_mohamed.py`, `src/run_tri_mohamed.py`)

- **Règle** : CA aligné Taxonomie UE (`EST_EU_TAXONOMY_MAX_REV`) ≥ 20 % **ou** objectif de réduction des émissions validé par SBTi.
- **Validation SBTi** : `near_term_status == "Validated Targets"` ou `long_term_status == "Validated Targets"`. Un simple engagement (« Commitment to Set Targets »), un engagement retiré (« Commitment Removed »), une absence de la base SBTi ou une donnée manquante ne valent jamais validation.
- **Avant** : Taxonomie > 0 %, Clean Tech ≥ 10 %, ITR ≤ 1,5 °C ou ODD ≥ 1. C'était beaucoup plus large que la slide 13.
- **Données SBTi** (dossier `data/sbti/`, séparé de nos données) :
  - `companies-excel.xlsx` : fichier officiel téléchargé le 20/11/2026 sur sciencebasedtargets.org/target-dashboard ;
  - `companies-excel.csv` : même contenu en CSV, lu par le code ;
  - `jointure_sbti_msci.csv` : statut SBTi de chacun de nos 1 247 titres.
- **Jointure** : par ISIN, complétée par **75 rapprochements par nom vérifiés à la main** (`SBTI_NAME_MATCHES` dans `run_tri_mohamed.py`). Ils couvrent les fiches SBTi sans ISIN, ou avec un ancien ISIN ou une autre classe d'actions : Novo Nordisk, Straumann, QIAGEN, West Pharmaceutical, TE Connectivity… 17 faux rapprochements ont été rejetés (Ferrari Group, PPL Inc. au Japon, Nice Group, Mercedes-Benz AG, JAPAN POST Co., Kao, homonymes « X&Y »).
- **Résultat** : 692 → **390 titres**. Le prof a lui aussi une étape après la slide 50 (sur la slide 62, environ 570 → 482).

## 3. Filtre thématique (`src/filters_mohamed.py`) : décision du groupe

- Le filtre actif est **inchangé** (version d'origine).
- Constats :
  - la règle « Industrie » ne fait entrer que Cummins (moteurs diesel) et Kubota (tracteurs) ;
  - la règle « Tech avec ODD 9 ≥ 1 » fait entrer de la Tech générique (Intuit, Sage, Adobe, Capgemini…) ;
  - resserrer les seuils ODD vide la poche Tech et garde Cummins ;
  - les fabricants d'équipements pharma sont déjà classés dans le secteur Santé.
- Deux options sont prêtes **en commentaire** :
  - `HealthTechAIScopeFilterV3` : tout le secteur Santé, plus les semi-conducteurs et les logiciels de conception de puces et de simulation (Cadence, Synopsys, Dassault Systèmes, Ansys). Résultat : **38 lignes**, 68,5 % Santé / 31,5 % Tech.
  - `HealthTechAIScopeFilterV6b` : V3 plus des industriels choisis (Lifco, Wolters Kluwer, RELX, Schneider Electric, Legrand, VAT Group). Résultat : **43 lignes**, 53,1 % Santé / 27,9 % Tech / 19,0 % Industrie.
- **Pour activer une option** : décommenter la classe dans `filters_mohamed.py` (pour V6b, décommenter aussi V3), puis l'import et la ligne `thematic_filter = ...` déjà prêts dans `run_tri_mohamed.py`.
- **Question ouverte** : faut-il ajouter Microsoft à la liste IA ?

## 4. Filtre financier (`src/filters_mohamed.py`)

- Le nouveau `FinancialQualityFilter` garde une entreprise si :
  - ROIC > 5 % ou marge nette > 5 % ;
  - FCF yield > 0 ;
  - dette / actifs < 65 % ;
  - volatilité à 5 ans ≤ 90e centile du MSCI World (46,9 %) ;
  - aucune de ces données ne manque.
- **Pourquoi ce changement** :
  - l'ancien filtre sélectionnait surtout sur la performance boursière passée (Sharpe et rendement à 5 ans : 17 exclusions sur 24). C'était un filtre de momentum, il créait un biais in-sample avec le backtest et contredisait la mention AMF « les performances passées ne préjugent pas des performances futures » ;
  - le FCF de Jensen était annoncé mais jamais appliqué : Cummins, Lonza et Elevance avaient un FCF négatif et étaient en portefeuille ;
  - le ROE n'est pas fiable dans les données (jusqu'à 22 574 % avec des fonds propres quasi nuls).
- La **version d'origine est conservée telle quelle** sous le nom `FinancialQualityFilterDaphne`. Une ligne prête dans `run_tri_mohamed.py` permet de la réactiver.
- **Argument marketing** : la « durabilité financière » (slide 5 : Kanopy définit l'investissement durable comme une double durabilité, extra-financière et financière).

## 5. Prix historiques (`src/prices.py`)

- Classe `HistoricalPriceLoader`, construite comme l'optimiseur et le backtest. On la lance avec `python src/prices.py`.
- Elle télécharge avec yfinance les cours de clôture ajustés (dividendes et divisions) des titres de l'univers sélectionnable, ainsi que le benchmark MSCI World (ETF iShares, `IWDA.AS`, coté en euros), du 02/01/2015 au 20/11/2026.
- Les cours sont convertis en euros ; les cours de Londres, cotés en pence, sont divisés par 100.
- Fichiers produits dans `data/prix/` : `prix_devise_locale.csv`, `taux_de_change.csv`, `prix_eur.csv`.
- **Contrôles** :
  - 59 titres sur 59 ont des données ;
  - le benchmark fait +10,2 % par an sur 2015-2023, avec 16,3 % de volatilité ;
  - trois chutes de plus de 35 % en une séance (Synopsys, West Pharmaceutical, ICON) restent à vérifier.
- Le module n'est pas encore branché dans `run_pipeline.py`, car il a besoin d'internet.

## 6. Résultats (nos données au 31/12/2024)

| Étape | v1 | Maintenant |
|---|---|---|
| Après les filtres extra-financiers du cours | 491 | 692 |
| Après la contribution positive (slide 13) | 412 | 390 |
| Après le filtre thématique | 77 | 80 |
| Après le filtre financier | 50 | 59 |
| **Lignes en portefeuille** | **50** | **57** |

| Indicateur | v1 | Maintenant |
|---|---|---|
| ITR du fonds | 1,52 °C | 1,67 °C |
| Intensité carbone scopes 1+2+3 par rapport à l'indice | −54,7 % | −65,1 % |
| Santé / Tech | 51,6 % / 39,9 % | 51,7 % / 40,0 % |
| Lignes avec un objectif SBTi validé | non mesuré | 57 / 57 |

Les chiffres de performance de `backtest.py` ne sont pas repris ici, car la méthode de calcul n'est pas fiable (voir la partie 7).

## 7. Ce qui reste à faire

- **Optimiseur** :
  - le rendement espéré est le rendement passé (biais in-sample) ;
  - la covariance est fabriquée avec des corrélations fixes (0,50 et 0,28) ;
  - les contraintes de secteur ne sont que des pénalités ;
  - « Industrie ≤ 15 % » et « ITR ≤ 1,8 °C » sont annoncées mais pas codées ;
  - un plafond caché ITR ≤ 2,5 retire NVIDIA, AMD…
  - Piste : appliquer la slide 63 (minimum de volatilité) avec la vraie covariance tirée des prix.
- **Backtest** : il n'utilise aucun prix. À refaire avec `data/prix/`. La période hors échantillon commence le 01/01/2025.
- **Livrables** : fichiers Excel, PowerPoint, et mise à jour du README et des docs (chiffres obsolètes, formulations à risque vis-à-vis de l'AMF).
- **Limites à mentionner à l'oral** : ma version lit encore la base SBTi de novembre 2026, alors que nos données sont de fin 2024 (la version officielle utilise désormais la photo au 31/12/2024, voir la partie 9) ; l'exclusion PAB est approchée par le secteur Energy.

## 8. Fusion avec la version de Daphné (21/11/2026)

- Daphné a poussé une nouvelle version sur `main` (3 commits du 21/11). Elle reprend une partie de mes filtres et propose une contribution positive « hybride » (santé ou climat).
- **Décision** : sa version devient la version officielle (`src/filters.py`, `src/run_tri.py`). La mienne est conservée dans `src/filters_mohamed.py` et `src/run_tri_mohamed.py`.
- **Pour revenir à ma version** : dans `run_pipeline.py`, commenter la ligne `from src.run_tri import ...` et décommenter la ligne `from src.run_tri_mohamed import ...` juste en dessous.

| Point | Daphné (version officielle) | Mohamed |
|---|---|---|
| Température | ITR ≤ 2 °C | ITR < Q80 % (3,1 °C) |
| Pilier E | exclut E ≤ Q5 % | exclut E < Q5 % |
| Contribution positive | hybride : Taxonomie ≥ 20 %, SBTi validé, Clean Tech ≥ 10 % ou ITR ≤ 1,5 °C, **ou** ODD 3 ≥ 1, ODD 9 ≥ 1, autres ODD ≥ 1,5 | stricte : Taxonomie ≥ 20 % ou SBTi validé |
| Rapprochements SBTi par nom | non | 75 vérifiés |
| Filtre financier | d'origine (Sharpe et rendement à 5 ans) | qualité (ROIC ou marge, FCF, dette, volatilité) |
| Lignes en portefeuille | 50 | 57 |
| ITR / carbone S1+2+3 vs indice | 1,53 °C / −69,9 % | 1,67 °C / −65,1 % |

## 9. Données SBTi à la date de nos données (photo du 13/01/2025)

- **Fichier** `data/sbti/msci_world_jointure_sbti_2025-01-13.csv` : nos 1 247 titres (100 colonnes identiques à `all_data.csv`), plus le statut SBTi tiré d'une archive de l'export officiel SBTi du 13/01/2025 (dépôt GitHub `CalibreFinancialTechnology/sbti-cta`). Il indique aussi la méthode de rapprochement et contient une colonne stricte : « validation publiée avant le 31/12/2024 confirmée ».
- **Pourquoi c'est important** : nos données sont au 31/12/2024. Avec la base SBTi de novembre 2026, **89 titres sont comptés comme validés alors qu'ils ne l'étaient pas encore fin 2024** (NVIDIA, Danaher, Medtronic, CSL, GSK, West Pharmaceutical, Waters, Veeva…). C'est un biais d'anticipation (look-ahead). À l'inverse, 10 titres validés fin 2024 ne le sont plus en 2026 (Biogen, Kao, Coca-Cola…).
- **Contrôles** : les rapprochements recoupent nos vérifications (Kao rapproché par ISIN exact ; Mercedes-Benz, Japan Post, PPL, Nice, T&D non rapprochés). Les 11 cas « à revoir » (dont Roche) sont comptés comme non validés.
- **Impact sur le portefeuille**, avec la validation stricte (confirmée avant le 31/12/2024). La lecture plus large du 13/01/2025 donne exactement les mêmes portefeuilles.

| Version | SBTi de nov. 2026 | SBTi au 31/12/2024 | Changements |
|---|---|---|---|
| Daphné (officielle) | 50 lignes | 49 lignes | sortent Veeva et Bio-Techne ; entre Straumann |
| Mohamed | 57 lignes | 49 lignes | sortent West Pharmaceutical, Danaher, SOBI (4,5 % chacun), TE Connectivity, Henry Schein, CSL, Veeva, Waters, Bio-Techne, CGI ; entrent Biogen et Kao |

- **Décision (21/11)** : on passe aux données SBTi au 31/12/2024. Elles sont cohérentes avec la date de toutes nos autres données, évitent le biais d'anticipation et gardent propre le futur backtest hors échantillon (à partir de 2025).
- **Dans le code (version officielle)** : `src/run_tri.py` lit ce fichier avec la nouvelle fonction `load_sbti_snapshot_by_isin`. Elle ne garde que les rapprochements sûrs (« MATCHED »), ne compte comme validés que les objectifs dont la publication avant le 31/12/2024 est confirmée, et traduit les statuts de la photo dans le vocabulaire de `filters.py`. `filters.py` n'a pas changé. La lecture de la base de novembre 2026 reste en commentaire.
- **Résultat** : 1 247 → 483 → 420 → 75 → 49 → **49 lignes** (contre 50). 98 % du poids est inchangé : sortent Bio-Techne et Veeva (1 % chacune), entre Straumann (1 %). L'ITR reste à 1,53 °C ; la baisse du carbone S1+2+3 par rapport à l'indice passe de −69,9 % à −69,6 %.
- **Fichiers** : `msci_world_jointure_sbti_2025-01-13.csv` est lu par le code. `sbti_2025-01-13_plan_b.csv` est la photo SBTi complète du 13/01/2025 (10 534 entreprises, côté SBTi) dont il est tiré ; il n'est pas lu par le code et sert à la traçabilité.
- **Ma version** (`run_tri_mohamed.py`) lit toujours la base de novembre 2026, avec ses 75 rapprochements par nom. À basculer si on y revient.

## 10. Avantages et inconvénients (pour la soutenance)

**Ce que la démarche apporte :**
- Des filtres fidèles au cours (slides 41 à 50), appliqués à la date des données, avec la règle de la slide 50 sur les données manquantes. C'est facile à défendre devant les enseignants.
- Une contribution positive (slide 13) explicite et vérifiable : objectif SBTi validé ou CA aligné Taxonomie. Argument fort : dans ma version, 100 % des lignes ont un objectif climat validé par SBTi.
- Une prudence systématique : une donnée manquante ou un simple engagement ne valent jamais validation.
- Un filtre financier de « durabilité financière » (rentable, cash positif, peu endetté, pas trop volatil), sans sélection sur la performance passée, donc cohérent avec la mention AMF.
- De la traçabilité : rapprochements SBTi vérifiés et documentés, deux versions conservées, commentaires `# Modif Mohamed`.

**Limites et inconvénients :**
- SBTi et la Taxonomie mesurent le climat, pas la santé. Une lecture stricte écarte des leaders sans objectif SBTi (Eli Lilly, Vertex, Regeneron) : c'est la raison de la version hybride de Daphné.
- La règle de température du cours (Q80 %) laisse entrer des titres jusqu'à 3,1 °C. Il faut donc une contrainte de température au niveau du portefeuille (slide 40).
- L'exclusion PAB est approchée par le secteur Energy, faute de part de CA fossile dans les données.
- Les scores ODD de MSCI mesurent mal le lien avec la santé : l'ODD 3 vaut 0 pour de vraies valeurs santé (ICON, IQVIA) et pour toute la Tech.
- Les listes de logiciels IA et d'industriels sont des choix discrétionnaires, à justifier.
- L'optimiseur et le backtest restent à refaire : les chiffres de performance actuels ne sont pas fiables.

## 11. Difficultés rencontrées (pour la soutenance)

- **Lire les règles exactes du cours** : les seuils ne figurent que dans les graphiques (cadres des slides 41 à 47). L'ancienne règle de température est en italique et ne compte pas dans le total. Les scopes du carbone ne sont pas précisés : il a fallu les déduire des niveaux de la figure 11.
- **Les dates** : nos données sont au 31/12/2024, celles du cours au 30/09/2026, et la base SBTi téléchargée date de novembre 2026. Il a fallu trouver une photo SBTi à la bonne date pour éviter le biais d'anticipation.
- **La jointure SBTi** : ISIN absents, anciens (divisions d'actions) ou d'une autre classe d'actions, et homonymes trompeurs (EQT, Ferrari, T&D…). Il a fallu vérifier les rapprochements à la main.
- **L'arbitrage entre conformité et marketing** : la règle stricte écarte Eli Lilly, tandis que les règles fondées sur les ODD font entrer Cummins (moteurs diesel), des produits ménagers ou du logiciel de gestion dans un fonds « HealthTech & AI ».
- **La qualité des données** : ROE aberrants (jusqu'à 22 574 %), fonds propres négatifs, données manquantes, chutes de cours à vérifier.
- **Le travail à plusieurs sur le même code** : deux versions des filtres développées en parallèle, réconciliées en conservant les deux.

## 12. Commits

| Commit | Contenu |
|---|---|
| `c18b2da` | filtres alignés sur le cours + règle SBTi de la slide 13 (poussé) |
| `deef454` | marquage `# Modif Mohamed` (poussé) |
| `2b60248` | rapprochements SBTi par nom, pilier E ≥ Q5, options thématiques V3 et V6b |
| `43e9ce1` | nouveau filtre financier (ancienne version conservée en `FinancialQualityFilterDaphne`) |
| `14c3b5b` | fusion : version de Daphné comme version officielle, `filters_mohamed.py`, `run_tri_mohamed.py`, ligne de bascule dans `run_pipeline.py` |
| commit suivant | données SBTi au 31/12/2024 branchées dans `run_tri.py`, fichiers SBTi de 2025, sorties régénérées (49 lignes) et ce document |
| non commité | `src/prices.py` et `data/prix/` |

Les commits postérieurs à `deef454` ne sont pas encore poussés sur GitHub.
