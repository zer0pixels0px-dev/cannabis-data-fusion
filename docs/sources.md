# Sources — analyse comparative & audit d’accessibilité (2026-10-11)

Critères : fiabilité génétique · fiabilité agronomique · qualité quantitative · facilité d’automatisation.

## Tableau de fiabilité

| Source | Fiabilité | Forces | Faiblesses | Note /10 |
|--------|-----------|--------|------------|----------|
| SeedFinder | Très élevée | Pedigrees, breeder tracking (~20 000 cultivars) | Peu de données labo (déclaratif) | 9.5 |
| Breeders officiels | Très élevée | Source primaire : lignée père/mère, drops 2024-2026 | Biais marketing, jamais de THC % | 9 |
| GrowDiaries | Élevée | Données de culture réelles (8 111 souches) | Variabilité des producteurs | 8.5 |
| Leafly | Bonne | Popularité commerciale, effets, terpènes, grow info | Données parfois marketing | 8 |
| kannapedia.net (ADN) | Élevée (génomique) | ADN réel, gènes terpènes/cannabinoïdes (2 411 souches) | Couverture limitée, pas de valeurs labo | 8 |
| Dataset ouvert 8 910 (CSV) | Bonne | 39 colonnes : breeder, THC/CBD, rendements, lignée | Source = un seedbank (biais catalogue) | 7.5 |
| Cannapedia (historique) | — | — | cannapedia.net MORT (DNS) ; cannapedia.ai = contenu IA non fiable | écarté |
| Wikileaf | — | — | MORT (domaine = Fire & Flower) | écarté |
| ICMag | Variable | Infos uniques sur lignées anciennes | Forum non structuré, robots.txt 403 | écarté (usage manuel ponctuel) |
| Phylos Galaxy | — | — | MORT (devenu seed company) ; archives : EBI-EVA, BigQuery | écarté |
| COA Labs (SC, ACS, Kaycha, Infinite…) | Très élevée (par lot) | THCA, terpènes, contaminants — par lot | Aucune base publique par cultivar ; clauses anti-reproduction | écarté en masse |

## Stratégie en 3 niveaux

**Niveau 1 — Vérité génétique** : SeedFinder + breeders officiels (+ kannapedia pour l’ADN)
→ `cultivars` + `pedigree` : cultivar, breeder, mother, father, backcross, générations, année de sortie.

**Niveau 2 — Données de laboratoire** : SQDC (tests obligatoires, étiquetage — source validée) + déclaratif Leafly/seedbanks
→ `lab_results` + `terpenes` : THCA, THC total, CBD, CBGA, humidité, activité de l’eau, terpènes totaux + myrcène/limonène/caryophyllène/linalool/ocimène/humulène/pinène.

**Niveau 3 — Production commerciale** : GrowDiaries + grow info Leafly + fiches breeders
→ `cultivation_data` + `hash_data` + `market_data` : stretch, floraison, g/m², résistance moisissure/PM, vigueur, wash %, bag appeal (dérivé), scores.

## Notes d’audit

- **SeedFinder** : robots.txt permissif, sitemap actif (9 fichiers), aucune interdiction de scraping trouvée ; API JSON officielle arrêtée le 2024-07-01 → scraping HTML poli (1 req / 2–3 s).
- **Leafly** : `/strains` autorisé par robots.txt ; méthode `__NEXT_DATA__` confirmée le 2026-10-11 ; user-agent neutre (GPTBot banni).
- **GrowDiaries** : 8 111 souches (les 82 records du 2026-10-10 étaient un périmètre partiel) ; passer par le HTML, pas l’API (`/api` disallow).
- **Breeders** : 5/9 scrapables (Compound, Clearwater 175 souches, Exotic Genetix, Solfire, Bloom 145 produits) ; fallback Neptune Seed Bank 8/9 ; aucun breeder n’affiche de THC %.
- **Green Scientific Labs** semble absorbé par Kaycha — ne pas traiter comme source indépendante.
- **Datasets ouverts** : `JonusNattapong/Cannabis-Strains` (GitHub, CSV 8 910 × 39) ; API Otreeba et The Strain API à tester.
