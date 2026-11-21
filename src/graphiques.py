#!/usr/bin/env python3
"""
GRAPHIQUES DE PERFORMANCE DU FONDS
----------------------------------
Master 272 - Finance Durable (Université Paris-Dauphine)
Enseignants : Thierry Béchu & Jean Jardel (Kanopy AM)

Trace la valeur de 100 € investis pour plusieurs portefeuilles, avec une couleur fixe par portefeuille.
Palette de référence vérifiée pour le daltonisme. Le jaune et le vert ont un contraste faible sur fond clair :
chaque courbe est donc nommée en bout de ligne, et les chiffres sont aussi exportés en tableau (CSV).
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

FOND, ENCRE, ENCRE_2, DISCRET, GRILLE, AXE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

# Une couleur fixe par portefeuille (elle ne change pas d'un graphique à l'autre)
COULEURS = {
    "mohamed_esg_risk": "#2a78d6",  # filtres stricts + budgets de risque ESG
    "daphne_original": "#eb6834",   # filtres hybrides + Pedersen corrigé
    "equipondere": "#1baf7a",   # vert d'eau : équipondéré 1/N sur les mêmes titres
    "daphne_esg_risk": "#b68100",  # filtres hybrides + budgets de risque ESG
    "thematique_recalibree": "#6250d6",  # violet : stratégie A, TE minimale + diversification maximale
    "msci_world": "#52514e",    # encre neutre : indice de référence
}

MOIS = {1: "janv.", 2: "févr.", 3: "mars", 4: "avr.", 5: "mai", 6: "juin", 7: "juil.", 8: "août", 9: "sept.",
        10: "oct.", 11: "nov.", 12: "déc."}


def nombre_fr(x):
    return f"{x:,.1f}".replace(",", " ").replace(".", ",")


def date_fr(x, _):
    d = mdates.num2date(x)
    return f"{d.year}" if d.month == 1 else f"{MOIS[d.month]} {d.year}"


def ecarter_etiquettes(valeurs, ecart):
    """Écarte verticalement les étiquettes de fin de courbe pour éviter qu'elles se chevauchent."""
    ordre = sorted(range(len(valeurs)), key=lambda i: valeurs[i])
    positions = list(valeurs)
    for a, b in zip(ordre, ordre[1:]):
        if positions[b] - positions[a] < ecart:
            positions[b] = positions[a] + ecart
    return positions


def tracer_performances(courbes, titre, sous_titre, chemin):
    """
    courbes : liste de (libellé, série de valeurs en base 1, couleur, épaisseur).
    Enregistre un PNG : valeur de 100 € investis, chaque courbe nommée en bout de ligne avec sa valeur finale.
    """
    fig, ax = plt.subplots(figsize=(10, 5.8), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax.set_facecolor(FOND)
    for libelle, serie, couleur, epaisseur in courbes:
        ax.plot(serie.index, serie * 100, color=couleur, lw=epaisseur, label=libelle, solid_capstyle="round")

    fins = [serie.dropna().iloc[-1] * 100 for _, serie, _, _ in courbes]
    hauteur = ax.get_ylim()[1] - ax.get_ylim()[0]
    for (libelle, serie, couleur, _), y, y_etiquette in zip(courbes, fins, ecarter_etiquettes(fins, hauteur * 0.045)):
        x_fin = serie.dropna().index[-1]
        ax.scatter([x_fin], [y], s=36, color=couleur, zorder=5, edgecolors=FOND, linewidths=1.5)
        # l'étiquette est placée à y_etiquette (écartée des voisines), le point reste sur la vraie valeur
        ax.annotate(f"{libelle}  {nombre_fr(y)}", xy=(x_fin, y_etiquette), xytext=(10, 0), textcoords="offset points",
                    va="center", fontsize=9, color=ENCRE_2, annotation_clip=False)

    ax.axhline(100, color=AXE, lw=1, zorder=1)
    ax.grid(axis="y", color=GRILLE, lw=0.6)
    ax.grid(axis="x", visible=False)
    for cote in ("top", "right", "left"):
        ax.spines[cote].set_visible(False)
    ax.spines["bottom"].set_color(AXE)
    ax.tick_params(colors=DISCRET, labelsize=9, length=0)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=9))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(date_fr))
    ax.set_ylabel("Valeur de 100 € investis", color=DISCRET, fontsize=9)
    fig.text(0.06, 0.95, titre, fontsize=13, color=ENCRE, weight="bold", ha="left")
    fig.text(0.06, 0.905, sous_titre, fontsize=9, color=ENCRE_2, ha="left")
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.02), ncol=len(courbes), frameon=False, fontsize=9,
              labelcolor=ENCRE_2, handlelength=1.6)
    fig.subplots_adjust(left=0.06, right=0.76, top=0.84, bottom=0.08)
    fig.savefig(chemin, facecolor=FOND, bbox_inches="tight")
    plt.close(fig)
    print(f"[Graphiques] Graphique exporté avec succès : {chemin}")


def tracer_diagnostics(modes, output_dir):
    """Allocation sectorielle et drawdowns des modes exécutés."""
    from pathlib import Path
    import pandas as pd

    output_dir = Path(output_dir)
    graph_dir = output_dir / 'graphiques'
    graph_dir.mkdir(parents=True, exist_ok=True)
    allocations = {}
    for mode, label in modes:
        allocations[label] = pd.read_csv(output_dir / mode / 'allocation_sectorielle.csv', index_col=0)['poids']
    frame = pd.DataFrame(allocations).fillna(0).T * 100
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax.set_facecolor(FOND)
    frame.plot.barh(stacked=True, ax=ax, color=['#2a78d6', '#1baf7a', '#eda100', '#eb6834'][:len(frame.columns)])
    ax.set(xlabel='Poids à la constitution (%)', ylabel='', title='Allocation sectorielle des modes')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(graph_dir / 'allocation_sectorielle.png', facecolor=FOND, bbox_inches='tight')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    fig.patch.set_facecolor(FOND)
    ax.set_facecolor(FOND)
    for mode, label in modes:
        perf = pd.read_csv(output_dir / mode / 'performances_hors_echantillon.csv', index_col=0, parse_dates=True)
        values = perf['fonds']
        ax.plot(values.index, values / values.cummax() - 1, label=label, color=COULEURS[mode])
    values = perf['msci_world']
    ax.plot(values.index, values / values.cummax() - 1, label='MSCI World', color=COULEURS['msci_world'])
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1))
    ax.set_title('Pertes depuis le dernier sommet : depuis fin 2024')
    ax.grid(axis='y', color=GRILLE)
    ax.legend(frameon=False, ncol=2, loc='lower left')
    fig.tight_layout()
    fig.savefig(graph_dir / 'drawdowns_hors_echantillon.png', facecolor=FOND, bbox_inches='tight')
    plt.close(fig)
