# 📊 Dividend Strategy

**Analyseur de stratégie dividende pour les actions françaises (CAC 40)**

Identifie les meilleures actions selon le **ratio rendement / volatilité** : un bon dividende, sans trop de secousses sur le prix.

## Fonctionnalités

- ✅ Analyse du CAC 40 ou de données personnalisées (CSV/JSON)
- ✅ Calcul de 3 métriques principales
- ✅ Scoring et classement automatique
- ✅ Export en CSV / JSON / HTML
- ✅ Interface interactive (menu, aucun argument CLI)
- ✅ Cache local (12 h) pour ne pas re-télécharger à chaque lancement

## Installation

```bash
git clone <repo>
cd dividend_strategy
pip install -r requirements.txt
```

## Utilisation

```bash
python main.py
```

Un menu te demande la source (CAC 40 ou fichier perso), puis affiche le tableau avec un sous-menu : tri, filtre, export.

**Fichier perso** (le prix et le dividende viennent de ton fichier, la volatilité est calculée avec l'historique Yahoo Finance) :

```csv
ticker,current_price,annual_dividend
MC.PA,450.25,12.50
SAF.PA,125.80,4.20
```

ou en JSON : `[{"ticker": "MC.PA", "current_price": 450.25, "annual_dividend": 12.50}]`.
Le séparateur `;` et la virgule décimale (`12,50`) sont acceptés. Prix et dividende doivent être > 0.

## Méthodologie statistique

| Statistique | Formule | Signification |
|---|---|---|
| **Rendement dividende** | (Dividende annuel / Prix actuel) × 100 | % de retour annuel issu des dividendes |
| **Volatilité** | écart-type des rendements journaliers × √252 | Amplitude des variations du prix sur un an ; plus bas = plus stable |
| **Ratio qualité** | Rendement / Volatilité | Dividende obtenu par point de risque ; **plus haut = meilleur** |

**Volatilité**, en détail :

```
r_t       = (P_t − P_{t−1}) / P_{t−1}        rendement du jour
σ_jour    = std(r_t)                          écart-type (ddof = 1)
σ_annuel  = σ_jour × √252                     annualisation (252 jours de bourse)
```

Pourquoi √252 ? Les variances de jours indépendants s'additionnent (Var_an = 252 × Var_jour), donc l'écart-type est multiplié par √252 ≈ 15,87.

**Données :** Yahoo Finance via `yfinance`, historique journalier sur 12 mois. Le prix actuel est le dernier cours de clôture ; le dividende annuel est la somme des dividendes versés sur les 12 derniers mois.

## Scoring

| Ratio Q | Score |
|---|---|
| ≥ 0,15 | ⭐⭐⭐⭐ Excellent |
| 0,10 – 0,15 | ⭐⭐⭐ Bon |
| 0,05 – 0,10 | ⭐⭐ Moyen |
| < 0,05 | ⭐ Faible |

Exemple (valeurs illustratives) : rendement 3,34 % et volatilité 22,1 % → ratio 0,151 → Excellent.

## Structure du projet

```
classes/     → Stock, Portfolio, AnalysisStrategy
fonctions/   → récupération, calcul, affichage/filtrage, export
data/        → exports et cache (ignorés par git)
main.py      → point d'entrée (menu interactif)
```

## Limites connues

- La composition du CAC 40 change : la liste est dans `fonctions/recuperation_donnees.py` (`CAC40_TICKERS`). Un ticker introuvable est ignoré avec un avertissement.
- Dividende sur 12 mois glissants : une année avec 0 ou 2 versements décalés fausse le rendement.
- Rendement avant impôts : la fiscalité française (PFU 30 %, etc.) n'est **pas** modélisée.
- Une volatilité passée ne garantit pas la future. Outil d'analyse, pas un conseil en investissement.

## Licence & contact

- Licence : MIT
- Auteur : Ange
- Repo : https://github.com/malitez/-Dividend-Strategy
