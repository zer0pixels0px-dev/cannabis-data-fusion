#!/usr/bin/env python3
"""Bonus v2-lite : images principales SeedFinder pour les 31 prioritaires.
Poli : 1 requete / 3 s via curl, UA identifie, arret au 2e echec consecutif.
Extrait l'image '01seeds' (photo principale de la fiche), ignore le logo og:image.
"""
import json, re, subprocess, time

BASE = '/home/hatch/workspace/research_notes'
UA = 'cannabis-data-fusion/1.0 (research; contact: zer0pixels0px-dev)'

sf = json.load(open(f'{BASE}/seedfinder-20261011/targets.json'))
out, fails = {}, 0
for s in sf:
    url = s.get('source_url')
    key = s.get('name', '').lower()
    try:
        p = subprocess.run(
            ['curl', '-s', '--max-time', '25', '--compressed', '-A', UA,
             '-H', 'Accept: text/html', '-w', '\n%{http_code}', url],
            capture_output=True, text=True, timeout=40)
        body, code = p.stdout.rsplit('\n', 1)
        if code.strip() != '200':
            raise RuntimeError(f'HTTP {code.strip()}')
        imgs = re.findall(r'https://seedfinder\.eu/storage/pics/01seeds/[^"\'\s\\]+', body)
        imgs = [i for i in imgs if not re.search(r'logo', i, re.I)]
        if imgs:
            out[key] = imgs[0]
            print('OK  ', s['name'])
        else:
            print('MISS', s['name'])
        fails = 0
    except Exception as e:
        fails += 1
        print('FAIL', s['name'], str(e)[:60], f'({fails}/2)')
        if fails >= 2:
            print('ABANDON : echecs repetes, on garde les fallbacks.')
            break
    time.sleep(3)

json.dump(out, open(f'{BASE}/seedfinder-20261011/sf_images.json', 'w'), ensure_ascii=False, indent=1)
print(f'\nimages : {len(out)}/31')
