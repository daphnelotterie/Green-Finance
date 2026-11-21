# Modifications de Mohamed (20-21/11/2026)

Branche Git : `filtres-slides-sbti`. Dans le code, chaque ligne modifiée par Mohamed porte le commentaire `# Modif Mohamed`.

- **Version officielle** : `src/filters.py` et `src/run_tri.py`. Ce sont ceux de Daphné, avec mes modifications du 21/11 (partie A).
- **Ma version** : `src/filters_mohamed.py` et `src/run_tri_mohamed.py` (partie B).
- **Synthèse finale des filtres**, pour le groupe : `docs/filters.md`.

## Résumé

- La version officielle utilise maintenant :
  - les **statuts SBTi au 31/12/2024**, à la même date que nos données ;
  - notre **filtre financier « qualité »** (rentabilité, cash, dette, volatilité), qui ne sélectionne plus sur la performance passée ;
  - **PTC à la place d'Ansys**, rachetée par Synopsys puis retirée de la cote en 2025.
- Résultat officiel : **61 lignes**, ITR de 1,53 °C. L'intensité carbone S1+2+3 est inférieure de 66,9 % à celle de l'indice.
- `src/prices.py` télécharge les prix des 61 lignes, de 2015 à aujourd'hui, pour le futur backtest.
- Ma version (filtres du cours et contribution positive stricte) donne **50 lignes**. Chacune a un objectif SBTi validé ou au moins 20 % de CA aligné Taxonomie.

## Partie A. Modifications de la version officielle (21/11/2026)

### A1. Données SBTi au 31/12/2024

- **Fichier lu** : `data/sbti/msci_world_jointure_sbti_2025-01-13.csv`. Il contient nos 1 247 titres, avec 100 colonnes identiques à `all_data.csv`. S'y ajoutent le statut SBTi tiré d'une archive de l'export officiel SBTi du 13/01/2025 (dépôt GitHub `CalibreFinancialTechnology/sbti-cta`) et la méthode de rapprochement.
- `data/sbti/sbti_2025-01-13_plan_b.csv` est la photo SBTi complète (10 534 entreprises) dont ce fichier est tiré. Le code ne le lit pas : il sert à la traçabilité.
- **Pourquoi** : nos données sont au 31/12/2024.
  - Avec la base de novembre 2026, **89 titres étaient comptés comme validés alors qu'ils ne l'étaient pas encore fin 2024** : NVIDIA, Danaher, Medtronic, CSL, GSK, West Pharmaceutical, Waters, Veeva… C'est un biais d'anticipation (look-ahead).
  - À l'inverse, 10 titres validés fin 2024 ne le sont plus en 2026 : Biogen, Kao, Coca-Cola…
- **Code** : nouvelle fonction `load_sbti_snapshot_by_isin` dans `run_tri.py`. `filters.py` n'a pas changé pour cela, et l'ancienne lecture de la base de novembre 2026 reste en commentaire.
  - Seuls les rapprochements sûrs (« MATCHED ») sont gardés. Les 11 cas « à revoir », dont Roche, comptent comme non validés.
  - Un objectif ne compte comme validé que si sa publication avant le 31/12/2024 est confirmée : c'est le cas pour 506 titres.
  - Les statuts sont traduits dans le vocabulaire de `filters.py`.
- **Contrôles** : les rapprochements du fichier recoupent nos vérifications. Kao est rapproché par ISIN exact ; Mercedes-Benz, Japan Post, PPL, Nice et T&D ne sont pas rapprochés.
- **Effet à lui seul** : 50 → 49 lignes, avec 98 % du poids inchangé. Bio-Techne et Veeva sortent, Straumann entre.

### A2. Filtre financier « qualité »

- Il remplace le filtre de Daphné, qui sélectionnait sur le Sharpe et le rendement à 5 ans. Celui-ci est conservé sous le nom `FinancialQualityFilterDaphne`, avec une ligne commentée dans `run_tri.py` pour le réactiver.
- **Règles** :
  - ROIC > 5 % ou marge nette > 5 % ;
  - FCF yield > 0 ;
  - dette / actifs < 65 % ;
  - volatilité à 5 ans ≤ 90e centile du MSCI World (46,9 %) ;
  - une donnée manquante entraîne l'exclusion.
- **Pourquoi** :
  - dans le scope thématique, 21 des 26 exclusions venaient de la seule performance passée (CSL, Biogen, Humana…). C'était un filtre de momentum : il créait un biais in-sample avec le backtest et contredisait la mention AMF « les performances passées ne préjugent pas des performances futures » ;
  - le FCF de Jensen était annoncé mais jamais appliqué ;
  - le ROE n'est pas fiable dans nos données (il monte jusqu'à 22 574 %).
- **Effet à lui seul** : 49 → 61 lignes.
  - Sortent **Eli Lilly et Vertex** (4,5 % chacune) et Elevance (1 %), dont le FCF yield est négatif dans nos données au 31/12/2024.
  - Entrent 15 lignes à 1 % : CSL, Biogen, Genmab, BioMarin, Shionogi, Ono, Kyowa Kirin, Sysmex, Teleflex, Eurofins, Centene, Kao, Unicharm, Essity et Kirin.
- **À discuter en groupe** :
  - la sortie d'Eli Lilly, valeur phare de la santé ;
  - l'entrée de Kirin à 1 % : c'est un brasseur, maison mère de Kyowa Kirin, qui passe par la règle « Consommation de base, ODD 3 ≥ 2 ».

### A3. Ansys remplacée par PTC

- **Problème** : Ansys (1 % du portefeuille) n'a plus de cours sur Yahoo. Synopsys l'a rachetée (accord annoncé le 16/01/2024, finalisé en juillet 2025) : elle a été retirée de la cote et Yahoo a supprimé tout son historique. Aucune autre source gratuite testée ne fonctionne.
- **Règle** : un titre sous offre de rachat définitive à la date des données est écarté. Il va quitter la cote, et son cours suit les termes de l'offre plutôt que l'entreprise. Cette information était publique au 31/12/2024 : la règle n'introduit donc pas de biais d'anticipation.
- **Remplaçant : PTC**, choisie dans l'univers discrétionnaire (slide 62).
  - Chez Daphné, l'optimiseur garde tous les titres éligibles : aucun titre passant déjà tous les filtres n'était hors du portefeuille.
  - PTC passe tous les filtres ESG et le filtre financier ; seul le filtre thématique l'écartait (son ODD 9 vaut 0).
  - Comme Ansys, elle édite des logiciels de conception (CAO, PLM) et de simulation, utilisés notamment par les fabricants de dispositifs médicaux.
  - Elle est mieux notée qu'Ansys : ITR de 1,3 °C contre 1,6 °C, objectif SBTi validé (Ansys n'est pas dans la base), Sharpe de 0,63 contre 0,20.
- Synopsys, qui a racheté Ansys, aurait été le choix naturel. Mais son ITR (2,1 °C) dépasse la règle ≤ 2 °C de la version officielle.
- **Code** : deux règles marquées dans `HealthTechAIScopeFilter` (`filters.py`). La même chose est faite dans ma version, y compris dans la liste de l'option V3.
- **Résultat** : PTC entre à 3,9 %. L'optimiseur lui donne plus que le 1 % d'Ansys.

### A4. Prix historiques (`src/prices.py`)

- La classe `HistoricalPriceLoader` est construite comme l'optimiseur et le backtest. On la lance avec `python src/prices.py`, après `run_pipeline.py`. Elle n'est pas branchée dans `run_pipeline.py`, car elle a besoin d'internet.
- Elle lit le **portefeuille final** (`data/portefeuille_final_pondere.csv`). Ce fichier n'a ni ticker Yahoo ni devise : elle les reprend dans `data/all_data.csv`, comme `backtest.py`. On peut aussi lui passer l'univers sélectionnable, par exemple pour un optimiseur qui utilise la vraie covariance.
- Elle télécharge avec yfinance les cours de clôture ajustés (dividendes et divisions), ainsi que le benchmark MSCI World (ETF iShares `IWDA.AS`, coté en euros), du 02/01/2015 au 20/11/2026.
- Tous les cours sont convertis en euros ; les cours de Londres, cotés en pence, sont divisés par 100.
- Fichiers produits dans `data/prix/` : `prix_devise_locale.csv`, `taux_de_change.csv`, `prix_eur.csv`.
- **Contrôles** sur les 61 lignes :
  - 61 titres sur 61 ont des cours (100 % du poids). Essity n'est cotée que depuis 06/2017, après sa scission de SCA ;
  - les variations de plus de 30 % en une séance sont de vrais événements (Biogen en 2020-2022, BioMarin en 2020, Centene en 07/2025). Seule exception à vérifier : PTC +33 % le 05/10/2026, après la date de constitution du portefeuille ;
  - le benchmark fait +10,2 % par an sur 2015-2023, avec une volatilité de 16,2 % ;
  - 4,1 % des cases sont vides : ce sont les jours fériés propres à chaque place. Le backtest devra reprendre le dernier cours connu.

### A5. Résultat de la version officielle

| Étape | Lignes | ITR | Intensité carbone S1+2+3 par rapport à l'indice |
|---|---|---|---|
| v2 de Daphné (SBTi de nov. 2026, filtre financier d'origine) | 50 | 1,53 °C | −69,9 % |
| + SBTi au 31/12/2024 | 49 | 1,53 °C | −69,6 % |
| + filtre financier qualité + PTC à la place d'Ansys | **61** | **1,53 °C** | **−66,9 %** |

- **Répartition** : Santé 51,6 % (33 lignes), Tech 35,9 % (19), Consommation de base 8,0 % (8), Industrie 4,5 % (Pentair).
- Dix lignes sont au plafond de 4,5 % : Novo Nordisk, Intuit, Cadence, Regeneron, Advantest, Chugai, NEC, Pentair, Molina et SOBI.
- Les chiffres de performance de `backtest.py` ne sont pas repris ici : il n'utilise aucun prix (voir la partie C).

## Partie B. Ma version (`src/filters_mohamed.py`, `src/run_tri_mohamed.py`)

### B1. Filtres extra-financiers

| Filtre | Avant (v1) | Ma version | Pourquoi |
|---|---|---|---|
| PAB (slide 44) | armes, tabac, secteur Energy | idem + tabac sans donnée exclu | règle des données manquantes (slide 50) |
| DNSH (slide 42) | controverse E, S ou G < 2 exclue | idem + donnée manquante exclue | règle des données manquantes |
| Bonne gouvernance (slide 41) | notes B/CCC exclues + pilier G ≤ 3 exclu | notes B/CCC et notes manquantes exclues ; pilier G retiré | le pilier G n'est pas dans le cours (la slide 45 parle du pilier E) |
| Température (slides 43 et 50) | ITR ≤ 2 °C | ITR < Q80 % de l'univers (3,1 °C) | la règle « ITR > 2 °C » a été abandonnée en février 2024 ; nos données sont au 31/12/2024 |
| Pilier E (slides 45 et 50) | absent | E ≥ Q5 % (3,0/10) ; E < Q5 % exclu | règle « Note du pilier E < Q5 % » de la slide 50 |
| Carbone (slide 46) | intensité scopes 1+2, pire décile par secteur | empreinte **et** intensité scopes 1+2+3, pire décile par secteur | la slide 46 utilise les deux mesures ; les niveaux de la figure correspondent aux scopes 1+2+3 |
| ODD 7, 12, 13 (slide 47) | score < −1 exclu | score = −10 exclu | le cadre de la slide 47 n'entoure que « −10 » et « No data » |
| Données manquantes | remplacées par des valeurs par défaut | exclusion, pour chaque filtre | note 1 de la slide 50 |

Après ces 8 filtres : 1 247 → **692 titres** (555 exclus, soit 44,5 %). Pour comparaison, la slide 50 (données Kanopy au 30/09/2026, 1 109 titres) indique 539 exclus (49 %).

### B2. Contribution positive (slide 13)

- **Règle** : CA aligné Taxonomie UE (`EST_EU_TAXONOMY_MAX_REV`) ≥ 20 % **ou** objectif de réduction des émissions validé par SBTi.
- **Validation SBTi** : `near_term_status` ou `long_term_status` vaut « Validated Targets ». Un simple engagement, un engagement retiré, une absence de la base SBTi ou une donnée manquante ne valent jamais validation.
- **Avant (v1)** : Taxonomie > 0 %, Clean Tech ≥ 10 %, ITR ≤ 1,5 °C ou ODD ≥ 1. C'était beaucoup plus large que la slide 13.
- **Données SBTi depuis le 21/11** : la photo au 31/12/2024, lue par la même fonction que la version officielle (A1).
  - L'ancienne lecture reste en option commentée : la base de novembre 2026 (`companies-excel.xlsx` et `.csv`, téléchargés le 20/11/2026), complétée par **75 rapprochements par nom vérifiés à la main** (`SBTI_NAME_MATCHES`).
  - Ces rapprochements couvraient les fiches SBTi sans ISIN, avec un ancien ISIN ou une autre classe d'actions : Novo Nordisk, Straumann, QIAGEN, West Pharmaceutical, TE Connectivity…
  - 17 faux rapprochements avaient été rejetés : Ferrari Group, PPL Inc. au Japon, Nice Group, Mercedes-Benz AG, JAPAN POST Co., homonymes « X&Y »…
- **Résultat** : 692 → **335 titres** (390 avec la base de novembre 2026).

### B3. Filtre thématique : décision du groupe

- Le filtre actif est celui d'origine, avec le même remplacement d'Ansys par PTC que la version officielle (A3).
- **Constats** :
  - la règle « Industrie » ne faisait entrer que Cummins (moteurs diesel) et Kubota (tracteurs) ;
  - la règle « Tech avec ODD 9 ≥ 1 » fait entrer de la Tech générique (Intuit, Sage, Adobe, Capgemini…) ;
  - resserrer les seuils ODD vide la poche Tech et garde Cummins.
- **Deux options sont prêtes en commentaire.** Leurs résultats ont été recalculés le 21/11, avec le SBTi au 31/12/2024 et le filtre financier qualité :
  - `HealthTechAIScopeFilterV3` : tout le secteur Santé, plus les semi-conducteurs et les logiciels de conception et de simulation (Cadence, Synopsys, Dassault Systèmes, PTC). Résultat : **32 lignes**, 65,2 % Santé / 34,8 % Tech ;
  - `HealthTechAIScopeFilterV6b` : V3 plus des industriels choisis (Lifco, Wolters Kluwer, RELX, Schneider Electric, Legrand, VAT Group). Résultat : **35 lignes**, 54,0 % Santé / 32,5 % Tech / 13,5 % Industrie.
- **Pour activer une option** : décommenter la classe dans `filters_mohamed.py` (pour V6b, décommenter aussi V3), puis son import et la ligne `thematic_filter = ...` déjà prêts dans `run_tri_mohamed.py`.
- **Question ouverte** : faut-il ajouter Microsoft à la liste IA ?

### B4. Filtre financier

- C'est le filtre « qualité » décrit en A2 : je l'ai créé dans ma version le 20/11, puis il est passé dans la version officielle le 21/11.
- **Argument marketing** : la « durabilité financière ». Sur la slide 5, Kanopy définit l'investissement durable comme une double durabilité, extra-financière et financière.

### B5. Résultats de ma version (nos données au 31/12/2024)

| Étape | v1 | Ma version, SBTi de nov. 2026 | Ma version, SBTi au 31/12/2024 + PTC |
|---|---|---|---|
| Après les filtres extra-financiers du cours | 491 | 692 | 692 |
| Après la contribution positive (slide 13) | 412 | 390 | 335 |
| Après le filtre thématique | 77 | 80 | 67 |
| Après le filtre financier | 50 | 59 | 52 |
| **Lignes en portefeuille** | **50** | **57** | **50** |

- Avec le SBTi au 31/12/2024 : 51,5 % Santé, 40,1 % Tech, 8,5 % Consommation de base, ITR de 1,59 °C.
- L'optimiseur écarte 2 des 52 titres sélectionnables, à cause du plafond ITR ≤ 2,5 caché dans son code.

### B6. Comparaison avec la version officielle

| Point | Version officielle | Ma version |
|---|---|---|
| Température | ITR ≤ 2 °C | ITR < Q80 % (3,1 °C) |
| Pilier E | exclut E ≤ Q5 % | exclut E < Q5 % |
| Contribution positive | hybride : Taxonomie ≥ 20 %, SBTi validé, Clean Tech ≥ 10 % ou ITR ≤ 1,5 °C, **ou** ODD 3 ≥ 1, ODD 9 ≥ 1, autres ODD ≥ 1,5 | stricte : Taxonomie ≥ 20 % ou SBTi validé |
| Données SBTi | photo au 31/12/2024 | photo au 31/12/2024 |
| Filtre thématique | d'origine, PTC à la place d'Ansys | d'origine, PTC à la place d'Ansys |
| Filtre financier | qualité | qualité |
| Lignes en portefeuille | 61 | 50 |
| ITR du fonds | 1,53 °C | 1,59 °C |

### B7. Pour revenir à ma version

Dans `run_pipeline.py`, commenter la ligne `from src.run_tri import ...` et décommenter la ligne `from src.run_tri_mohamed import ...` juste en dessous.

## C. Ce qui reste à faire

- **Optimiseur** :
  - le rendement espéré est le rendement passé (biais in-sample) ;
  - la covariance est fabriquée avec des corrélations fixes (0,50 et 0,28) ;
  - les contraintes de secteur ne sont que des pénalités ;
  - « Industrie ≤ 15 % » et « ITR ≤ 1,8 °C » sont annoncées mais pas codées ;
  - un plafond caché ITR ≤ 2,5 °C écarte des titres.
  - Piste en cours : minimum de variance sous contraintes (slide 63) avec la vraie covariance tirée des prix, testée d'abord hors du dépôt.
- **Backtest** : il n'utilise aucun prix. À refaire avec `data/prix/`, avec une période hors échantillon à partir du 01/01/2025.
- **Livrables** : fichiers Excel et PowerPoint. Le README et les docs de Daphné (`README.md`, `docs/note_methodologique_filtres_sbti.md`, `docs/resultats_backtest.md`) indiquent encore 50 lignes et la base SBTi de 2026.
- **Décisions du groupe** : règle de température (≤ 2 °C ou Q80 %), contribution positive (hybride ou stricte), sort d'Eli Lilly et de Vertex (FCF négatif), entrée de Kirin, option thématique.
- **Limites à mentionner à l'oral** :
  - la photo SBTi vient d'une archive GitHub de l'export officiel, pas du site SBTi lui-même ;
  - l'exclusion PAB est approchée par le secteur Energy.

## D. Avantages et inconvénients (pour la soutenance)

**Ce que la démarche apporte :**
- Des filtres fidèles au cours (slides 41 à 50), appliqués à la date des données, avec la règle de la slide 50 sur les données manquantes. C'est facile à défendre devant les enseignants.
- Des données SBTi à la même date que nos données : pas de biais d'anticipation dans la sélection.
- Une contribution positive (slide 13) explicite et vérifiable : objectif SBTi validé ou CA aligné Taxonomie.
- Une prudence systématique : une donnée manquante ou un simple engagement ne valent jamais validation.
- Un filtre financier de « durabilité financière » (rentable, cash positif, peu endetté, pas trop volatil), sans sélection sur la performance passée, donc cohérent avec la mention AMF.
- De la traçabilité : rapprochements SBTi vérifiés et documentés, deux versions conservées, commentaires `# Modif Mohamed`.

**Limites et inconvénients :**
- SBTi et la Taxonomie mesurent le climat, pas la santé. Une lecture stricte écarte des leaders sans objectif SBTi (Eli Lilly, Vertex, Regeneron) : c'est la raison de la version hybride de Daphné.
- Le critère FCF > 0 écarte aussi Eli Lilly et Vertex de la version officielle, alors que ce sont des entreprises rentables.
- La règle de température du cours (Q80 %) laisse entrer des titres jusqu'à 3,1 °C. Il faut donc une contrainte de température au niveau du portefeuille (slide 40).
- L'exclusion PAB est approchée par le secteur Energy, faute de part de CA fossile dans les données.
- Les scores ODD de MSCI mesurent mal le lien avec la santé : l'ODD 3 vaut 0 pour de vraies valeurs santé (ICON, IQVIA) et pour toute la Tech. La règle ODD 3 ≥ 2 de la Consommation de base fait entrer un brasseur (Kirin).
- Les listes de logiciels IA et d'industriels, comme le choix de PTC, sont des choix discrétionnaires à justifier.
- L'optimiseur et le backtest restent à refaire : les chiffres de performance actuels ne sont pas fiables.

## E. Difficultés rencontrées (pour la soutenance)

- **Lire les règles exactes du cours** : les seuils ne figurent que dans les graphiques (cadres des slides 41 à 47). L'ancienne règle de température est en italique et ne compte pas dans le total. Les scopes du carbone ne sont pas précisés : il a fallu les déduire des niveaux de la figure 11.
- **Les dates** : nos données sont au 31/12/2024, celles du cours au 30/09/2026, et la base SBTi téléchargée date de novembre 2026. Il a fallu trouver une photo SBTi à la bonne date pour éviter le biais d'anticipation.
- **La jointure SBTi** : ISIN absents, anciens (divisions d'actions) ou d'une autre classe d'actions, et homonymes trompeurs (EQT, Ferrari, T&D…). Il a fallu vérifier les rapprochements à la main.
- **Les rachats d'entreprises** : Ansys a disparu de la cote en 2025, avec tout son historique de prix. Il a fallu une règle datée (offre de rachat en cours au 31/12/2024) et un remplaçant justifié.
- **L'arbitrage entre conformité et marketing** : la règle stricte écarte Eli Lilly, tandis que les règles fondées sur les ODD font entrer Cummins (moteurs diesel), des produits ménagers, un brasseur ou du logiciel de gestion dans un fonds « HealthTech & AI ».
- **La qualité des données** : ROE aberrants (jusqu'à 22 574 %), fonds propres négatifs, données manquantes, jours fériés différents selon les places.
- **Le travail à plusieurs sur le même code** : deux versions des filtres développées en parallèle, réconciliées en conservant les deux.

## F. Commits

| Commit | Contenu |
|---|---|
| `c18b2da` | filtres alignés sur le cours + règle SBTi de la slide 13 |
| `deef454` | marquage `# Modif Mohamed` |
| `2b60248` | rapprochements SBTi par nom, pilier E ≥ Q5, options thématiques V3 et V6b |
| `43e9ce1` | nouveau filtre financier dans ma version (ancien conservé en `FinancialQualityFilterDaphne`) |
| `14c3b5b` | fusion : version de Daphné comme version officielle, ma version dans `filters_mohamed.py` et `run_tri_mohamed.py` |
| `4005abc` | données SBTi au 31/12/2024 dans la version officielle, sorties régénérées (49 lignes) |
| `f73ad69` | `src/prices.py` sur le portefeuille final et `data/prix/` |
| commits du 21/11 après-midi | filtre financier qualité et PTC dans la version officielle (61 lignes), SBTi au 31/12/2024 dans ma version, `docs/filters.md` |

Tous ces commits sont poussés sur GitHub, sur la branche `filtres-slides-sbti` (`main` n'est pas modifiée).
