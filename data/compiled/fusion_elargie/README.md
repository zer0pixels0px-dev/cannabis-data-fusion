# fusion_elargie — shards

Fusion élargie v2-lite : 15 287 cultivars uniques multi-sources (7,6 Mo au total),
découpée en morceaux de ~95 Ko pour le push via l'API GitHub.

## Réassembler

```bash
cat shard_*.json | python3 -c "
import json, glob
d = []
for f in sorted(glob.glob('shard_*.json')):
    d.extend(json.load(open(f)))
json.dump(d, open('fusion_elargie.json', 'w'), ensure_ascii=False)
print(len(d), 'cultivars')
"
```

## Contenu
{
 "fichier": "fusion_elargie (shardée)",
 "shards": 16,
 "fichiers": [
  "data/compiled/fusion_elargie/shard_00.json",
  "data/compiled/fusion_elargie/shard_01.json",
  "data/compiled/fusion_elargie/shard_02.json",
  "data/compiled/fusion_elargie/shard_03.json",
  "data/compiled/fusion_elargie/shard_04.json",
  "data/compiled/fusion_elargie/shard_05.json",
  "data/compiled/fusion_elargie/shard_06.json",
  "data/compiled/fusion_elargie/shard_07.json",
  "data/compiled/fusion_elargie/shard_08.json",
  "data/compiled/fusion_elargie/shard_09.json",
  "data/compiled/fusion_elargie/shard_10.json",
  "data/compiled/fusion_elargie/shard_11.json",
  "data/compiled/fusion_elargie/shard_12.json",
  "data/compiled/fusion_elargie/shard_13.json",
  "data/compiled/fusion_elargie/shard_14.json",
  "data/compiled/fusion_elargie/shard_15.json"
 ],
 "total_cultivars": 15287,
 "note": "Fusion élargie v2-lite découpée pour le push API. Recoller: cat shard_*.json | python3 -c \"import json,sys,glob; d=[]; [d.extend(json.load(open(f))) for f in sorted(glob.glob(\"shard_*.json\"))]; json.dump(d, open(\"fusion_elargie.json\",\"w\"))\""
}
