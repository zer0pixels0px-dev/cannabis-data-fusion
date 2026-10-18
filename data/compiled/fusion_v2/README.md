# Fusion v2 — cannabis-data-fusion

Compilation du crawl SeedFinder phase 2 (41 858 pages) fusionnée avec le dataset v1.

- **44 105 entrées** : 8 067 cultivars v1 enrichis (données SeedFinder ajoutées sans écrasement),
  28 818 nouveaux cultivars, 7 220 entrées v1 sans page SeedFinder recopiées intactes.
- **90 shards** (`shard_00.json` … `shard_89.json`) : découpage du dataset complet pour
  contourner les limites de taille de fichier de l'API.
- `fusion_v2_report.md` : méthode, couverture, conflits, limites.
- `fusion_v2.py` : script rejouable (~25 s).
- `fusion_v2_stats.json` : statistiques machine.

## Règles

- Jamais inventé : `null` honnête si absent.
- Chaque valeur porte sa source (`{'value': ..., 'source': 'seedfinder'}`).
- Conflits exposés, jamais tranchés (`conflits_lignee[]`, flags de divergence).
- Données SeedFinder = contributions communautaires / fiches commerciales, pas de labo.

## Assemblage

```python
import json, glob
data = []
for f in sorted(glob.glob('shard_*.json')):
    data += json.load(open(f))
```

Archive v1 : `data/compiled/fusion_elargie/` (intouchée).
