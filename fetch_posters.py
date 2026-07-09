#!/usr/bin/env python3
"""
Fetch missing poster images using TMDB API (by IMDB ID).
Usage: python fetch_posters.py <TMDB_API_KEY>
Get a free key at: https://www.themoviedb.org/settings/api
"""
import json, re, sys, time
import requests

sys.stdout.reconfigure(encoding='utf-8')

if len(sys.argv) < 2:
    print("Ús: python fetch_posters.py <TMDB_API_KEY>")
    sys.exit(1)

API_KEY   = sys.argv[1]
JSON_PATH = 'C:/TSS/proyectos/series-tracker/series.json'
TMDB_BASE = 'https://api.themoviedb.org/3'
IMG_BASE  = 'https://image.tmdb.org/t/p/w185'

def extract_imdb_id(url):
    m = re.search(r'tt\d+', str(url))
    return m.group(0) if m else None

def get_poster(imdb_id):
    try:
        r = requests.get(
            f'{TMDB_BASE}/find/{imdb_id}',
            params={'api_key': API_KEY, 'external_source': 'imdb_id'},
            timeout=10
        )
        if r.status_code == 429:
            time.sleep(2)
            return get_poster(imdb_id)  # retry
        if r.status_code != 200:
            return None
        d = r.json()
        # Try TV results first, then movie results
        for key in ('tv_results', 'movie_results', 'tv_episode_results'):
            results = d.get(key, [])
            if results and results[0].get('poster_path'):
                return IMG_BASE + results[0]['poster_path']
    except Exception as e:
        print(f"  Error: {e}")
    return None

with open(JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

missing = [(i, s) for i, s in enumerate(data)
           if not s.get('g') and s.get('u') and 'imdb.com' in s.get('u', '')]

print(f"Series sense poster: {len(missing)}")
print(f"Processant amb TMDB API...\n")

updated = 0
errors  = 0

for n, (i, s) in enumerate(missing, 1):
    imdb_id = extract_imdb_id(s.get('u', ''))
    if not imdb_id:
        errors += 1
        continue

    poster = get_poster(imdb_id)

    if poster:
        data[i]['g'] = poster
        updated += 1
        status = '✓'
    else:
        errors += 1
        status = '✗'

    print(f"[{n:4}/{len(missing)}] {status} {s['t'][:60]}")

    # TMDB allows 40 requests/10s → ~4/s → safe with no extra delay
    # Add tiny sleep to be polite
    time.sleep(0.05)

    # Save every 100
    if n % 100 == 0:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        print(f"  → Guardat ({updated} afegits, {errors} sense poster fins ara)\n")

# Final save
with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

total_with = sum(1 for s in data if s.get('g'))
print(f"\n✅ Fi: {updated} posters nous afegits, {errors} no trobats")
print(f"   Total amb poster: {total_with} de {len(data)}")
