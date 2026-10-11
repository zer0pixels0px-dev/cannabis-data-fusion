# Score commercial

Pour un producteur intérieur commercial (type C3 Farm), chaque cultivar reçoit un score composite sur 100.

## Formule

```
commercial_score = (yield_score      × 0.35)
                 + (terpene_score    × 0.20)
                 + (vigor_score      × 0.15)
                 + (pm_score         × 0.10)
                 + (bag_appeal       × 0.10)
                 + (market_score     × 0.10)
```

Chaque sous-score est normalisé sur 100.

## Dérivation des sous-scores (heuristiques documentées)

| Sous-score | Source brute | Règle |
|------------|--------------|-------|
| `yield_score` | `cultivation_data.yield_g_m2` (GrowDiaries, Leafly grow info) | Normalisé sur le max observé du dataset (g/m² → 0-100) |
| `terpene_score` | `terpenes.total_terpenes` (SQDC, déclaratif) | % terpènes totaux → 0-100 (plafond 4 %) |
| `vigor_score` | `cultivation_data.vigor_score` 1-10 | ×10 ; défaut NULL si inconnu |
| `pm_score` | `cultivation_data.pm_resistance` 1-10 | ×10 ; résistance oïdium |
| `bag_appeal` | `market_data.retail_popularity` + notes Leafly | Heuristique : note moyenne ×20, ajustée du nombre d’avis |
| `market_score` | `market_data` (mentions sociales, volume de recherche, popularité wholesale) | Normalisé sur le max observé |

## Règles d’honnêteté

1. **Aucun champ inventé** : si la donnée brute manque, le sous-score est NULL et le `commercial_score` est marqué `partiel` (recalculé au prorata des sous-scores disponibles, avec mention explicite).
2. **Bag appeal / vigueur / résistances** : ce sont des *proxies* calculés, pas des mesures labo — toujours affichés avec leur méthode.
3. **THC/terpènes** : valeur SQDC prioritaire quand disponible, sinon déclaratif seedbank/Leafly avec badge de source.
4. Le score est **comparatif intra-base** (normalisé sur le dataset), pas une note absolue universelle.
