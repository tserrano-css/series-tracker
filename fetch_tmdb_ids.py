#!/usr/bin/env python3
"""Fetch TMDB ID and type (tv/movie) for all series to build direct URLs."""
import json, re, sys, time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_KEY   = sys.argv[1] if len(sys.argv) > 1 else '844a662a1a742649db465e65709da7b4'
JSON_PATH = 'C:/TSS/proyectos/series-tracker/series.json'
TMDB_BASE = 'https://api.themoviedb.org/3'

def extract_imdb_id(url):
    m = re.search(r'tt\d+', str(url))
    return m.group(0) if m else None

def get_tmdb_id(imdb_id):
    try:
        r = requests.get(
            f'{TMDB_BASE}/find/{imdb_id}',
            params={'api_key': API_KEY, 'external_source': 'imdb_id'},
            timeout=10
        )
        if r.status_code == 429:
            time.sleep(2); return get_tmdb_id(imdb_id)
        if r.status_code != 200:
            return None, None
        d = r.json()
        for key, kind in [('tv_results','tv'), ('movie_results','movie')]:
            results = d.get(key, [])
            if results:
                return results[0]['id'], kind
    except Exception:
        pass
    return None, None

with open(JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

missing = [(i, s) for i, s in enumerate(data) if not s.get('tmid') and s.get('u')]
print(f"Sèries sense TMDB ID: {len(missing)}")

updated = 0
for n, (i, s) in enumerate(missing, 1):
    imdb_id = extract_imdb_id(s.get('u', ''))
    if not imdb_id:
        continue
    tmid, kind = get_tmdb_id(imdb_id)
    if tmid:
        data[i]['tmid'] = tmid
        data[i]['tmtype'] = kind
        updated += 1
        print(f"[{n:4}/{len(missing)}] ✓ {kind}/{tmid} {s['t'][:50]}")
    else:
        print(f"[{n:4}/{len(missing)}] ✗ {s['t'][:50]}")
    time.sleep(0.05)
    if n % 200 == 0:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',',':'))
        print(f"  → Guardat ({updated} IDs afegits)\n")

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',',':'))

print(f"\n✅ Fi: {updated} TMDB IDs afegits")
