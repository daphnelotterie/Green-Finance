# Synapse HealthTech & AI

Projet de Finance durable du Master 272, Université Paris-Dauphine – PSL, à partir d'un univers de 1 247 valeurs du MSCI World au 31 décembre 2024. La thèse associe santé, MedTech et technologies de l'IA, avec suivi des ODD 3 et 9, du climat et du risque financier.

La pipeline conserve les classes de filtrage, les deux optimiseurs et le moteur de backtest existants. Les variantes sont sélectionnées par un mode, sans copier les modules selon l'auteur.

## Exécuter

Depuis la racine du dépôt, avec Python et les dépendances du projet :

```powershell
python -m pip install -r requirements.txt
python run_pipeline.py
```

La commande sans option exécute les trois modes, produit leurs résultats séparément et les compare :

| Mode | Sélection | Allocation |
|---|---|---|
| `daphne_original` | Daphné, version consolidée | Optimiseur Pedersen d'origine, corrigé |
| `daphne_esg_risk` | Même sélection Daphné | Budgets de risque ESG |
| `mohamed_esg_risk` | Règles de Mohamed | Budgets de risque ESG |

```powershell
python run_pipeline.py --mode daphne_original
python run_pipeline.py --mode daphne_esg_risk
python run_pipeline.py --mode mohamed_esg_risk
python run_pipeline.py --mode all --skip-history
python run_pipeline.py --mode all --refresh-prices
```

Les prix déjà présents permettent une exécution sans téléchargement. `--refresh-prices` renouvelle le cache et nécessite Internet. `--skip-history` limite le backtest à la période à partir de 2025 ; il conserve la sélection et l'optimisation au 31 décembre 2024.

## Organisation

```text
run_pipeline.py                  # Point d'entrée : sélection, allocation, backtest, graphiques
requirements.txt                 # Dépendances Python
src/
  filters.py                     # Company et classes de filtres partagées
  run_tri.py                     # Entonnoir selon le mode de sélection
  optimizer.py                   # Pedersen corrigé et budgets de risque ESG
  prices.py                      # Chargement des prix, change et cache EUR
  backtest.py                    # Séries historiques et indicateurs
  graphiques.py                  # Graphiques par mode et comparaisons
data/
  raw/
    all_data.csv                 # Univers et caractéristiques au 31/12/2024
    sbti/                        # Sources SBTi et rapprochement historique
  cache/prices/                  # Prix locaux, taux de change et prix EUR
results/
  daphne_original/               # Univers sélectionné, poids et backtests du mode
  daphne_esg_risk/
  mohamed_esg_risk/
  comparaison_modes.csv          # Comparaison produite par l'exécution
  graphiques/                   # Graphiques communs aux trois modes
docs/
  methodologie_et_chronologie.md # Règles, corrections et historique regroupés
  resultats.md                   # Analyse de la dernière exécution
cours/                           # Supports pédagogiques existants
Projet Final.pdf                 # Sujet du projet
```

Chaque dossier de mode contient ses sorties et ses graphiques. Les sources, le cache téléchargeable et les résultats calculés sont ainsi séparés ; une exécution d'un mode n'écrase pas les résultats des autres.

## Lire les résultats

La comparaison distingue les performances calculées sur les cours et les caractéristiques ESG de la photographie au 31 décembre 2024. Le benchmark de performance est l'ETF MSCI World `IWDA.AS`, coté en euros ; les comparaisons ESG utilisent les pondérations de l'univers source.

Les calculs historiques avant 2025 utilisent un univers sélectionné avec les données de fin 2024 : ils constituent une analyse rétrospective. L'évaluation à partir de 2025 conserve les poids décidés fin 2024, mais reste soumise aux limites du jeu de données et du cache de prix. Le projet est une simulation pédagogique à objectif durable ; les filtres ne constituent pas une certification SFDR Article 9 ou PAB.

Les règles détaillées, la chronologie des contributions et les corrections sont dans [Méthodologie et chronologie](docs/methodologie_et_chronologie.md). Les résultats effectivement exécutés, les graphiques et leurs limites sont dans [Résultats](docs/resultats.md).
