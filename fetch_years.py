#!/usr/bin/env python3
"""Fetch start year from TMDB for all series that don't have it yet."""
import json, re, sys, time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_KEY   = sys.argv[1] if len(sys.argv) > 1 else '844a662a1a742649db465e65709da7b4'
JSON_PATH = 'C:/TSS/proyectos/series-tracker/series.json'
TMDB_BASE = 'https://api.themoviedb.org/3'

def extract_imdb_id(url):
    m = re.search(r'tt\d+', str(url))
    return m.group(0) if m else None

def get_year(imdb_id):
    try:
        r = requests.get(
            f'{TMDB_BASE}/find/{imdb_id}',
            params={'api_key': API_KEY, 'external_source': 'imdb_id'},
            timeout=10
        )
        if r.status_code == 429:
            time.sleep(2); return get_year(imdb_id)
        if r.status_code != 200:
            return None
        d = r.json()
        for key, date_field in [('tv_results','first_air_date'), ('movie_results','release_date')]:
            results = d.get(key, [])
            if results and results[0].get(date_field):
                return int(results[0][date_field][:4])
    except Exception:
        pass
    return None

with open(JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

missing = [(i, s) for i, s in enumerate(data)
           if not s.get('yr') and s.get('u') and 'imdb.com' in s.get('u','')]

print(f"Series sense any: {len(missing)}")

updated = 0
for n, (i, s) in enumerate(missing, 1):
    imdb_id = extract_imdb_id(s.get('u',''))
    if not imdb_id:
        continue
    year = get_year(imdb_id)
    if year:
        data[i]['yr'] = year
        updated += 1
        status = f'✓ {year}'
    else:
        status = '✗'
    print(f"[{n:4}/{len(missing)}] {status} {s['t'][:55]}")
    time.sleep(0.05)
    if n % 200 == 0:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',',':'))
        print(f"  → Guardat ({updated} anys afegits fins ara)\n")

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',',':'))

total_yr = sum(1 for s in data if s.get('yr'))
print(f"\n✅ Fi: {updated} anys afegits. Total amb any: {total_yr}/{len(data)}")
