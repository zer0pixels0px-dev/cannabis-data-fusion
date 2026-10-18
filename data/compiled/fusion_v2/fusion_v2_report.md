# Fusion v2 — rapport de compilation

**Date :** 2026-10-17 · **Source :** crawl SeedFinder phase 2 (41 858 pages JSON, `~/workspace/research_notes/seedfinder-20261011/pages/`)
**Base :** `fusion_elargie.json` v1 (15 287 entrées) — **archive intouchée**, la v2 enrichit sans remplacer.
**Sorties :** `fusion_v2.json` (87,7 Mo), `fusion_v2.py` (script rejouable), `fusion_v2_stats.json`.

## Méthode

1. **Normalisation** : fonction `norm()` + `ALIASES` copiés de `fuse_v2_lite.py` (pas d'import : l'import exécuterait tout le pipeline v1 et réécrirait l'archive).
2. **Regroupement** : les 41 858 pages sont groupées par nom normalisé → **36 885 groupes** (12 pages sans nom ignorées). Un groupe = un cultivar, une à N fiches breeders.
3. **Matching** : chaque groupe est matché contre l'index v1 (nom normalisé + alias).
   - **Match (8 067)** : la fiche v1 est enrichie — badge `seedfinder` ajouté, `source_urls.seedfinder`, `fiche_source` / `phenotype` / `floraison_jours` / `parents` / `lineage_raw` complétés **uniquement si absents**. Jamais d'écrasement.
   - **Nouveau (28 818)** : fiche créée au schéma v1 (badges `['seedfinder']`, `populaire: false`, `breeder_origine` non vérifié → null).
   - **7 220** entrées v1 sans page SeedFinder : recopiées intactes.
4. **Bloc `donnees_seedfinder`** : chaque fiche matchée ou nouvelle porte un sous-objet namespacé avec l'intégralité des données SeedFinder (breeders, URLs, type normalisé, culture, type de graine, floraison, parents, lignage brut, arbre généalogique, liens parents, effets, arômes, goût, récompenses, description breeder tronquée à 600 car.). Aucune ambiguïté sur la provenance.
5. **Phénotype** : `type` SeedFinder normalisé (`indica / sativa` → `Hybrid`, `mostly indica` → `Indica-dominant`, `ruderalis / …` → `… (auto)`, `unknown` → null, préfixe `discontinued` → flag).

### Règle anti-bruit sur les lignées (correctif appliqué après audit)

Les fiches breeders décrivent souvent des **versions dérivées** (autofécondations `X x X`, croisements `X x Y`), pas la lignée du cultivar. Remplir les parents plats avec ces paires serait faux (ex. `Blue Dream` ← `Blue Dream x Blue Dream`).
Règle : une paire n'est *informative* que si les deux parents diffèrent et qu'aucun n'est le cultivar lui-même ou une de ses versions. Sinon :
- pas de remplissage plat ;
- flag `seedfinder : fiches = autofécondations/croisements dérivés — aucune lignée informative` (1 318 cas) ;
- désaccords entre versions documentés en `conflits_lignee`, jamais tranchés.

## Couverture

| Indicateur | Valeur |
|---|---|
| Pages crawlées | 41 858 (12 sans nom ignorées, 0 invalide) |
| Groupes SeedFinder | 36 885 |
| Entrées v1 | 15 287 |
| Groupes matchés (enrichis) | **8 067** (52,8 % de v1) |
| Nouveaux cultivars | **28 818** |
| Entrées v1 sans SeedFinder (intactes) | 7 220 |
| **Total fusion v2** | **44 105** |

### Champs complétés sur fiches existantes (SeedFinder comme nouvelle source)

| Champ | Fiches complétées |
|---|---|
| `source_urls.seedfinder` | 8 036 |
| `fiche_source` (attribution fiche) | 8 036 |
| `lineage_raw` | 7 901 |
| `parents` (consensus informatif uniquement) | 5 145 |
| `floraison_jours` | 4 722 |
| `phenotype` | 3 657 |
| Bloc `donnees_seedfinder` | 8 067 |

### Données sensorielles et descriptives (tous cultivars v2)

- Fiches avec **effets** : 1 275 (top : Calming, Relaxing, Activating, Uplifting)
- Fiches avec **arômes** : 689 (top : Lemon, Earth, Hashish, Pine)
- Fiches avec **description breeder** : 36 786
- Fiches multi-breeders fusionnées : 1 564 (flag explicite)

## Conflits détectés (exposés, jamais tranchés)

| Type | Cas |
|---|---|
| `parents (seedfinder vs existant)` — la fiche SeedFinder contredit la lignée existante | 226 |
| `parents (versions seedfinder)` — les breeders divergent entre eux (fiches existantes) | 730 |
| `parents (versions seedfinder)` — sur nouveaux cultivars | 523 |
| Divergences `floraison_jours` (> 7 j d'écart, en `flags_qualite`) | 417 |
| Fiches avec `conflits_lignee` au total | 1 481 |

Exemples vérifiés : `Blue Dream` (31 fiches breeders, 4 versions de lignée documentées, parents plats laissés vides honnêtement), `GMO` (conflit pré-existant conservé + nouveau conflit seedfinder vs existant), `AutoDaiquiri Lime` (remplissage propre, consensus).

## Limites

- **Données SeedFinder = contributions communautaires et fiches commerciales**, pas d'essais contrôlés ni de labo. Les effets/arômes/goûts sont déclaratifs.
- **Couverture sensorielle faible** : 3,5 % des groupes ont des effets, 1,9 % des arômes. L'absence de données = null, jamais inventé.
- **Bruit dans les fiches breeders** : une même fiche peut décrire un dérivé (S1, croisement) plutôt que le cultivar d'origine ; la règle anti-bruit limite le risque mais le bloc `donnees_seedfinder` reste à interpréter avec prudence (breeders et URLs fournis pour vérification).
- **Descriptions breeders tronquées** à 600 caractères (taille du fichier) ; texte intégral dans les pages sources.
- **12 pages sans nom** ignorées (comptées, non inventées).
- **2 anomalies pré-existantes v1** conservées telles quelles (`Alien Mints`, `Super Boof` : `mere == pere` hérité du scrape v1) — la v2 n'écrase pas, elle documente.
- `basic_infos_raw` (menu de navigation du site) non repris : sans valeur informative.
- Les récompenses (`awards`) ne sont conservées que si elles mentionnent explicitement un gain/une coupe (filtrage anti-marketing).

## Rejouabilité

```bash
cd ~/workspace/research_notes/compiled-20261011/fusion_v2
python3 fusion_v2.py
```

Le script ne lit que `../fusion_elargie.json` et `../../seedfinder-20261011/pages/*.json`, n'écrit que dans `fusion_v2/`. Durée constatée : ~25 s (+ validation).
