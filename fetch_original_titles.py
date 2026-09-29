#!/usr/bin/env python3
"""Omple el camp `ot` (títol original) de totes les sèries des de TMDB.

Fa servir el tmid/tmtype ja desat quan hi és (la majoria de sèries, gràcies
a fetch_tmid_wikidata.py); per a la resta, el resol primer via /find amb
l'id d'IMDb, igual que fan fetch_tmdb_ids.py / fetch_tmdb_scores.py.

Usage: python fetch_original_titles.py [TMDB_API_KEY]
       python fetch_original_titles.py --refresh   # torna a comprovar TOTES,
                                                     # no només les que no en tenen
"""
import json, os, re, sys, time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_KEY   = next((a for a in sys.argv[1:] if not a.startswith('--')), '844a662a1a742649db465e65709da7b4')
REFRESH   = '--refresh' in sys.argv
JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'series.json')
TMDB_BASE = 'https://api.themoviedb.org/3'


def extract_imdb_id(url):
    m = re.search(r'tt\d+', str(url))
    return m.group(0) if m else None


def resolve_tmid(imdb_id):
    """Igual que als altres scripts: /find per imdb_id -> (tmid, tmtype)."""
    try:
        r = requests.get(f'{TMDB_BASE}/find/{imdb_id}',
                          params={'api_key': API_KEY, 'external_source': 'imdb_id'},
                          timeout=10)
        if r.status_code == 429:
            time.sleep(2); return resolve_tmid(imdb_id)
        if r.status_code != 200:
            return None, None
        d = r.json()
        for key, kind in [('tv_results', 'tv'), ('movie_results', 'movie')]:
            results = d.get(key, [])
            if results:
                return results[0]['id'], kind
    except Exception:
        pass
    return None, None


def get_original_title(tmid, tmtype):
    try:
        r = requests.get(f'{TMDB_BASE}/{tmtype}/{tmid}', params={'api_key': API_KEY}, timeout=10)
        if r.status_code == 429:
            time.sleep(2); return get_original_title(tmid, tmtype)
        if r.status_code != 200:
            return None
        d = r.json()
        return d.get('original_name') or d.get('original_title')
    except Exception:
        return None


def main():
    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)

    work = [(i, s) for i, s in enumerate(data) if REFRESH or not s.get('ot')]
    print(f"Sèries a processar: {len(work)} de {len(data)}"
          f"{' (--refresh: totes)' if REFRESH else ' (només sense títol original)'}")

    updated = notfound = 0
    for n, (i, s) in enumerate(work, 1):
        tmid, tmtype = s.get('tmid'), s.get('tmtype')
        if not tmid:
            imdb_id = extract_imdb_id(s.get('u', ''))
            if imdb_id:
                tmid, tmtype = resolve_tmid(imdb_id)
                if tmid:
                    data[i]['tmid'], data[i]['tmtype'] = tmid, tmtype

        ot = get_original_title(tmid, tmtype) if tmid and tmtype else None
        if ot and ot != s.get('ot'):
            data[i]['ot'] = ot
            updated += 1
            print(f"[{n:4}/{len(work)}] ✓ {ot[:50]}  ({s['t'][:40]})")
        else:
            notfound += 1
            print(f"[{n:4}/{len(work)}] ✗ {s['t'][:50]}")
        time.sleep(0.05)

        if n % 200 == 0:
            with open(JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            print(f"  → Guardat ({updated} actualitzats fins ara)\n")

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"\n✅ Fi: {updated} títols originals afegits, {notfound} no trobats")


if __name__ == '__main__':
    main()
