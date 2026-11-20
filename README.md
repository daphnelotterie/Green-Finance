# Synapse HealthTech & AI Equity Fund
**Fonds d'Actions Internationales — Classification SFDR Article 9 & Paris-Aligned Benchmark (PAB)**

> **Master 272 — Ingénierie Financière & Finance Quantitative**  
> **Université Paris-Dauphine — PSL**  
> **Cours : Finance Durable**  
> **Enseignants :** Thierry BÉCHU (*Directeur des Gestions, Kanopy AM*) & Jean JARDEL (*Quantitative Researcher, Kanopy AM*)  
> **Thématique du Fonds :** Santé, MedTech & Intelligence Artificielle (Deep Tech médicale, drug discovery computationnelle, semi-conducteurs biomédicaux et diagnostic précoce).

---

## 1. Vue d'Ensemble & Thèse d'Investissement

Le fonds **Synapse HealthTech & AI** est un fonds actions de conviction internationale labellisé **Article 9 SFDR** (objectif d'investissement durable au sens de l'Article 2(17) SFDR). 

Il capitalise sur la convergence séculaire entre :
1. **Les sciences de la vie et la santé** (biotechnologies, thérapies géniques, robotique chirurgicale, diagnostics).
2. **L'intelligence artificielle computationnelle** (modélisation moléculaire, puissance de calcul accéléré, simulation d'essais cliniques, instrumentation d'imagerie).

Le portefeuille est construit à l'intersection rigoureuse de **trois univers** selon le modèle méthodologique présenté par **Jean Jardel (Slide 62)** :
$$\text{Univers Sélectionnable} = \text{Univers Extra-Financier (Art. 9 / PAB)} \cap \text{Univers Thématique Discrétionnaire} \cap \text{Univers Financier Quantitatif}$$

L'allocation est résolue via la théorie de la **Frontière ESG-Efficiente de Pedersen, Fitzgibbons et Pomorski (2021, *Journal of Financial Economics*)** formulée sous contraintes convexes selon la **Slide 63 du cours**.

---

## 2. Structure et Organisation du Projet

Le projet a été restructuré pour permettre une auditabilité totale et un partage immédiat entre collègues et avec le jury :

```text
Final_project/
├── run_pipeline.py                 # Script maître : exécute le tri, l'optimisation et le backtest en 1 clic
├── README.md                       # Documentation générale du projet et guide d'exécution
├── Projet Final.pdf                # Sujet officiel et consignes d'évaluation du cours
│
├── data/                           # DOSSIER CENTRAL DES DONNÉES ET LIVRABLES CSV
│   ├── all_data.csv                # Univers initial brut : 1 247 valeurs (MSCI World Developed Markets)
│   ├── actifs_tous_article_9.csv   # Livrable 1 : 412 entreprises éligibles SFDR Article 9 (tous secteurs)
│   ├── actifs_notre_secteur_healthtech_ai.csv # Livrable 2 : 50 entreprises qualifiées dans notre scope
│   ├── portefeuille_final_pondere.csv         # Livrable 3 : Portefeuille final avec pondérations optimisées (Excel)
│   └── resultats_backtest_comparaison.csv     # Livrable 4 : Tableau comparatif complet de backtest (Excel)
│
├── src/                            # CODE SOURCE PYTHON (ARCHITECTURE ORIENTÉE OBJET)
│   ├── __init__.py
│   ├── filters.py                  # Classes de filtres POO (Slides 24, 40-52 de Jean Jardel)
│   ├── run_tri.py                  # Moteur d'application de l'entonnoir de sélection
│   ├── optimizer.py                # Optimiseur quadratique de Pedersen (Slide 63, Water-Filling)
│   └── backtest.py                 # Moteur de calcul multi-horizons (1Y, 5Y, 10Y) et risques de queue
│
├── docs/                           # RAPPORTS ET SUPPORTS POUR LA PRÉSENTATION ORALE
│   ├── resultats_backtest.md       # Rapport d'analyse financière & extra-financière et plan des 10 slides
│   ├── criteres_article_9_sfdr.md  # Note technique sur la réglementation SFDR Art. 9, DNSH et doctrine AMF
│   ├── strategie_fonds_healthtech_ai_art9.md # Thèse d'investissement détaillée et 4 piliers du fonds
│   ├── strategies_quantitatives.md # Synthèse académique des 4 stratégies quantitatives proposées
│   └── strategies_quantitatives.pdf# Version PDF mise en page des stratégies quantitatives
│
├── Cours/                          # SUPPORTS DE COURS OFFICIELS DES ENSEIGNANTS
│   ├── Finance_Durable_Approche_Quantitative.pdf # Cours complet d'approche quantitative (J. Jardel, 65 slides)
│   ├── Cours_gouvernance_2026-2027_finale.pdf   # Cours sur la théorie de la gouvernance (T. Béchu)
│   ├── 272 - Finance Durable - 2026-2027 - N°1-1.pdf # Cours 1 : Limites planétaires et climat
│   ├── 272 - Finance Durable - 2026-2027 - N°2.pdf   # Cours 2 : Cadre SFDR et indices PAB
│   └── 272 - Finance Durable - 2026-2027 - N°4.pdf   # Cours 4 : Agrégation et notation ESG
│
└── dossier_tri/                    # Dossier miroir conservé pour rétro-compatibilité
```

---

## 3. Guide de Démarrage Rapide (Quick Start)

Le projet est conçu en **Python 3 standard pur** : aucune installation complexe de packages (`numpy`, `scipy` ou `pandas`) n'est requise. Il s'exécute directement sur n'importe quel ordinateur en **moins de 2 secondes**.

### Exécution du Pipeline Complet en 1 Commande :
Depuis la racine du projet :
```bash
python3 run_pipeline.py
```

### Exécution Modulaire Étape par Étape :
```bash
# 1. Exécuter l'entonnoir de filtrage extra-financier et thématique
python3 src/run_tri.py

# 2. Exécuter l'optimisation des poids de Pedersen (Frontière ESG-Efficiente)
python3 src/optimizer.py

# 3. Exécuter le moteur de backtest comparatif
python3 src/backtest.py
```

---

## 4. Méthodologie : L'Entonnoir de Sélection (Slides 40 à 52)

L'univers de départ de 1 247 valeurs du MSCI World est filtré pas à pas selon les critères enseignés par Jean Jardel :

| Étape | Filtre Appliqué | Référence Cours (J. Jardel) | Valeurs Restantes | Valeurs Éliminées |
| :---: | :--- | :---: | :---: | :---: |
| **0** | **Univers de Départ MSCI World** | Slide 28 | **1 247** | - |
| **1** | **Exclusions PAB & Combustibles Fossiles** (0% armes, tabac, pétrole/charbon) | Slide 44 & 50 | **1 185** | - 62 |
| **2** | **DNSH - Controverses Sévères** (Scores E, S, G $\ge 2.0$, pas d'alerte rouge) | Slide 42 & 50 | **1 022** | - 163 |
| **3** | **Bonne Gouvernance & Notation ESG** (Pas de `CCC`/`B`, Pilier G $> 3.0/10$) | Slide 41, 45 & 50 | **992** | - 30 |
| **4** | **Accord de Paris - Climat** (Trajectoire $\text{ITR} \le 2.0^\circ\text{C}$) | Slide 43 & 50 | **536** | - 456 |
| **5** | **Intensité Carbone Sectorielle** (Exclusion du pire décile 10% Scope 1+2 par secteur) | Slide 46 & 50 | **505** | - 31 |
| **6** | **ODD Climatiques** (Exclusion des atteintes nettes aux ODD 7, 12, 13) | Slide 47 & 50 | **491** | - 14 |
| **7** | **Contribution Positive Substantielle** (SFDR Art. 2(17) condition 1) | Slide 24 | **412** | - 79 |
| **📁** | **UNIVERS EXTRA-FINANCIER ARTICLE 9 GLOBAL** | **Slide 50 & 62** | **412 valeurs** | **-67.0% sélectivité** |
| **8** | **Univers Thématique Discrétionnaire** (HealthTech & AI Scope) | Slide 62 | **77 valeurs** | - |
| **9** | **Univers Financier Quantitatif** (FCF Jensen 1986, ROE/ROIC $> 5\%$, Sharpe $> 0.10$) | Slide 59 & 62 | **50 valeurs** | - 27 |
| **🎯** | **UNIVERS SÉLECTIONNABLE FINAL** | **Slide 62 & 63** | **50 valeurs** | **Portefeuille final** |

> **Validation Slide 52 (Les Exclus Notables) :**  
> Notre filtre élimine fidèlement les grandes valeurs citées par Jean Jardel : **NVIDIA, AMD, Broadcom, Micron** (exclus par l'ITR $> 2.0^\circ\text{C}$), **Apple, Amazon, Tesla, Meta** (exclus par le DNSH social $< 2.0$) et **Alphabet** (exclu par la gouvernance $\le 3.0$).

---

## 5. Stratégie Quantitative d'Allocation (Slide 63)

Le portefeuille est pondéré selon la formulation mathématique de la diapositive 63 du cours :

$$\min_W \quad f(W) = \frac{\gamma}{2} W^T \Sigma W - W^T \mu - \theta \cdot W^T S_{\text{Impact}}$$

Sous les contraintes institutionnelles suivantes :
$$\begin{cases}
\sum_{i=1}^{50} w_i = 1 & \text{(Plein investissement)} \\
1.0\% \le w_i \le 4.5\% & \text{(Bornes UCITS 5/10/40 : aucun actif} > 5\% \text{)} \\
\sum_{i \in \text{Santé}} w_i \in [50\%, 65\%] & \text{(Cœur de thèse HealthTech)} \\
\sum_{i \in \text{Tech IA}} w_i \in [28\%, 40\%] & \text{(Puissance computationnelle \& Enablers)} \\
\sum_{i \in \text{Industrie}} w_i \le 15\% & \text{(Filtration \& Instruments de précision)}
\end{cases}$$

* **$\gamma = 3.0$** : Aversion institutionnelle au risque.
* **$\theta = 0.04$** : Intensité du tilt d'impact extra-financier le long de la frontière de Pedersen.
* **$\Sigma$** : Matrice de covariance structurée (modèle Elton-Gruber : $\rho_{\text{intra}} = 0.50$, $\rho_{\text{inter}} = 0.28$).
* **$S_{\text{Impact}}$** : Score composite standardisé en $z$-scores :
  $$S_{\text{Impact}, i} = 0.40 \cdot z(\text{ODD\_03}_i) + 0.25 \cdot z(\text{ODD\_09}_i) - 0.20 \cdot z(\text{ITR}_i) + 0.15 \cdot z(\text{Gov}_i)$$
* **Algorithme de Résolution :** Descente de gradient projetée avec projection exacte de *Water-Filling* par bissection.

---

## 6. Résultats Synthétiques du Backtest Comparatif

Les métriques sont issues de [`data/resultats_backtest_comparaison.csv`](file:///Users/daphnelotterie/Desktop/Etudes/M2%20272/Green%20Finance/Final_project/data/resultats_backtest_comparaison.csv) :

| Indicateur Analysé | Synapse HealthTech & AI (Optimisé Pedersen) | Équipondéré ($1/N$) | Benchmark Marché (MSCI World) | Valeur Ajoutée M2 272 |
| :--- | :---: | :---: | :---: | :--- |
| **Rendement Annualisé (5 Ans)** | **18.85%** | 14.02% | 20.58% | **+4.83% par an vs $1/N$** (Alpha d'optimisation pure) |
| **Volatilité Annualisée (5 Ans)** | **20.93%** | 19.94% | 34.54% | **-13.61 points de volatilité** vs marché |
| **Ratio de Sharpe (5 Ans, $R_f=2\%$)** | **0.81** | 0.60 | 0.56 | **+44.6% d'efficience ajustée du risque** vs indice |
| Ratio de Sharpe (10 Ans) | **0.82** | 0.76 | 0.60 | Régularité de la thèse séculaire (+36.7% vs indice) |
| Maximum Drawdown (5 Ans) | **-41.31%** | -41.91% | -45.54% | Chute maximale contenue de +4.23 points |
| Value-at-Risk 95% (Journalière) | **-2.09%** | -2.01% | -3.09% | Risque de perte journalier réduit d'un tiers |
| Expected Shortfall (CVaR 95%) | **-2.65%** | -2.54% | -4.83% | Risque extrême divisé par près de deux |
| **Trajectoire Climatique ITR** | **1.52°C** | 1.54°C | 2.39°C | **Strictement aligné Accord de Paris 1.5°C** |
| **Intensité Carbone Scope 1+2** | **9.6 tCO₂e/M$** | 10.5 | 95.6 | **-89.9% d'émissions** (Exigence PAB : -50%) |
| **Intensité Carbone Totale (1+2+3)**| **386.3 tCO₂e/M$**| 439.6 | 851.9 | **-54.7% de réduction** (Scope 3 amont/aval inclus) |
| Score Alignement ODD 3 (Santé) | **+1.71** | +1.25 | -0.11 | Contribution positive démontrée (SFDR Art. 2(17)) |
| Score Gouvernance (Kanopy) | **6.67 / 10** | 6.63 | 5.65 | **+18.1% de qualité managériale** (Aligné Jensen 1986) |
| Nombre de Titres & Poids Max | **50 titres / 4.50%**| 50 / 2.0% | 1 247 / 4.8% | **100% Conforme règle UCITS 5/10/40** |
| Répartition Sectorielle | **51.6% Santé / 39.9% Tech IA / 8.5% Industrie** | - | Équilibre défensif/croissance maîtrisé |

---

## 7. Principales Valeurs en Portefeuille (Top Convictions)

Le fichier [`data/portefeuille_final_pondere.csv`](file:///Users/daphnelotterie/Desktop/Etudes/M2%20272/Green%20Finance/Final_project/data/portefeuille_final_pondere.csv) détaille l'ensemble des 50 positions. Les premières lignes à la borne maximale de **4.50%** illustrent parfaitement la thèse :
* **Eli Lilly & Co (`LLY US`, 4.50%)** : Rdt 5Y = 44.9%, ITR = 1.5°C, leader mondial GLP-1 (obésité/diabète) et drug design par IA.
* **Cadence Design Systems (`CDNS US`, 4.50%)** : Rdt 5Y = 35.3%, ITR = 1.3°C, logiciels de conception de puces accélératrices biomédicales.
* **Novo Nordisk (`NOVOB DC`, 4.50%)** : Rdt 5Y = 27.2%, ITR = 1.3°C, leader des traitements métaboliques, décarbonation exemplaire.
* **ASM International (`ASM NA`, 4.50%)** : Rdt 5Y = 41.2%, ITR = 1.4°C, dépôts en couches atomiques pour processeurs d'IA.
* **Advantest Corp (`6857 JP`, 4.50%)** : Rdt 5Y = 36.5%, ITR = 2.0°C, testeurs de puces graphiques utilisées en imagerie médicale.
* **Pentair PLC (`PNR US`, 4.50%)** : Rdt 5Y = 19.6%, ITR = 2.0°C, filtration d'eau ultra-pure et fluides critiques pour la biopharmacie.
* **Regeneron Pharmaceuticals (`REGN US`, 4.50%)** : Rdt 5Y = 15.1%, ODD 3 = +5.0, plateforme d'anticorps optimisés par génétique computationnelle.
* **Vertex Pharmaceuticals (`VRTX US`, 4.50%)** : Rdt 5Y = 14.4%, ODD 3 = +4.5, thérapies géniques CRISPR (Casgevy).

---

## 8. Livrables pour la Remise du Projet Final

Conformément aux consignes du fichier `Projet Final.pdf`, les éléments à transmettre à Thierry Béchu et Jean Jardel sont :

1. **Fichier Excel des Actifs et Pondérations :**  
   Fichier [`data/portefeuille_final_pondere.csv`](file:///Users/daphnelotterie/Desktop/Etudes/M2%20272/Green%20Finance/Final_project/data/portefeuille_final_pondere.csv), directement importable sous Excel (colonnes ticker, nom, isin, secteur, poids en %, rendement 5Y, volatilité, Sharpe, ITR, scores ODD et gouvernance).
2. **Fichier Excel des Données Complémentaires :**  
   Fichier [`data/resultats_backtest_comparaison.csv`](file:///Users/daphnelotterie/Desktop/Etudes/M2%20272/Green%20Finance/Final_project/data/resultats_backtest_comparaison.csv), contenant l'ensemble des métriques comparatives et historiques.
3. **Support de Présentation (PowerPoint de 10 Slides) :**  
   La trame complète des 10 diapositives est rédigée dans [`docs/resultats_backtest.md`](file:///Users/daphnelotterie/Desktop/Etudes/M2%20272/Green%20Finance/Final_project/docs/resultats_backtest.md).
