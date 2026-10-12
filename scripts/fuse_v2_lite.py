#!/usr/bin/env python3
"""FUSION v2-lite — cannabis-data-fusion : union elargie multi-sources.
Entrees : CSV 8910, Leafly 8762, SeedFinder 31, GrowDiaries 31, breeders 31,
          kannapedia 4, fusion v1 (31 fiches), sf_images.json (bonus, optionnel).
Sorties : fusion_elargie.json, fusion_elargie_report.md
Regles : jamais inventer (null), chaque valeur porte sa source,
         conflits exposes jamais tranches.
"""
import csv, json, math, os, re, statistics, unicodedata
from collections import Counter, defaultdict

BASE = os.path.expanduser('~/workspace/research_notes')
OUT = os.path.join(BASE, 'compiled-20261011')
os.makedirs(OUT, exist_ok=True)

# ---------------- normalisation ----------------
ALIASES = {
    'honey bananas': 'honey banana',
    'the don mega': 'don mega',
    'rs 11': 'rs-11', 'rs11': 'rs-11',
    'gmo cookies': 'gmo',
    'gsc': 'girl scout cookies',
    'thin mint gsc': 'girl scout cookies',
    'girl scout cookie': 'girl scout cookies',
}
def norm(name):
    if not name:
        return ''
    n = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode()
    n = n.lower().strip()
    n = re.sub(r"['`\"]", '', n)
    key = re.sub(r'[^a-z0-9 ]', ' ', n)
    key = re.sub(r'\s+', ' ', key).strip()
    return ALIASES.get(key, key)

def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def parse_pct(s):
    if s is None: return None
    m = re.search(r'\d+(?:\.\d+)?', str(s).replace(',', '.'))
    return float(m.group()) if m else None

def parse_range_mean(s, ndigits=2):
    """Moyenne d'une plage ('0.03-16 %' -> 8.02) ou valeur simple."""
    if s is None: return None
    nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', str(s).replace(',', '.'))]
    return round(sum(nums)/len(nums), ndigits) if nums else None

def parse_gm2(s):
    if not s: return None
    nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', str(s).replace(',', '.')) if float(x) > 0]
    return sum(nums)/len(nums) if nums else None

def parse_days_range(s):
    """'64 days'->64 ; '8-9 Weeks (55-63 Days)'->59 ; '12-14 weeks'->91."""
    if s is None: return None
    if isinstance(s, (int, float)): return int(s)
    t = str(s)
    par = re.findall(r'\(([^)]*)\)', t)
    for p in par:
        nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', p.replace(',', '.'))]
        if nums:
            return round(sum(nums)/len(nums))
    nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', t.replace(',', '.'))]
    if not nums: return None
    avg = sum(nums)/len(nums)
    if re.search(r'week', t, re.I): avg *= 7
    return round(avg)

# ---------------- entrees ----------------
sf = load_json(f'{BASE}/seedfinder-20261011/targets.json')
gd_raw = load_json(f'{BASE}/growdiaries-20261011/targets_yield.json')
br = load_json(f'{BASE}/breeders-20261011/breeders_targets.json')
kn = load_json(f'{BASE}/breeders-20261011/kannapedia_targets.json')
lf = load_json(f'{BASE}/leafly-index-20261010/leafly_merged.json')
v1 = load_json(f'{BASE}/compiled-20261011/cultivars_prioritaires.json')
sf_images = {}
if os.path.exists(f'{BASE}/seedfinder-20261011/sf_images.json'):
    _raw = load_json(f'{BASE}/seedfinder-20261011/sf_images.json')
    sf_images = {norm(k): v for k, v in _raw.items()}

gd = gd_raw.get('cultivars', gd_raw) if isinstance(gd_raw, dict) else gd_raw
gd_idx, br_idx, kn_idx, v1_idx = {}, {}, {}, {}
for r in gd: gd_idx[norm(r.get('cultivar',''))] = r
for r in br: br_idx[norm(r.get('cultivar',''))] = r
for r in kn: kn_idx[norm(r.get('cultivar',''))] = r
for r in v1: v1_idx[norm(r.get('cultivar',''))] = r

lf_idx = defaultdict(list)
for r in lf: lf_idx[norm(r.get('name',''))].append(r)

csv_rows = []
with open(f'{BASE}/datasets-20261011/cannabis-strains-8910.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        csv_rows.append(row)
csv_idx = defaultdict(list)
for row in csv_rows: csv_idx[norm(row.get('strain_name',''))].append(row)

# fillers genetic_background (seuil v1 : >= 30 occurrences)
_bg_count = Counter((r.get('genetic_background') or '').strip() for r in csv_rows if (r.get('genetic_background') or '').strip())
FILLER_BG = {bg for bg, n in _bg_count.items() if n >= 30}

def pick_leafly(recs):
    return max(recs, key=lambda r: (r.get('reviews') or 0, r.get('rating') or 0)) if recs else None

def split_lineage(bg):
    """'A x B' -> (A, B) si un seul separateur ; sinon (None, None)."""
    if not bg: return None, None
    parts = re.split(r'\s+[xX×]\s+', bg.strip())
    if len(parts) == 2 and all(p.strip() for p in parts):
        return parts[0].strip(), parts[1].strip()
    return None, None

def parse_leafly_lineage(desc):
    """Parse conservateur : 'cross of X and Y' / 'cross between X and Y'."""
    if not desc: return None, None
    m = re.search(r'\bcross\s+(?:of|between)\s+([A-Z][\w .\'#\-]{1,40}?)\s+and\s+([A-Z][\w .\'#\-]{1,40}?)[.,]', desc)
    if m:
        a, b = m.group(1).strip(), m.group(2).strip()
        if 1 <= len(a.split()) <= 4 and 1 <= len(b.split()) <= 4:
            return a, b
    return None, None

PRIO31 = {norm(s['name']) for s in sf}

# ---------------- univers ----------------
keys = set()
for idx in (csv_idx, lf_idx):
    keys.update(idx.keys())
for idx in (gd_idx, br_idx, kn_idx, v1_idx):
    keys.update(idx.keys())
for s in sf:
    keys.add(norm(s['name']))
keys.discard('')

# ---------------- fusion ----------------
fused, stats = [], defaultdict(int)
n_doublons = 0
for key in sorted(keys):
    s = next((x for x in sf if norm(x['name']) == key), None)
    g = (gd_idx.get(key) or {}).get('growdiaries', {})
    b = br_idx.get(key, {})
    k = kn_idx.get(key)
    l = pick_leafly(lf_idx.get(key, []))
    cands = csv_idx.get(key, [])
    old = v1_idx.get(key)

    n_src = sum([bool(s), bool(g and g.get('status')=='found'), bool(b and b.get('breeder_status')),
                 bool(k), bool(l), bool(cands)])
    if n_src > 1: n_doublons += 1

    # nom d'affichage : SF > GD > Leafly > CSV
    display = (s or {}).get('name') or (gd_idx.get(key) or {}).get('cultivar') \
        or (l or {}).get('name') or (cands[0].get('strain_name') if cands else key)
    aliases = sorted({n for n in [
        (s or {}).get('name'), (gd_idx.get(key) or {}).get('cultivar'),
        (l or {}).get('name')] if n and n != display})

    badges, urls = [], {}
    if s: badges.append('seedfinder'); urls['seedfinder'] = s.get('source_url')
    if g and g.get('status') == 'found': badges.append('growdiaries'); urls['growdiaries'] = g.get('url')
    if b and b.get('breeder_status') == 'vendu_par_breeder': badges.append('breeder-direct'); urls['breeder-direct'] = b.get('source_url')
    if k: badges.append('kannapedia'); urls['kannapedia'] = k.get('source_url')
    if l: badges.append('leafly'); urls['leafly'] = f"https://www.leafly.com/strains/{l.get('slug')}"
    if cands: badges.append('dataset-8910')
    for bd in badges: stats[f'badge_{bd}'] += 1

    # --- breeder_origine : breeder-direct (verifie) > dataset-8910 (seedbank) > null ---
    if b and b.get('breeder_status') == 'vendu_par_breeder' and b.get('breeder'):
        breeder_origine = {'value': b['breeder'], 'source': 'breeder-direct', 'qualite': 'verifie'}
    elif cands:
        bc = Counter((r.get('breeder') or '').strip() for r in cands if (r.get('breeder') or '').strip())
        if bc:
            breeder_origine = {'value': bc.most_common(1)[0][0], 'source': 'dataset-8910', 'qualite': 'seedbank'}
        else:
            breeder_origine = {'value': None, 'source': None, 'qualite': None}
    else:
        breeder_origine = {'value': None, 'source': None, 'qualite': None}

    fiche_source = s.get('breeder') if s else None  # attribution fiche SeedFinder, pas un fait

    # --- parents : SF > breeder-direct > Leafly desc > dataset (non-filler) ---
    mere = pere = None
    p_sources = []
    if s and s.get('parent_1') and s.get('parent_2'):
        mere, pere, p_sources = s['parent_1'], s['parent_2'], ['seedfinder']
    elif b and b.get('mother') and b.get('father'):
        mere, pere, p_sources = b['mother'], b['father'], ['breeder-direct']
    if not mere and l and l.get('desc'):
        a, bb = parse_leafly_lineage(l['desc'])
        if a:
            mere, pere, p_sources = a, bb, ['leafly-desc']
            stats['parents_via_leafly_desc'] += 1
    bg_used = None
    if not mere and cands:
        for r in sorted(cands, key=lambda r: len(r.get('genetic_background') or ''), reverse=True):
            bg = (r.get('genetic_background') or '').strip()
            if bg and bg not in FILLER_BG:
                a, bb = split_lineage(bg)
                if a:
                    mere, pere, p_sources, bg_used = a, bb, ['dataset-8910'], bg
                    break
    lineage_raw = (s or {}).get('lineage_raw') or bg_used

    # --- floraison ---
    floraison = (s or {}).get('flowering_days')
    if floraison is None and cands:
        vals = [parse_days_range(r.get('flowering_time')) for r in cands]
        vals = [v for v in vals if v]
        floraison = round(statistics.median(vals)) if vals else None

    # --- THC : growdiaries > leafly > dataset ---
    thc, thc_src = None, None
    if g.get('thc_pct') is not None: thc, thc_src = g['thc_pct'], 'growdiaries'
    elif l and l.get('thc'): thc, thc_src = l['thc'], 'leafly'
    elif cands:
        vals = [parse_range_mean(r.get('thc')) for r in cands]
        vals = [v for v in vals if v is not None]
        if vals: thc, thc_src = round(statistics.median(vals), 2), 'dataset-8910'

    phenotype = (l or {}).get('phenotype') or (s or {}).get('type')

    # --- image : seedfinder(scrape) > dataset > leafly ---
    image_url, image_src = None, None
    if key in sf_images: image_url, image_src = sf_images[key], 'seedfinder'
    elif cands and (cands[0].get('image_url') or '').strip():
        image_url, image_src = cands[0]['image_url'].strip(), 'dataset-8910'
    elif l and l.get('img'): image_url, image_src = l['img'], 'leafly'

    # --- production ---
    r_gplant = g.get('yield_g_plant_median')
    gm2_vals = [parse_gm2(r.get('yield_indoor')) for r in cands]
    gm2_vals = [v for v in gm2_vals if v]
    production = {
        'rendement_median_g_plant': r_gplant,
        'rendement_seedbank_g_m2': round(statistics.median(gm2_vals), 1) if gm2_vals else None,
        'recoltes_growdiaries': g.get('harvests'),
        'avis_leafly': l.get('reviews') if l else None,
        'note_leafly': l.get('rating') if l else None,
    }

    # --- populaire ---
    raisons = []
    if cands and any((r.get('most_popular_seeds') or '').strip() == 'Most Popular Cannabis Seeds' for r in cands):
        raisons.append('most_popular_seeds (Seed City)')
    if key in PRIO31: raisons.append('cultivar prioritaire (top 31)')
    if l and (l.get('reviews') or 0) >= 500: raisons.append(f"Leafly : {l['reviews']} avis")
    if (g.get('harvests') or 0) >= 50: raisons.append(f"GrowDiaries : {g['harvests']} récoltes")
    populaire = {'vrai': bool(raisons), 'raisons': raisons}

    # --- v1 : conflits, score, flags ---
    conflits = (old or {}).get('lineage_conflits', [])
    cscore = (old or {}).get('commercial_score')
    spartiel = (old or {}).get('score_partiel')
    flags = list((old or {}).get('flags_qualite', []))
    if cands and len(cands) > 1:
        flags.append(f'{len(cands)} lignes dataset-8910 fusionnées (médiane/mode)')
    if bg_used is None and cands and all(((r.get('genetic_background') or '').strip() in FILLER_BG or not (r.get('genetic_background') or '').strip()) for r in cands):
        flags.append('dataset-8910 : genetic_background filler ou absent — lignée non reprise')
    if 'leafly-desc' in p_sources:
        flags.append('lignée parsée depuis le descriptif Leafly — à vérifier')

    desc = (l.get('desc') or '')[:300] if l else None

    rec = {
        'name': display,
        'aliases': aliases,
        'breeder_origine': breeder_origine,
        'fiche_source': fiche_source,
        'parents': {'mere': mere, 'pere': pere, 'sources': p_sources},
        'lineage_raw': lineage_raw,
        'conflits_lignee': conflits,
        'floraison_jours': floraison,
        'thc_pct': thc, 'thc_src': thc_src,
        'phenotype': phenotype,
        'image_url': image_url, 'image_src': image_src,
        'production': production,
        'populaire': populaire,
        'badges': badges,
        'source_urls': urls,
        'flags_qualite': flags,
        'commercial_score': cscore,
        'score_partiel': spartiel,
        'heterozygosity_pct': k.get('heterozygosity_pct') if k else None,
        'dna_report_type': k.get('report_type') if k else None,
        'desc': desc,
    }
    # encodage sparse : on retire les null / [] / {} a tous les niveaux
    # (absence de cle = null ; schema documente dans le rapport)
    for sub in ('production', 'breeder_origine', 'parents'):
        for kk in [kk for kk, vv in rec[sub].items() if vv is None or vv == []]:
            del rec[sub][kk]
    for kk in [kk for kk, vv in rec.items() if vv is None or vv == [] or vv == {}]:
        if kk not in ('production', 'breeder_origine', 'parents', 'populaire', 'badges', 'name'):
            del rec[kk]
    fused.append(rec)

with open(f'{OUT}/fusion_elargie.json', 'w', encoding='utf-8') as f:
    json.dump(fused, f, ensure_ascii=False, separators=(',', ':'))
print('cultivars uniques:', len(fused), '| cles multi-sources:', n_doublons)
print('badges:', dict(stats))
