# cannabis-data-fusion
### Le « Bloomberg du cannabis » — base de données cultivars multi-sources, orientée production commerciale

Projet porté par Alain (technicien en culture, Québec) : compiler les meilleures sources ouvertes et semi-ouvertes de données cannabis en **une seule base structurée** — pedigree vérifié, données labo, rendements réels, profils terpéniques et **scores commerciaux** par cultivar.

## Architecture

8 tables relationnelles — voir [docs/schema.md](docs/schema.md) :

```
breeders ──→ cultivars ──→ pedigree (mother / father)
                  ├──→ lab_results ──→ terpenes
                  ├──→ cultivation_data
                  ├──→ hash_data
                  └──→ market_data
```

## Sources

| # | Source | Rôle | Statut |
|---|--------|------|--------|
| 1 | SeedFinder | Pedigree (~20 000 cultivars), floraison, arômes | ✅ phase 1 OK · crawl complet en cours |
| 2 | Leafly | Popularité, effets, terpènes, grow info (8 762) | ✅ rattaché en fusion v1 |
| 3 | GrowDiaries | Rendements réels observés (8 111 souches) | ✅ phase 1 OK (26/31) · full bloqué Cloudflare |
| 4 | Breeders officiels + Neptune Seed Bank | Lignées père/mère officielles, drops 2024-2026 | ✅ phase 1 OK · Bloom/Neptune bloqués |
| 5 | kannapedia.net | ADN / génomique (Medicinal Genomics) | ✅ phase 1 OK (4/31) |
| — | Dataset ouvert 8 910 souches (CSV, 39 colonnes) | Base de départ : breeder, THC/CBD, rendements, lignée | ✅ intégré en fusion v1 |
| — | COA labs | Aucune base publique par cultivar (COA par lot) | ❌ écarté |
| — | Phylos Galaxy | Mort (devenu vitrine commerciale) | ❌ écarté |
| — | Wikileaf | Mort (domaine = Fire & Flower) | ❌ écarté |
| — | ICMag | Forum non structuré + anti-bot | ❌ écarté |
| — | cannapedia.net / cannapedia.ai | Domaine mort / contenu IA non fiable | ❌ écarté |

Détail complet : [docs/sources.md](docs/sources.md) — audit d’accessibilité du 2026-10-11.

## Base compilée

[`data/compiled/cultivars_prioritaires.json`](data/compiled/cultivars_prioritaires.json) — **fusion v1** : 31 cultivars prioritaires, 3,9 badges moyens par fiche (SeedFinder, Leafly, GrowDiaries, breeder, kannapedia, dataset-8910). Conflits de pedigree listés sans être tranchés (Pink Runtz, Gary Payton, GMO, Runtz, Zoap, Cereal Milk). Commercial_score calculé — **tous partiels** pour l’instant (terpènes/vigueur/PM sans données réelles) : top Ice Cream Cake 93,9 · Gary Payton 84,4 · Runtz 82,6.

Données brutes par source : [`data/raw/`](data/raw/) (seedfinder, growdiaries, breeders, kannapedia).

## Score commercial

```
commercial_score = rendement×0.35 + terpènes×0.20 + vigueur×0.15
                 + résistance_PM×0.10 + bag_appeal×0.10 + marché×0.10
```

Méthode de calcul : [docs/commercial-score.md](docs/commercial-score.md)

## Structure du dépôt

```
docs/            schéma, audit des sources, formule du score commercial
scripts/         scrapers polis + scripts de fusion
data/raw/        datasets bruts, un dossier par source (badge par source)
data/compiled/   base fusionnée — une fiche = un cultivar
targets/         31 cultivars prioritaires (marché nord-américain 2026)
```

## Statut

- [x] Audit d’accessibilité des 10 sources (2026-10-11)
- [x] Dataset ouvert 8 910 souches téléchargé et profilé
- [x] Scaffold du dépôt
- [x] SeedFinder phase 1 (31 cultivars, pedigree) — [data/raw/seedfinder/targets.json](data/raw/seedfinder/targets.json)
- [ ] SeedFinder phase 2 — crawl des 41 858 pages **en cours** (~35 h, chien de garde actif)
- [x] GrowDiaries phase 1 (26/31 : rendements, THC, notes) — [data/raw/growdiaries/targets_yield.json](data/raw/growdiaries/targets_yield.json)
- [ ] GrowDiaries full (8 111) — bloqué Cloudflare 403, fetcher navigateur requis
- [x] Breeders phase 1 + kannapedia (lignées officielles, 4 fiches ADN) — [data/raw/breeders/](data/raw/breeders/) · [data/raw/kannapedia/](data/raw/kannapedia/)
- [ ] Bloom Seed Co / Neptune — bloqués (403 nginx), fetcher navigateur requis
- [x] **Fusion v1** — [data/compiled/cultivars_prioritaires.json](data/compiled/cultivars_prioritaires.json)
