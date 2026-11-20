# Synapse HealthTech & AI Equity Fund
**Fonds d'Actions Internationales — Classification SFDR Article 9 & Paris-Aligned Benchmark (PAB)**

> **Master 272 — Ingénierie Financière & Finance Quantitative**  
> **Université Paris-Dauphine — PSL**  
> **Cours : Finance Durable**  
> **Enseignants :** Thierry BÉCHU (*Directeur des Gestions, Kanopy AM*) & Jean JARDEL (*Quantitative Researcher, Kanopy AM*)  
> **Thématique du Fonds :** Santé, MedTech & Intelligence Artificielle (Deep Tech médicale, drug discovery computationnelle, semi-conducteurs biomédicaux et diagnostic précoce).

---

## 1. Vue d'Ensemble & Précision Réglementaire SFDR

Une entreprise n'est pas « Article 9 » en soi : **seul le fonds (le produit financier) peut être classifié Article 9**.  
Les entreprises composant le portefeuille doivent quant à elles satisfaire au statut d'**Investissement Durable** au sens de l'**Article 2(17) SFDR** (contribution positive environnementale ou sociale, respect du principe DNSH et pratiques de bonne gouvernance).

Le fonds **Synapse HealthTech & AI** est un fonds actions de conviction internationale labellisé **Article 9 SFDR**. Il capitalise sur la convergence séculaire entre :
1. **Les sciences de la vie et la santé** (biotechnologies, thérapies géniques, robotique chirurgicale, diagnostics).
2. **L'intelligence artificielle computationnelle** (modélisation moléculaire, calcul accéléré, simulation d'essais cliniques, instrumentation d'imagerie).

Le portefeuille est construit à l'intersection rigoureuse de **trois univers** selon le modèle méthodologique présenté par **Jean Jardel (Slide 62)** :
$$\text{Univers Sélectionnable} = \text{Univers Extra-Financier (Art. 2(17) / PAB)} \cap \text{Univers Thématique Discrétionnaire} \cap \text{Univers Financier Quantitatif}$$

L'allocation est résolue via la théorie de la **Frontière ESG-Efficiente de Pedersen, Fitzgibbons et Pomorski (2021, *Journal of Financial Economics*)** formulée sous contraintes convexes selon la **Slide 63 du cours**.

---

## 2. Structure et Organisation du Projet

```text
Final_project/
├── run_pipeline.py                 # Script maître : exécute tri, optimisation et backtest en 1 clic
├── README.md                       # Documentation générale du projet et guide d'exécution
├── Projet Final.pdf                # Sujet officiel et consignes de notation
│
├── data/                           # DOSSIER DES DONNÉES & FICHIERS CSV (LIVRABLES EXCEL)
│   ├── all_data.csv                # Données brutes initiales (1 247 valeurs MSCI World)
│   ├── actifs_notre_secteur_healthtech_ai.csv # 50 valeurs éligibles sélectionnées dans notre scope
│   ├── portefeuille_final_pondere.csv         # Livrable officiel : Portefeuille final avec poids (Excel)
│   └── resultats_backtest_comparaison.csv     # Livrable officiel : Tableau de backtest comparatif (Excel)
│
├── src/                            # CODE SOURCE PYTHON (ORIENTÉ OBJET & SANS DÉPENDANCES LOURDES)
│   ├── __init__.py
│   ├── filters.py                  # Classes de filtres POO (Slides 24, 40-52 de Jean Jardel)
│   ├── run_tri.py                  # Moteur d'application de l'entonnoir de filtrage
│   ├── optimizer.py                # Optimiseur quadratique de Pedersen (Slide 63, Water-Filling)
│   └── backtest.py                 # Moteur de backtest multi-horizons (1Y, 5Y, 10Y)
│
├── docs/                           # DOSSIER DES RAPPORTS ET SUPPORTS DE SOUTENANCE
│   ├── resultats_backtest.md       # Analyse financière/ESG complète et plan des 10 slides
│   ├── criteres_article_9_sfdr.md  # Note technique sur la réglementation SFDR Art. 9, DNSH et doctrine AMF
│   ├── strategie_fonds_healthtech_ai_art9.md # Thèse d'investissement et piliers du fonds
│   ├── strategies_quantitatives.md # Comparatif académique des 4 stratégies quantitatives
│   └── strategies_quantitatives.pdf# Support PDF des stratégies quantitatives
│
├── Cours/                          # SUPPORTS DE COURS OFFICIELS DES PROFESSEURS
│   ├── Finance_Durable_Approche_Quantitative.pdf # Cours Jean Jardel (Kanopy AM, 65 slides)
│   ├── Cours_gouvernance_2026-2027_finale.pdf   # Cours Thierry Béchu (Gouvernance & FCF Jensen)
│   ├── 272 - Finance Durable - 2026-2027 - N°1-1.pdf
│   ├── 272 - Finance Durable - 2026-2027 - N°2.pdf
│   └── 272 - Finance Durable - 2026-2027 - N°4.pdf
│
└── dossier_tri/                    # Miroir conservé pour rétro-compatibilité
```

---

## 3. Guide de Démarrage Rapide (Quick Start)

Le projet est conçu en **Python 3 standard pur** : aucune installation complexe de packages (`numpy`, `scipy` ou `pandas`) n'est requise. Il s'exécute directement en **moins de 2 secondes**.

```bash
python3 run_pipeline.py
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
| **📁** | **UNIVERS EXTRA-FINANCIER ÉLIGIBLE SFDR ART. 2(17)** | **Slide 50 & 62** | **412 valeurs** | **-67.0% sélectivité** |
| **8** | **Univers Thématique Discrétionnaire** (HealthTech & AI Scope) | Slide 62 | **77 valeurs** | - |
| **9** | **Univers Financier Quantitatif** (FCF Jensen 1986, ROE/ROIC $> 5\%$, Sharpe $> 0.10$) | Slide 59 & 62 | **50 valeurs** | - 27 |
| **🎯** | **UNIVERS SÉLECTIONNABLE FINAL DU FONDS** | **Slide 62 & 63** | **50 valeurs** | **Portefeuille final** |

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

## 7. Livrables Officiels pour le Rendu

Conformément aux consignes du fichier `Projet Final.pdf`, les livrables à transmettre à Thierry Béchu et Jean Jardel sont :

1. **Fichier Excel des Actifs et Pondérations :**  
   Fichier [`data/portefeuille_final_pondere.csv`](file:///Users/daphnelotterie/Desktop/Etudes/M2%20272/Green%20Finance/Final_project/data/portefeuille_final_pondere.csv).
2. **Fichier Excel des Données Complémentaires :**  
   Fichier [`data/resultats_backtest_comparaison.csv`](file:///Users/daphnelotterie/Desktop/Etudes/M2%20272/Green%20Finance/Final_project/data/resultats_backtest_comparaison.csv).
3. **Support de Présentation (PowerPoint de 10 Slides) :**  
   La trame complète des 10 diapositives est rédigée dans [`docs/resultats_backtest.md`](file:///Users/daphnelotterie/Desktop/Etudes/M2%20272/Green%20Finance/Final_project/docs/resultats_backtest.md).
