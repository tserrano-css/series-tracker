#!/usr/bin/env python3
"""Fetch TMDB score and episode count for all series, recalculate media."""
import json, re, sys, time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_KEY   = sys.argv[1] if len(sys.argv) > 1 else '844a662a1a742649db465e65709da7b4'
JSON_PATH = 'C:/TSS/proyectos/series-tracker/series.json'
TMDB_BASE = 'https://api.themoviedb.org/3'

def extract_imdb_id(url):
    m = re.search(r'tt\d+', str(url))
    return m.group(0) if m else None

def get_tmdb_data(imdb_id):
    try:
        r = requests.get(
            f'{TMDB_BASE}/find/{imdb_id}',
            params={'api_key': API_KEY, 'external_source': 'imdb_id'},
            timeout=10
        )
        if r.status_code == 429:
            time.sleep(2); return get_tmdb_data(imdb_id)
        if r.status_code != 200:
            return None, None
        d = r.json()
        for key, eps_field in [('tv_results','number_of_episodes'), ('movie_results',None)]:
            results = d.get(key, [])
            if results:
                item = results[0]
                score = round(item.get('vote_average', 0), 1) or None
                # For TV: get full show data to get episode count
                if key == 'tv_results' and item.get('id'):
                    tv_id = item['id']
                    rv = requests.get(f'{TMDB_BASE}/tv/{tv_id}',
                                      params={'api_key': API_KEY}, timeout=10)
                    if rv.status_code == 200:
                        tvd = rv.json()
                        episodes = tvd.get('number_of_episodes') or None
                        score = round(tvd.get('vote_average', 0), 1) or None
                        return score, episodes
                return score, None
    except Exception as e:
        pass
    return None, None

def calc_media(i, f, tm):
    vals = [v for v in [i, f, tm] if v and v > 0]
    if not vals: return None
    return round(sum(vals) / len(vals), 2)

with open(JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

print(f"Total sèries: {len(data)}")
updated_score = 0
updated_eps   = 0

for n, s in enumerate(data, 1):
    imdb_id = extract_imdb_id(s.get('u', ''))
    if not imdb_id:
        continue

    score, episodes = get_tmdb_data(imdb_id)

    changed = False
    if score and score != s.get('tm'):
        s['tm'] = score
        updated_score += 1
        changed = True
    if episodes and episodes != s.get('e'):
        s['e'] = episodes
        updated_eps += 1
        changed = True

    # Recalculate media
    new_media = calc_media(s.get('i'), s.get('f'), s.get('tm'))
    if new_media:
        s['m'] = new_media

    status = '✓' if changed else '·'
    score_str = f" tm:{score}" if score else ""
    eps_str   = f" ep:{episodes}" if episodes else ""
    print(f"[{n:4}/{len(data)}] {status}{score_str}{eps_str} {s['t'][:50]}")
    time.sleep(0.05)

    if n % 200 == 0:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',',':'))
        print(f"  → Guardat ({updated_score} punts, {updated_eps} ep actualitzats)\n")

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',',':'))

print(f"\n✅ Fi: {updated_score} puntuacions TMDB, {updated_eps} episodis actualitzats")
