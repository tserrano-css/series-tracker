#!/usr/bin/env python3
"""
Fetch Filmaffinity score via scraping (search by title, take best match).
Filmaffinity has no public API and no CORS, so this must run locally.
Usage: python fetch_filmaffinity.py
"""
import json, re, sys, time
import requests
from urllib.parse import quote

sys.stdout.reconfigure(encoding='utf-8')

JSON_PATH = 'C:/TSS/proyectos/series-tracker/series.json'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9',
}

def search_score(title):
    try:
        url = f'https://www.filmaffinity.com/es/search.php?stext={quote(title)}&stype=title'
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        # Direct redirect to a film page (single result)
        m = re.search(r'<div id="movie-rat-avg"[^>]*>([\d,]+)</div>', r.text)
        if m:
            return float(m.group(1).replace(',', '.'))
        # Search results page: take first result link and follow it
        link = re.search(r'<a href="(https://www\.filmaffinity\.com/es/film\d+\.html)"', r.text)
        if link:
            r2 = requests.get(link.group(1), headers=HEADERS, timeout=15)
            m2 = re.search(r'<div id="movie-rat-avg"[^>]*>([\d,]+)</div>', r2.text)
            if m2:
                return float(m2.group(1).replace(',', '.'))
    except Exception:
        pass
    return None

def calc_media(i, f, tm):
    vals = [v for v in [i, f, tm] if v and v > 0]
    if not vals: return None
    return round(sum(vals) / len(vals), 2)

with open(JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

missing = [(i, s) for i, s in enumerate(data) if not s.get('f')]
print(f"Series sense puntuació Filmaffinity: {len(missing)}")

updated = 0
errors  = 0

for n, (i, s) in enumerate(missing, 1):
    score = search_score(s['t'])
    if score:
        data[i]['f'] = score
        data[i]['m'] = calc_media(data[i].get('i'), score, data[i].get('tm'))
        updated += 1
        status = f'✓ {score}'
    else:
        errors += 1
        status = '✗'
    print(f"[{n:4}/{len(missing)}] {status} {s['t'][:55]}")
    time.sleep(0.8)  # be polite, avoid rate limiting / blocking

    if n % 100 == 0:
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',',':'))
        print(f"  → Guardat ({updated} afegits fins ara)\n")

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',',':'))

print(f"\n✅ Fi: {updated} puntuacions Filmaffinity afegides, {errors} no trobades")
