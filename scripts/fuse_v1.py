#!/usr/bin/env python3
"""FUSION v1 — cannabis-data-fusion : une fiche = un cultivar.
Entrees : seedfinder targets, growdiaries targets_yield, breeders_targets,
          kannapedia_targets, dataset CSV 8910, index Leafly __NEXT_DATA__.
Sorties : cultivars_prioritaires.json, base_8910_enrichie.jsonl, fusion_report.md
"""
import csv, json, math, os, re, statistics, unicodedata
from collections import defaultdict

BASE = os.path.expanduser('~/workspace/research_notes')
OUT = os.path.join(BASE, 'compiled-20261011')
os.makedirs(OUT, exist_ok=True)

# ---------------- normalisation ----------------
ALIASES = {
    'honey bananas': 'honey banana',
    'the don mega': 'don mega',
    'rs 11': 'rs-11', 'rs11': 'rs-11',
    'gmo cookies': 'gmo',
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

DISPLAY_OVERRIDE = {'Honey Bananas': 'Honey Banana', 'The Don Mega': 'Don Mega'}

def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

# ---------------- entrees ----------------
sf = load_json(f'{BASE}/seedfinder-20261011/targets.json')                      # 31
gd = load_json(f'{BASE}/growdiaries-20261011/targets_yield.json')                # 31
br = load_json(f'{BASE}/breeders-20261011/breeders_targets.json')               # 31
kn = load_json(f'{BASE}/breeders-20261011/kannapedia_targets.json')             # 4
lf = load_json(f'{BASE}/leafly-index-20261009/strains.json')                    # 8816

gd = gd if isinstance(gd, list) else gd.get('cultivars', gd)
br = br if isinstance(br, list) else br.get('cultivars', br)

gd_idx = {norm(r.get('cultivar', '')): r for r in gd}
br_idx = {norm(r.get('cultivar', '')): r for r in br}
kn_idx = {norm(r.get('cultivar', '')): r for r in kn}

lf_idx = defaultdict(list)
for r in lf:
    lf_idx[norm(r.get('name', ''))].append(r)

csv_rows = []
with open(f'{BASE}/datasets-20261011/cannabis-strains-8910.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        csv_rows.append(row)
csv_idx = defaultdict(list)
for row in csv_rows:
    csv_idx[norm(row.get('strain_name', ''))].append(row)

def pick_leafly(recs):
    if not recs:
        return None
    return max(recs, key=lambda r: (r.get('reviews') or 0, r.get('rating') or 0))

def parse_pct(s):
    if s is None:
        return None
    m = re.search(r'[\d.]+', str(s).replace(',', '.'))
    return float(m.group()) if m else None

def parse_gm2(s):
    if not s:
        return None
    nums = re.findall(r'[\d.]+', str(s).replace(',', '.'))
    nums = [float(x) for x in nums if float(x) > 0]
    if not nums:
        return None
    return sum(nums) / len(nums)

def parse_days(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    m = re.search(r'[\d.]+', str(s))
    return int(float(m.group())) if m else None

def lin_norm(s):
    if not s:
        return ''
    n = norm(s).replace(' x ', ' ').replace('x', ' ')
    return re.sub(r'\s+', ' ', n).strip()

# ---------------- conflits connus (ancres dans les donnees) ----------------
KNOWN_CONFLICTS = {
    'pink runtz': [
        {'valeur': 'Pink Panties × Runtz', 'source': 'SeedFinder / Copycat Genetix'},
        {'valeur': 'Pink Panties × Rainbow Sherbet (version clone-only)',
         'source': 'SeedFinder — note fiche (2e version)'},
    ],
    'gary payton': [
        {'valeur': 'Gary Payton × Girl Scout Cookies (auto-référentielle)',
         'source': 'SeedFinder / Blim Burn Seeds — douteuse'},
    ],
    'gmo': [
        {'valeur': 'Chemdog D [Clementine pheno] × (GrapeApe × OG Male)',
         'source': 'SeedFinder / Apothecary Genetics'},
        {'valeur': 'Chemdawg × GSC (version publiée standard)',
         'source': 'littérature breeder — diverge de la fiche SeedFinder'},
    ],
    'runtz': [
        {'valeur': 'Runtz × Auto OG Kush (fiche auto)',
         'source': 'SeedFinder / Humboldt Seed Organisation'},
        {'valeur': 'Zkittlez × Gelato (pedigree original) — absent de SeedFinder',
         'source': 'littérature breeder'},
    ],
    'zoap': [
        {'valeur': 'RS-11 × Pink Guava', 'source': 'SeedFinder / Unknown or Legendary'},
        {'valeur': 'Rainbow Sherbet × Pink Guava (version citée)',
         'source': 'littérature — à trancher'},
    ],
}

# --- dataset CSV 8910 : detection des genetic_background "filler" ---
# (5 valeurs generiques reparties sur ~700 lignes : donnees source non fiables)
_bg_count = defaultdict(int)
for row in csv_rows:
    bg = (row.get('genetic_background') or '').strip()
    if bg:
        _bg_count[bg] += 1
FILLER_BG = {bg for bg, n in _bg_count.items() if n >= 30}

def is_filler_bg(bg):
    return (bg or '').strip() in FILLER_BG

def pick_csv(recs, sf_breeder=''):
    """Choisit la meilleure ligne CSV : background non-filler > champs remplis > breeder concordant."""
    def score(r):
        s = 0
        bg = (r.get('genetic_background') or '').strip()
        if bg and not is_filler_bg(bg):
            s += 4
        for f_ in ('thc', 'cbd', 'yield_indoor', 'flowering_time', 'effect', 'flavor'):
            if (r.get(f_) or '').strip():
                s += 1
        if sf_breeder and norm(r.get('breeder', '')) == norm(sf_breeder):
            s += 3
        return s
    if not recs:
        return None
    return max(recs, key=score)

# ---------------- score commercial ----------------
# max pour normalisation (sur les 31)
_max_yield, _max_reviews = 0, 0
_tmp = []
for s in sf:
    c = csv_idx.get(norm(s['name']), [])
    for row in c:
        v = parse_gm2(row.get('yield_indoor'))
        if v:
            _max_yield = max(_max_yield, v)
    l = pick_leafly(lf_idx.get(norm(s['name']), []))
    if l and l.get('reviews'):
        _max_reviews = max(_max_reviews, l['reviews'])
_max_yield = _max_yield or 1
_max_reviews = _max_reviews or 1

W = {'yield': .35, 'terpene': .20, 'vigor': .15, 'pm': .10, 'bag': .10, 'market': .10}

def commercial_score(yield_gm2, rating10, n_ratings, leafly_reviews):
    parts, flags = {}, []
    if yield_gm2:
        parts['yield'] = min(100.0, yield_gm2 / _max_yield * 100)
    else:
        flags.append('yield: pas de g/m² exploitable')
    parts['terpene'] = None; flags.append('terpene: aucune donnée labo (NULL)')
    parts['vigor'] = None;   flags.append('vigueur: aucune donnée (NULL)')
    parts['pm'] = None;      flags.append('PM: aucune donnée (NULL)')
    if rating10:
        conf = min(1.0, math.log10((n_ratings or 0) + 1) / 2) if n_ratings else 0.5
        parts['bag'] = round(rating10 * 10 * conf, 1)  # proxy documenté
    else:
        flags.append('bag_appeal: aucune note')
    if leafly_reviews:
        parts['market'] = round(leafly_reviews / _max_reviews * 100, 1)
    else:
        flags.append('marché: pas de fiche Leafly')
    avail = {k: v for k, v in parts.items() if v is not None}
    if not avail:
        return None, True, parts, flags
    score = sum(W[k] * v for k, v in avail.items()) / sum(W[k] for k in avail)
    return round(score, 1), len(avail) < 6, parts, flags

# ---------------- fusion des 31 ----------------
fused, match_stats = [], defaultdict(int)
for s in sf:
    key = norm(s['name'])
    display = DISPLAY_OVERRIDE.get(s['name'], s['name'])
    g = (gd_idx.get(key) or {}).get('growdiaries', {})
    b = br_idx.get(key, {})
    k = kn_idx.get(key)
    l = pick_leafly(lf_idx.get(key, []))
    cands = csv_idx.get(key, [])
    c0 = pick_csv(cands, s.get('breeder', ''))
    n_csv_cands = len(cands)

    sources, urls = [], {}
    if s: sources.append('seedfinder'); urls['seedfinder'] = s.get('source_url')
    if g and g.get('status') == 'found':
        sources.append('growdiaries'); urls['growdiaries'] = g.get('url'); match_stats['growdiaries'] += 1
    if b and (b.get('mother') or b.get('parent_use_evidence')):
        sources.append('breeder'); 
        if b.get('source_url'): urls['breeder'] = b['source_url']
        match_stats['breeder'] += 1
    if k: sources.append('kannapedia'); urls['kannapedia'] = k.get('source_url'); match_stats['kannapedia'] += 1
    if c0: sources.append('dataset-8910'); match_stats['dataset-8910'] += 1
    if l: sources.append('leafly'); urls['leafly'] = f"https://www.leafly.com/strains/{l.get('slug')}"; match_stats['leafly'] += 1
    match_stats['seedfinder'] += 1

    aliases = set()
    for nm in (s.get('name'), g.get('cultivar'), (b or {}).get('cultivar')):
        if nm and nm != display:
            aliases.add(nm)
    aliases = sorted(aliases)

    # --- pedigree : officiel breeder > seedfinder ; conflits listes, jamais tranches ---
    mother = father = lineage_src = None
    conflits = []
    if b and b.get('mother') and b.get('father'):
        mother, father, lineage_src = b['mother'], b['father'], 'breeder_officiel'
    if s.get('parent_1') and s.get('parent_2'):
        sm, sfth = s['parent_1'], s['parent_2']
        if mother and (lin_norm(mother) != lin_norm(sm) or lin_norm(father) != lin_norm(sfth)):
            conflits.append({'champ': 'mother×father',
                             'versions': [{'valeur': f'{mother} × {father}', 'source': 'breeder officiel'},
                                          {'valeur': f'{sm} × {sfth}', 'source': 'SeedFinder'}]})
        elif not mother:
            mother, father, lineage_src = sm, sfth, 'seedfinder'
    if key in KNOWN_CONFLICTS:
        conflits.append({'champ': 'lineage (versions publiees)',
                         'versions': KNOWN_CONFLICTS[key]})
    csv_bg = (c0.get('genetic_background') or '').strip() if c0 else ''
    flags = []  # initialise ici car le bloc filler ci-dessous l'utilise
    if csv_bg and not is_filler_bg(csv_bg) and s.get('lineage_raw'):
        # compare en ignorant le parenthesage
        a = lin_norm(csv_bg).replace('(', ' ').replace(')', ' ')
        bb = lin_norm(s['lineage_raw']).replace('(', ' ').replace(')', ' ')
        if a != bb:
            conflits.append({'champ': 'genetic_background',
                             'versions': [{'valeur': csv_bg, 'source': 'dataset-8910 (Seed City)'},
                                          {'valeur': s['lineage_raw'], 'source': 'SeedFinder'}]})
    elif c0 and (not csv_bg or is_filler_bg(csv_bg)):
        flags.append('dataset-8910 : genetic_background générique/filler — ignoré pour la lignée'
                     + (f' ({n_csv_cands} lignes CSV pour ce cultivar)' if n_csv_cands > 1 else ''))

    # --- champs ---
    thc = g.get('thc_pct')
    if thc is None and c0: thc = parse_pct(c0.get('thc'))
    if thc is None and l: thc = l.get('thc')
    cbd = g.get('cbd_pct')
    if cbd is None and c0: cbd = parse_pct(c0.get('cbd'))
    rating10, n_ratings = g.get('rating_10'), (g.get('harvests') or g.get('diaries') or 0)
    if rating10 is None and l:
        rating10, n_ratings = (l['rating'] / 5 * 10) if l.get('rating') else None, (l.get('reviews') or 0)
    yield_gm2 = parse_gm2(c0.get('yield_indoor')) if c0 else None

    score, partiel, parts, score_flags = commercial_score(
        yield_gm2, rating10, n_ratings, (l or {}).get('reviews'))

    if key == 'georgia pie' and (g.get('thc_pct') == 14):
        flags.append('Georgia Pie : THC 14 % affiché sur GrowDiaries — invraisemblable vs avis')
    if key == 'permanent marker' and g.get('notes') and '8.4' in str(g.get('notes')):
        flags.append('Permanent Marker : note 8,4 (listing) vs 9,4 (fiche) — donnée vivante')
    if key == 'red pop':
        flags.append('Red Pop : lignée legacy sur GrowDiaries (diaries 4-6 ans) — ne pas fusionner avec un Red Pop moderne sans vérifier le breeder')
    if key == 'super boof':
        flags.append('Super Boof : SeedFinder n’a que des auto-croisements — vraie lignée absente')
    if key == 'alien mints':
        flags.append('Alien Mints : Animal Mints × Animal Mints sur SeedFinder — probable S1')
    yh = g.get('yield_g_plant_observed') or []
    if yh and len(yh) <= 2:
        flags.append(f'rendement GrowDiaries n={len(yh)} — faible fiabilité (auto-déclaré)')
    if b and b.get('breeder_status') == 'non_vendu_direct' and not b.get('parent_use_evidence'):
        flags.append('breeder : non vendu en direct, aucune lignée officielle')
    flags.extend('score: ' + f for f in score_flags if 'aucune' in f or 'pas de' in f)

    rec = {
        'cultivar': display,
        'breeder': (b.get('breeder') if b and b.get('breeder') else s.get('breeder')),
        'aliases': aliases,
        'mother': mother, 'father': father, 'lineage_src': lineage_src,
        'lineage_raw_seedfinder': s.get('lineage_raw'),
        'lineage_conflits': conflits,
        'flowering_days': s.get('flowering_days') or parse_days(g.get('flowering_days_observed')),
        'type': s.get('type'),
        'thc_pct': thc, 'cbd_pct': cbd,
        'thc_src': 'growdiaries' if g.get('thc_pct') is not None else ('dataset-8910' if c0 and parse_pct(c0.get('thc')) is not None else ('leafly' if l and l.get('thc') else None)),
        'rating_10': round(rating10, 2) if rating10 else None,
        'rating_src': 'growdiaries' if g.get('rating_10') else ('leafly' if l and l.get('rating') else None),
        'harvests': g.get('harvests'), 'diaries': g.get('diaries'),
        'yield_g_plant_median': g.get('yield_g_plant_median'),
        'yield_gm2_csv': round(yield_gm2, 1) if yield_gm2 else None,
        'heterozygosity_pct': k.get('heterozygosity_pct') if k else None,
        'dna_variants': k.get('high_impact_variants') if k else None,
        'dna_report_type': k.get('report_type') if k else None,
        'parent_use_evidence': b.get('parent_use_evidence') if b else {},
        'leafly': {'rating': l.get('rating'), 'reviews': l.get('reviews'),
                   'top_effect': l.get('topEffect'), 'top_terp': l.get('topTerp'),
                   'phenotype': l.get('phenotype')} if l else None,
        'csv8910': {'breeder': c0.get('breeder'), 'thc': c0.get('thc'), 'cbd': c0.get('cbd'),
                    'yield_indoor': c0.get('yield_indoor'), 'yield_outdoor': c0.get('yield_outdoor'),
                    'flowering_time': c0.get('flowering_time'),
                    'genetic_background': c0.get('genetic_background'),
                    'indica_sativa': c0.get('indica_sativa'), 'effect': c0.get('effect'),
                    'flavor': c0.get('flavor')} if c0 else None,
        'sources': sources,
        'source_urls': urls,
        'commercial_score': score,
        'score_partiel': partiel,
        'score_detail': {kk: vv for kk, vv in parts.items()},
        'flags_qualite': flags,
    }
    fused.append(rec)

with open(f'{OUT}/cultivars_prioritaires.json', 'w', encoding='utf-8') as f:
    json.dump(fused, f, ensure_ascii=False, indent=1)

# ---------------- base 8910 enrichie ----------------
sf31 = {norm(s['name']): s for s in sf}
n_lf = n_sf = 0
with open(f'{OUT}/base_8910_enrichie.jsonl', 'w', encoding='utf-8') as out:
    for row in csv_rows:
        key = norm(row.get('strain_name', ''))
        l = pick_leafly(lf_idx.get(key, []))
        s = sf31.get(key)
        rec = dict(row)
        rec['badges'] = ['dataset-8910']
        if l:
            n_lf += 1
            rec['badges'].append('leafly')
            rec['leafly'] = {'rating': l.get('rating'), 'reviews': l.get('reviews'),
                             'thc': l.get('thc'), 'top_effect': l.get('topEffect'),
                             'top_terp': l.get('topTerp'), 'phenotype': l.get('phenotype'),
                             'slug': l.get('slug')}
        if s:
            n_sf += 1
            rec['badges'].append('seedfinder')
            rec['seedfinder'] = {'parent_1': s.get('parent_1'), 'parent_2': s.get('parent_2'),
                                 'lineage_raw': s.get('lineage_raw'),
                                 'flowering_days': s.get('flowering_days'),
                                 'type': s.get('type'), 'breeder': s.get('breeder'),
                                 'url': s.get('source_url')}
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')

# ---------------- rapport ----------------
scores = [(r['cultivar'], r['commercial_score']) for r in fused if r['commercial_score'] is not None]
scores.sort(key=lambda x: -x[1])
n_conf = sum(1 for r in fused if r['lineage_conflits'])
dist = defaultdict(int)
for _, sc in scores:
    dist[f"{int(sc//10)*10}-{int(sc//10)*10+9}"] += 1

def fsize(p):
    return os.path.getsize(p)

report = f"""# Rapport de fusion v1 — cannabis-data-fusion (2026-10-11)

## Méthode
- 31 cultivars prioritaires : SeedFinder (vérité pedigree) + GrowDiaries (rendements/THC/notes)
  + breeders officiels (lignée primaire + parent_use_evidence) + kannapedia (ADN)
  + dataset CSV 8 910 (Seed City) + index Leafly __NEXT_DATA__ (8 816).
- Normalisation des noms insensible à la casse/ponctuation + alias
  (Honey Banana=Bananas, Don Mega=The Don Mega, RS11=RS-11, GMO=GMO Cookies).
  Match exact sur nom normalisé uniquement ; doublons Leafly → fiche max reviews.
- Conflits de lignée : listés avec versions + sources, jamais tranchés.
- Score commercial : yield×.35 + terp×.20 + vigor×.15 + PM×.10 + bag×.10 + marché×.10.
  terpènes/vigueur/PM = NULL partout (aucune donnée réelle) → tous les scores sont
  partiels (recalcul au prorata des sous-scores disponibles : yield, bag_appeal, marché).
  bag_appeal = proxy (note×10 × confiance log10(n)) — documenté comme proxy.

## Taux de matching (sur 31)
- seedfinder : {match_stats['seedfinder']}/31 (base des 31)
- growdiaries : {match_stats['growdiaries']}/31
- breeder (lignée officielle ou parent_use) : {match_stats['breeder']}/31
- kannapedia (ADN) : {match_stats['kannapedia']}/31
- dataset-8910 : {match_stats['dataset-8910']}/31
- leafly : {match_stats['leafly']}/31
- CSV 8 910 enrichi : {n_lf}/8910 avec Leafly, {n_sf}/8910 avec SeedFinder (31)

## Conflits de pedigree ({n_conf} cultivars)
"""
for r in fused:
    if r['lineage_conflits']:
        report += f"\n### {r['cultivar']}\n"
        for c in r['lineage_conflits']:
            report += f"- {c['champ']} :\n"
            for v in c['versions']:
                report += f"  - « {v['valeur']} » ← {v['source']}\n"

report += f"""
## Distribution des commercial_score (n={len(scores)}, tous partiels)
"""
for bkt in sorted(dist):
    report += f"- {bkt} : {'█' * dist[bkt]} {dist[bkt]}\n"
report += "\nTop 5 :\n" + "".join(f"- {c} : {sc}\n" for c, sc in scores[:5])
report += "\nBottom 5 :\n" + "".join(f"- {c} : {sc}\n" for c, sc in scores[-5:])

report += f"""
## Limites honnêtes
- Aucune donnée terpènes/vigueur/PM réelle → 3 sous-scores NULL, scores partiels.
- Rendements GrowDiaries : auto-déclarés, petits n — faible fiabilité (flaggé par fiche).
- THC : GrowDiaries (déclaratif cultivateurs) > CSV seedbank > Leafly ; pas de labo.
- Données vivantes : notes/compteurs bougent entre deux lectures.
- Georgia Pie THC 14 % (invraisemblable), Red Pop legacy, Super Boof/Alien Mints faibles.
- 5 cultivars absents de GrowDiaries ; 27/31 sans ADN kannapedia ; 29/31 sans lignée breeder officielle.
- dataset-8910 : les 5 genetic_background les plus fréquents (Northern Lights x Haze,
  Haze x Skunk, Afghani x Mexican, Colombian x Mexican, Afghani x Thai — 700 lignes)
  sont des valeurs filler du seedbank → ignorés pour les lignées ; meilleure ligne
  choisie par complétude des champs.

## Fichiers
- cultivars_prioritaires.json : {fsize(f'{OUT}/cultivars_prioritaires.json')/1024:.0f} Ko (31 fiches)
- base_8910_enrichie.jsonl : {fsize(f'{OUT}/base_8910_enrichie.jsonl')/1024/1024:.1f} Mo (8 910 lignes)
"""
with open(f'{OUT}/fusion_report.md', 'w', encoding='utf-8') as f:
    f.write(report)

print('fused:', len(fused), '| scores:', len(scores), '| conflits:', n_conf)
print('csv enrichi: leafly', n_lf, '| seedfinder', n_sf)
print('tailles:', fsize(f'{OUT}/cultivars_prioritaires.json'), fsize(f'{OUT}/base_8910_enrichie.jsonl'))
