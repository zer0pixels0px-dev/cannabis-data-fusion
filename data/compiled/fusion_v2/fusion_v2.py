#!/usr/bin/env python3
"""FUSION v2 — cannabis-data-fusion : enrichit fusion_elargie.json (v1, archive)
avec les 41 858 pages du crawl SeedFinder phase 2.

Regles : jamais inventer (null honnete), chaque valeur porte sa source,
         conflits exposes jamais tranches.
         Ne modifie PAS fusion_elargie.json (archive v1 intouchable).
Sorties : fusion_v2.json, fusion_v2_report.md (dossier fusion_v2/).
"""
import copy, glob, json, os, re, statistics, unicodedata
from collections import Counter, defaultdict

BASE = os.path.expanduser('~/workspace/research_notes')
V1 = os.path.join(BASE, 'compiled-20261011', 'fusion_elargie.json')
PAGES = os.path.join(BASE, 'seedfinder-20261011', 'pages')
OUT = os.path.join(BASE, 'compiled-20261011', 'fusion_v2')
os.makedirs(OUT, exist_ok=True)

# ---------------- normalisation (copie de fuse_v2_lite.py — pas d'import :
# l'import executerait tout le pipeline v1 et reecrirait l'archive) ----------------
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

PHENO_MAP = {
    'indica': 'Indica',
    'sativa': 'Sativa',
    'indica / sativa': 'Hybrid',
    'mostly indica': 'Indica-dominant',
    'mostly sativa': 'Sativa-dominant',
    'ruderalis / indica / sativa': 'Hybrid (auto)',
    'ruderalis / indica': 'Indica-dominant (auto)',
    'ruderalis / sativa': 'Sativa-dominant (auto)',
}
def norm_pheno(t):
    if not t or not isinstance(t, str):
        return None, False
    t = t.strip().lower()
    disc = t.startswith('discontinued')
    if disc:
        t = t[len('discontinued'):].strip()
    if t == 'unknown' or not t:
        return None, disc
    return PHENO_MAP.get(t, t.title()), disc

def clean_terms(raw, fix_split=True):
    """effect_data / aroma_data -> liste de termes propres."""
    if not raw or not isinstance(raw, str):
        return []
    t = re.sub(r'View all.*$', '', raw, flags=re.I).strip()
    toks = t.split()
    out, i = [], 0
    while i < len(toks):
        if fix_split and i + 1 < len(toks) and (toks[i], toks[i + 1]) in (
                ('Pain', 'numbing'), ('Thought', 'provoking')):
            out.append(toks[i] + ' ' + toks[i + 1]); i += 2
        elif toks[i] == 'Meditativ':
            out.append('Meditative'); i += 1
        else:
            out.append(toks[i]); i += 1
    seen, res = set(), []
    for x in out:
        if x.lower() not in seen:
            seen.add(x.lower()); res.append(x)
    return res

def clean_taste(raw, limit=400):
    if not raw or not isinstance(raw, str):
        return None
    t = re.sub(r'View all.*$', '', raw, flags=re.I).strip()
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) < 3:
        return None
    return t[:limit] + ('…' if len(t) > limit else '')

def informative_pairs(pairs, key):
    """Paires exploitables pour la lignée d'un cultivar : exclut les
    autofécondations (p1 == p2) et les croisements impliquant le cultivar
    lui-même ou une de ses versions (ex. 'Blue Dream' x 'Blue Dream [reversed]',
    'Blue Dream' x 'Kush Dreams' = produits dérivés, pas la lignée)."""
    key_toks = set(key.split())
    out, seen = [], set()
    for a, b, br in pairs:
        na, nb = norm(a), norm(b)
        if not na or not nb or na == nb:
            continue
        ta, tb = set(na.split()), set(nb.split())
        if key_toks <= ta or ta <= key_toks or key_toks <= tb or tb <= key_toks:
            continue
        k = (na, nb)
        if k not in seen:
            seen.add(k)
            out.append((a, b, br))
    return out

def clean_awards(raw, limit=400):
    if not raw or not isinstance(raw, str):
        return None
    if not re.search(r'\b(won|cup|place|award)\b', raw, re.I):
        return None
    t = re.sub(r'\s+', ' ', raw).strip()
    return t[:limit] + ('…' if len(t) > limit else '')

stats = Counter()

# ---------------- passe 1 : grouper les pages ----------------
groups = defaultdict(list)  # norm(name) -> [page courte]
files = glob.glob(os.path.join(PAGES, '*.json'))
stats['pages_trouvees'] = len(files)
for fp in files:
    try:
        with open(fp, encoding='utf-8') as fh:
            d = json.load(fh)
    except Exception:
        stats['pages_invalides'] += 1
        continue
    name = d.get('name')
    key = norm(name)
    if not key:
        stats['pages_sans_nom'] += 1
        continue
    pheno, disc = norm_pheno(d.get('type'))
    fd = d.get('flowering_days')
    groups[key].append({
        'name': name, 'breeder': d.get('breeder'), 'url': d.get('source_url'),
        'pheno': pheno, 'disc': disc,
        'cultivation': d.get('cultivation'), 'seed_type': d.get('seed_type'),
        'fd': fd if isinstance(fd, int) else None,
        'p1': d.get('parent_1'), 'p2': d.get('parent_2'),
        'parent_links': d.get('parent_links') or [],
        'lineage_raw': d.get('lineage_raw'),
        'extended_tree': d.get('extended_tree') or [],
        'effets': clean_terms(d.get('effect_data')),
        'aromes': clean_terms(d.get('aroma_data'), fix_split=False),
        'gout': clean_taste(d.get('taste_data')),
        'awards': clean_awards(d.get('awards')),
        'desc': (d.get('breeder_description') or '').strip(),
    })
stats['groupes_seedfinder'] = len(groups)

# ---------------- index v1 ----------------
with open(V1, encoding='utf-8') as fh:
    v1 = json.load(fh)
v1_idx = {}
for e in v1:
    k = norm(e.get('name'))
    if k and k not in v1_idx:
        v1_idx[k] = e
    for a in e.get('aliases', []) or []:
        ka = norm(a)
        if ka and ka not in v1_idx:
            v1_idx[ka] = e
stats['entrees_v1'] = len(v1)

# ---------------- agregation + fusion ----------------
def aggregate(pages):
    breeders = [p['breeder'] for p in pages if p['breeder']]
    bcount = Counter(breeders)
    urls = [p['url'] for p in pages if p['url']]
    phenos = [p['pheno'] for p in pages if p['pheno']]
    fds = [p['fd'] for p in pages if p['fd']]
    pairs = []
    seen_pair = set()
    for p in pages:
        if p['p1'] and p['p2']:
            k = (norm(p['p1']), norm(p['p2']))
            if k not in seen_pair:
                seen_pair.add(k)
                pairs.append((p['p1'], p['p2'], p['breeder']))
    effets, aromes = [], []
    for p in pages:
        for x in p['effets']:
            if x.lower() not in {y.lower() for y in effets}:
                effets.append(x)
        for x in p['aromes']:
            if x.lower() not in {y.lower() for y in aromes}:
                aromes.append(x)
    gouts = [p['gout'] for p in pages if p['gout']]
    descs = [(len(p['desc']), p['desc'], p['breeder']) for p in pages if p['desc']]
    awards = [p['awards'] for p in pages if p['awards']]
    trees = [p['extended_tree'] for p in pages if p['extended_tree']]
    plinks = [p['parent_links'] for p in pages if p['parent_links']]
    lins = [p['lineage_raw'] for p in pages if p['lineage_raw']]
    disc = any(p['disc'] for p in pages)
    # nom d'affichage : le plus frequent, ex-aequo le plus long
    nc = Counter(p['name'] for p in pages if p['name'])
    display = sorted(nc.items(), key=lambda kv: (-kv[1], -len(kv[0])))[0][0]
    return {
        'display': display, 'breeders': breeders, 'breeder_top': bcount.most_common(1)[0][0] if bcount else None,
        'urls': urls, 'phenos': phenos, 'fds': fds, 'pairs': pairs,
        'effets': effets, 'aromes': aromes, 'gouts': gouts,
        'desc': max(descs)[1] if descs else None,
        'desc_breeder': max(descs)[2] if descs else None,
        'awards': awards, 'trees': trees, 'plinks': plinks, 'lins': lins, 'disc': disc,
        'n': len(pages),
    }

def build_sf_block(ag):
    pheno_c = Counter(ag['phenos'])
    fd_med = round(statistics.median(ag['fds'])) if ag['fds'] else None
    block = {
        'nb_fiches': ag['n'],
        'breeders': sorted(set(ag['breeders'])),
        'urls': ag['urls'][:8],
        'type_normalise': pheno_c.most_common(1)[0][0] if pheno_c else None,
        'type_graine': None, 'floraison_jours': fd_med,
        'parents': None, 'lignage_brut': ag['lins'][0] if ag['lins'] else None,
        'arbre_genealogique': ag['trees'][0] if ag['trees'] else None,
        'liens_parents': ag['plinks'][0] if ag['plinks'] else None,
        'effets': ag['effets'] or None, 'aromes': ag['aromes'] or None,
        'gout': ag['gouts'][0] if ag['gouts'] else None,
        'recompenses': ag['awards'][:3] or None,
        'description_breeder': (ag['desc'][:600] + ('…' if len(ag['desc']) > 600 else '')) if ag['desc'] else None,
        'description_breeder_source': ag['desc_breeder'],
    }
    # culture / type_graine sont renseignes par l'appelant (besoin du detail des pages)
    return block

def sparse_rec(rec):
    for sub in ('production', 'breeder_origine', 'parents', 'populaire', 'donnees_seedfinder'):
        if sub in rec and isinstance(rec[sub], dict):
            for kk in [kk for kk, vv in rec[sub].items() if vv is None or vv == [] or vv == {}]:
                del rec[sub][kk]
    for kk in [kk for kk, vv in rec.items() if vv is None or vv == [] or vv == {}]:
        if kk not in ('production', 'breeder_origine', 'parents', 'populaire', 'badges', 'name',
                      'donnees_seedfinder'):
            del rec[kk]
    return rec

# --- passe 2 ---
fused = []
n_matched = n_new = 0
for key in sorted(groups):
    pages = groups[key]
    ag = aggregate(pages)
    # culture / type_graine : valeurs les plus frequentes
    cult_c = Counter(p['cultivation'] for p in pages if p['cultivation'])
    st_c = Counter(p['seed_type'] for p in pages if p['seed_type'] and isinstance(p['seed_type'], str))
    sf = build_sf_block(ag)
    sf['culture'] = cult_c.most_common(1)[0][0] if cult_c else None
    sf['type_graine'] = st_c.most_common(1)[0][0] if st_c else None
    # parents : paire informative la plus frequente (jamais d'autofecondation
    # ni de croisement impliquant le cultivar lui-meme pour le remplissage plat)
    inf = informative_pairs(ag['pairs'], key)
    pair = None
    if inf:
        pc = Counter((norm(a), norm(b)) for a, b, _ in inf)
        topk = pc.most_common(1)[0][0]
        pair = next((a, b) for a, b, _ in inf if (norm(a), norm(b)) == topk)
    sf['parents'] = {'mere': pair[0], 'pere': pair[1]} if pair else None
    sf['nb_versions_lignee'] = len(ag['pairs'])

    e = v1_idx.get(key)
    if e is not None:
        # ---------- MATCH : enrichir sans remplacer ----------
        r = copy.deepcopy(e)
        n_matched += 1
        stats['sf_groupes_matchés'] += 1
        if 'seedfinder' not in r.get('badges', []):
            r.setdefault('badges', []).append('seedfinder')
        r.setdefault('source_urls', {})
        if 'seedfinder' not in r['source_urls'] and ag['urls']:
            r['source_urls']['seedfinder'] = ag['urls'][0]
            stats['url_seedfinder_ajoutee'] += 1
        if not r.get('fiche_source') and ag['breeder_top']:
            r['fiche_source'] = ag['breeder_top']
            stats['fiche_source_completee'] += 1
        pheno_top = Counter(ag['phenos']).most_common(1)
        if 'phenotype' not in r and pheno_top:
            r['phenotype'] = pheno_top[0][0]
            stats['phenotype_complete'] += 1
        if 'floraison_jours' not in r and sf['floraison_jours']:
            r['floraison_jours'] = sf['floraison_jours']
            stats['floraison_completee'] += 1
        elif 'floraison_jours' in r and sf['floraison_jours']:
            if abs(r['floraison_jours'] - sf['floraison_jours']) > 7:
                r.setdefault('flags_qualite', []).append(
                    f"floraison : {r['floraison_jours']} j (existant) vs "
                    f"{sf['floraison_jours']} j (seedfinder) — non tranche")
                stats['divergence_floraison'] += 1
        if 'lineage_raw' not in r and sf['lignage_brut']:
            r['lineage_raw'] = sf['lignage_brut']
            stats['lineage_raw_complete'] += 1
        # parents : remplir si absent ET consensus informatif, conflit si divergent.
        # Jamais de remplissage plat depuis des autofecondations ou des
        # croisements impliquant le cultivar lui-meme.
        mere_e = (r.get('parents') or {}).get('mere')
        n_inf = len(inf)
        if not mere_e and n_inf == 1 and pair:
            r.setdefault('parents', {})['mere'] = pair[0]
            r['parents']['pere'] = pair[1]
            r['parents']['sources'] = ['seedfinder']
            stats['parents_completes'] += 1
        elif not mere_e and n_inf > 1:
            versions = [{'valeur': f'{a} x {b}', 'source': f'seedfinder / {br or "?"}'}
                        for a, b, br in inf[:6]]
            r.setdefault('conflits_lignee', []).append(
                {'champ': 'parents (versions seedfinder)', 'versions': versions})
            stats['conflit_parents_intra_sf'] += 1
        elif not mere_e and ag['pairs']:
            r.setdefault('flags_qualite', []).append(
                'seedfinder : fiches = autofecondations/croisements derives — '
                'aucune lignee informative, parents non repris')
            stats['parents_non_informatifs'] += 1
        elif mere_e and pair:
            if norm(mere_e) != norm(pair[0]) or norm((r['parents']).get('pere')) != norm(pair[1]):
                versions = [{
                    'valeur': f"{mere_e} x {r['parents'].get('pere')}",
                    'source': 'existantes : ' + ', '.join((r['parents']).get('sources') or ['?']),
                }]
                for a, b, br in inf[:5]:
                    versions.append({'valeur': f'{a} x {b}', 'source': f'seedfinder / {br or "?"}'})
                r.setdefault('conflits_lignee', []).append(
                    {'champ': 'parents (seedfinder vs existant)', 'versions': versions})
                stats['conflit_parents'] += 1
        if ag['disc']:
            r.setdefault('flags_qualite', []).append('discontinued (seedfinder)')
        if ag['n'] > 1:
            r.setdefault('flags_qualite', []).append(
                f"seedfinder : {ag['n']} fiches breeders fusionnees")
            stats['entrees_multi_breeders'] += 1
        r['donnees_seedfinder'] = sf
        stats['donnees_seedfinder_ajoutees'] += 1
        fused.append(sparse_rec(r))
    else:
        # ---------- NOUVEAU cultivar ----------
        n_new += 1
        stats['sf_groupes_nouveaux'] += 1
        n_inf = len(inf)
        r = {
            'name': ag['display'],
            'breeder_origine': {'value': None, 'source': None, 'qualite': None},
            'fiche_source': ag['breeder_top'],
            'parents': ({'mere': pair[0], 'pere': pair[1], 'sources': ['seedfinder']}
                        if (n_inf == 1 and pair) else {}),
            'lineage_raw': sf['lignage_brut'],
            'floraison_jours': sf['floraison_jours'],
            'phenotype': Counter(ag['phenos']).most_common(1)[0][0] if ag['phenos'] else None,
            'production': {},
            'populaire': {'vrai': False, 'raisons': []},
            'badges': ['seedfinder'],
            'source_urls': {'seedfinder': ag['urls'][0]} if ag['urls'] else {},
            'flags_qualite': [],
            'donnees_seedfinder': sf,
        }
        if ag['disc']:
            r['flags_qualite'].append('discontinued (seedfinder)')
        if ag['n'] > 1:
            r['flags_qualite'].append(f"seedfinder : {ag['n']} fiches breeders fusionnees")
        if n_inf > 1:
            versions = [{'valeur': f'{a} x {b}', 'source': f'seedfinder / {br or "?"}'}
                        for a, b, br in inf[:6]]
            r['conflits_lignee'] = [{'champ': 'parents (versions seedfinder)', 'versions': versions}]
            stats['conflit_parents_nouveaux'] += 1
        elif ag['pairs']:
            r['flags_qualite'].append(
                'seedfinder : fiches = autofecondations/croisements derives — '
                'aucune lignee informative, parents non repris')
        fused.append(sparse_rec(r))

# ajouter les entrees v1 sans page seedfinder (copie intacte)
matched_ids = set()
for key, pages in groups.items():
    if v1_idx.get(key) is not None:
        matched_ids.add(id(v1_idx[key]))
for e in v1:
    if id(e) not in matched_ids:
        fused.append(copy.deepcopy(e))
        stats['entrees_v1_sans_seedfinder'] += 1

stats['entrees_fusion_v2'] = len(fused)

with open(os.path.join(OUT, 'fusion_v2.json'), 'w', encoding='utf-8') as fh:
    json.dump(fused, fh, ensure_ascii=False, separators=(',', ':'))
print('OK — entrees v2:', len(fused), '| matches:', n_matched, '| nouveaux:', n_new)
print(json.dumps({k: v for k, v in stats.items()}, ensure_ascii=False, indent=1))

with open(os.path.join(OUT, 'fusion_v2_stats.json'), 'w', encoding='utf-8') as fh:
    json.dump(dict(stats), fh, ensure_ascii=False, indent=1)
