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
| 1 | SeedFinder | Pedigree (~20 000 cultivars), floraison, arômes | ✅ priorité #1 |
| 2 | Leafly | Popularité, effets, terpènes, grow info (8 762) | ✅ |
| 3 | GrowDiaries | Rendements réels observés (8 111 souches) | ✅ |
| 4 | Breeders officiels + Neptune Seed Bank | Lignées père/mère officielles, drops 2024-2026 | ✅ |
| 5 | kannapedia.net | ADN / génomique (2 411 souches, Medicinal Genomics) | ✅ complément |
| — | Dataset ouvert 8 910 souches (CSV, 39 colonnes) | Base de départ : breeder, THC/CBD, rendements, lignée | ✅ |
| — | COA labs | Aucune base publique par cultivar (COA par lot) | ❌ écarté |
| — | Phylos Galaxy | Mort (devenu vitrine commerciale) | ❌ écarté |
| — | Wikileaf | Mort (domaine = Fire & Flower) | ❌ écarté |
| — | ICMag | Forum non structuré + anti-bot | ❌ écarté |
| — | cannapedia.net / cannapedia.ai | Domaine mort / contenu IA non fiable | ❌ écarté |

Détail complet : [docs/sources.md](docs/sources.md) — audit d’accessibilité du 2026-10-11.

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
- [ ] Scraping SeedFinder (pedigree)
- [ ] Re-scraping GrowDiaries (8 111 souches)
- [ ] Scraping breeders / Neptune
- [ ] kannapedia.net (ADN)
- [ ] Fusion → base compilée + scores commerciaux
