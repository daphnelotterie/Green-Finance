# Filtres du fonds Synapse HealthTech & AI : version finale (21/11/2026)

Ce document décrit l'état final de la sélection des titres (`src/filters.py` et `src/run_tri.py`). Pour chaque filtre, il donne la règle appliquée, la slide du cours, le nombre de valeurs restantes et ce qui a changé depuis la première version.

- **Données** : MSCI World au 31/12/2024 (`data/all_data.csv`, 1 247 valeurs).
- **Résultat** : **61 lignes en portefeuille**.
- Le détail des modifications de Mohamed, sa version alternative et les arguments pour la soutenance sont dans `docs/modifications_mohamed.md`.

## 1. L'entonnoir de sélection

| # | Filtre | Règle appliquée | Slides | Valeurs restantes |
|---|---|---|---|---|
| 1 | Exclusions PAB | armes controversées, tabac et secteur Energy exclus ; tabac sans donnée exclu | 44, 50 | 1 178 (−69) |
| 2 | DNSH | note de controverse E, S ou G < 2 exclue ; donnée manquante exclue | 42, 50 | 1 014 (−164) |
| 3 | Bonne gouvernance | notes ESG B et CCC exclues ; note manquante exclue | 41, 50 | 1 004 (−10) |
| 4 | Température | ITR ≤ 2 °C ; donnée manquante exclue | 43, 50 | 540 (−464) |
| 5 | Pilier E | note E ≤ quantile à 5 % de l'univers (3,0/10) exclue | 45, 50 | 526 (−14) |
| 6 | Empreinte carbone | scopes 1+2+3 : pire décile de chaque secteur exclu | 46 | 493 (−33) |
| 7 | Intensité carbone | scopes 1+2+3 : pire décile de chaque secteur exclu | 46 | 487 (−6) |
| 8 | ODD climat | score de −10 sur l'ODD 7, 12 ou 13 exclu | 47 | 483 (−4) |
| 9 | Contribution positive (SFDR art. 2(17)) | voir ci-dessous | 13 | **420** (−63) |
| 10 | Univers thématique HealthTech & AI | voir ci-dessous | 62 | 75 |
| 11 | Univers financier « qualité » | voir ci-dessous | 59, 62 | **61** |

Les filtres 1 à 9 forment l'univers extra-financier éligible à l'article 9 : 420 valeurs sur 1 247, soit 66,3 % d'exclusions. L'optimiseur garde ensuite les 61 valeurs sélectionnables : il les pondère sans en exclure aucune.

**Filtre 9, contribution positive (règle hybride).** Une valeur est retenue si elle passe la voie climat **ou** la voie santé et sociale :
- **voie climat** : au moins 20 % de CA aligné Taxonomie, un objectif SBTi validé au 31/12/2024, au moins 10 % de CA Clean Tech, ou un ITR ≤ 1,5 °C ;
- **voie santé et sociale** : ODD 3 ≥ 1, ODD 9 ≥ 1, ou ODD 1, 2, 4, 6 ou 11 ≥ 1,5.

Un simple engagement SBTi, une absence de la base SBTi ou une donnée manquante ne comptent jamais comme une validation.

**Filtre 10, univers thématique (discrétionnaire)** :
- **Santé** : tout le secteur Health Care ;
- **Tech** : ODD 3 ≥ 1, ou ODD 9 ≥ 1 dans le logiciel, les semi-conducteurs, l'informatique ou l'électronique ;
- **Industrie** : ODD 3 ≥ 1, ou une liste nominative (Pentair, Mettler, Halma, Cummins, Siemens) ;
- **Consommation de base** : ODD 3 ≥ 2.

S'y ajoute un choix discrétionnaire : **Ansys est écartée et remplacée par PTC**. Ansys faisait l'objet d'une offre de rachat définitive de Synopsys au 31/12/2024 ; elle a quitté la cote en juillet 2025, et il n'existe plus aucun cours pour elle. PTC fait, comme Ansys, des logiciels de conception et de simulation, et elle passe tous les autres filtres.

**Filtre 11, univers financier « qualité »** :
- ROIC > 5 % ou marge nette > 5 % ;
- FCF yield > 0 ;
- dette / actifs < 65 % ;
- volatilité à 5 ans ≤ 46,9 % (90e centile du MSCI World) ;
- une donnée manquante entraîne l'exclusion.

## 2. Ce qui a changé depuis la première version

| Filtre | Première version | Version finale | Pourquoi |
|---|---|---|---|
| Données manquantes | remplacées par des valeurs par défaut | exclusion, pour chaque filtre | note 1 de la slide 50 |
| PAB | armes, tabac, secteur Energy | idem, tabac sans donnée exclu | règle des données manquantes |
| Bonne gouvernance | notes B/CCC et pilier G ≤ 3 exclus | notes B/CCC et notes manquantes exclues | le pilier G n'est pas un critère du cours |
| Pilier E | absent | note E ≤ Q5 % exclue | slides 45 et 50 |
| Carbone | intensité scopes 1+2 | empreinte **et** intensité scopes 1+2+3 | slide 46 |
| ODD climat | score < −1 exclu | score = −10 exclu | cadre de la slide 47 |
| Contribution positive | Taxonomie > 0 %, Clean Tech ≥ 10 %, ITR ≤ 1,5 °C ou ODD ≥ 1 | règle hybride (ci-dessus), avec Taxonomie ≥ 20 % et SBTi validé | slide 13 : 20 % de CA durable ou objectif SBTi validé |
| Données SBTi | aucune | statuts au 31/12/2024 (photo SBTi du 13/01/2025) | même date que nos données, sans biais d'anticipation |
| Univers thématique | règles d'origine | idem, Ansys remplacée par PTC | Ansys rachetée et retirée de la cote |
| Univers financier | Sharpe ≥ 0,10, rendement 5 ans > 0, ROE/ROIC/marge > 5 %, dette < 65 % | qualité : rentabilité, FCF > 0, dette < 65 %, volatilité ≤ Q90 | ne plus sélectionner sur la performance passée (biais in-sample, mention AMF) et appliquer vraiment le FCF |

La température est restée à **ITR ≤ 2 °C**, ce qui est plus strict que la règle du cours depuis février 2024 (ITR < Q80 % de l'univers, soit 3,1 °C).

**Historique** :
- **première version** (Daphné) ;
- **20/11** (Mohamed) : filtres alignés sur les slides 41 à 50 et règle SBTi de la slide 13 ;
- **21/11** (Daphné, v2) : reprise de ces filtres, avec la contribution positive hybride et l'ITR ≤ 2 °C ;
- **21/11** (Mohamed) : données SBTi au 31/12/2024, filtre financier « qualité », PTC à la place d'Ansys, module de prix `src/prices.py`.

## 3. Données utilisées

| Fichier | Contenu | Utilisation |
|---|---|---|
| `data/all_data.csv` | MSCI World au 31/12/2024 : 1 247 valeurs, 100 colonnes | univers de départ |
| `data/sbti/msci_world_jointure_sbti_2025-01-13.csv` | nos 1 247 valeurs + leur statut SBTi au 13/01/2025, avec la méthode de rapprochement | lu par `run_tri.py` |
| `data/sbti/sbti_2025-01-13_plan_b.csv` | la photo SBTi complète du 13/01/2025 (10 534 entreprises) | traçabilité |
| `data/sbti/companies-excel.xlsx` et `.csv` | base SBTi de novembre 2026 | non utilisée : postérieure à nos données |
| `data/prix/` | cours en euros des 61 lignes et du MSCI World (ETF IWDA), du 02/01/2015 au 20/11/2026 | futur backtest |

Une validation SBTi ne compte que si sa publication avant le 31/12/2024 est confirmée (506 valeurs). La base de novembre 2026 en aurait compté 89 de trop.

## 4. Le portefeuille obtenu

- **61 lignes** :
  - Santé 51,6 % (33 lignes) ;
  - Tech 35,9 % (19 lignes) ;
  - Consommation de base 8,0 % (8 lignes) ;
  - Industrie 4,5 % (Pentair).
- **Au plafond de 4,5 %** : Novo Nordisk, Intuit, Cadence, Regeneron, Advantest, Chugai, NEC, Pentair, Molina et SOBI. PTC pèse 3,9 % et AstraZeneca 2,1 % ; les 49 autres lignes pèsent 1 % chacune.
- **ITR du fonds** : 1,53 °C, contre 2,39 °C pour l'indice.
- **Intensité carbone par rapport à l'indice** : −81,5 % sur les scopes 1+2 et −66,9 % sur les scopes 1+2+3.

Les pondérations viennent de l'optimiseur actuel (Pedersen). Il doit être remplacé par un minimum de variance sous contraintes, calculé avec la vraie covariance des prix : ce travail est en cours de test. Les chiffres de performance de `backtest.py` ne sont pas fiables, car il n'utilise aucun prix.

## 5. Points à trancher en groupe

- **Température** : garder ITR ≤ 2 °C, ou appliquer la règle du cours (ITR < Q80 %) avec une contrainte de température au niveau du portefeuille ?
- **Eli Lilly et Vertex** : le critère FCF > 0 les écarte, car leur FCF yield est négatif dans nos données au 31/12/2024. Faut-il assouplir ce critère ?
- **Kirin** (brasseur, maison mère de Kyowa Kirin) entre à 1 % par la règle « Consommation de base, ODD 3 ≥ 2 ». Faut-il la garder dans un fonds santé ?
- **PTC** : son cours fait +33 % le 05/10/2026, à vérifier. Cela n'a pas d'effet sur la sélection, qui est faite au 31/12/2024.
- **Version alternative** (Mohamed : ITR < Q80 %, contribution stricte Taxonomie ≥ 20 % ou SBTi validé) : 50 lignes. Pour l'activer, voir `docs/modifications_mohamed.md`.

## 6. Relancer la sélection

1. `python run_pipeline.py` : sélection, optimiseur et backtest actuel.
2. `python src/prices.py` : prix du portefeuille final ; il faut internet.

Fichiers produits :
- `data/actifs_notre_secteur_healthtech_ai.csv` : les 61 valeurs sélectionnables ;
- `data/portefeuille_final_pondere.csv` : les poids ;
- `data/sbti/jointure_sbti_msci.csv` : le statut SBTi de chaque valeur ;
- `data/prix/` : les séries de prix.
