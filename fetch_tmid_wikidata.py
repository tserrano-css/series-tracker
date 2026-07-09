#!/usr/bin/env python3
"""
Omple tmid/tmtype de TMDB a partir de l'id d'IMDb, SENSE cap API key,
consultant Wikidata (P345 = IMDB id → P4983 sèrie / P4947 pel·lícula).

A diferència de fetch_tmdb_ids.py (que usa l'API de TMDB i necessita key),
això no requereix cap credencial i consulta Wikidata per lots.

Usage: python fetch_tmid_wikidata.py
"""
import json, os, re, sys, time
import requests

sys.stdout.reconfigure(encoding='utf-8')

# series.json és al costat d'aquest script (dins del repo)
JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'series.json')
SPARQL_URL = 'https://query.wikidata.org/sparql'
HEADERS = {
    'Accept': 'application/sparql-results+json',
    'User-Agent': 'series-tracker/1.0 (https://github.com/tserrano-css/series-tracker)',
}
BATCH = 50   # ids d'IMDb per consulta


def imdb_id(url):
    m = re.search(r'tt\d+', str(url))
    return m.group(0) if m else None


def query_batch(ids):
    """Retorna {imdb_id: (tmid, tmtype)} per als ids trobats a Wikidata."""
    values = ' '.join(f'"{i}"' for i in ids)
    sparql = (
        'SELECT ?imdb ?tv ?movie WHERE { '
        f'VALUES ?imdb {{ {values} }} '
        '?item wdt:P345 ?imdb. '
        'OPTIONAL { ?item wdt:P4983 ?tv. } '
        'OPTIONAL { ?item wdt:P4947 ?movie. } }'
    )
    r = requests.get(SPARQL_URL, params={'format': 'json', 'query': sparql},
                     headers=HEADERS, timeout=60)
    r.raise_for_status()
    out = {}
    for b in r.json()['results']['bindings']:
        imdb = b['imdb']['value']
        if imdb in out:
            continue  # ja resolt per una fila anterior
        if 'tv' in b:
            out[imdb] = (int(b['tv']['value']), 'tv')
        elif 'movie' in b:
            out[imdb] = (int(b['movie']['value']), 'movie')
    return out


def main():
    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)

    missing = []
    for i, s in enumerate(data):
        if s.get('tmid'):
            continue
        iid = imdb_id(s.get('u', ''))
        if iid:
            missing.append((i, iid, s.get('t', '')))

    print(f'Sèries sense tmid (amb id IMDb): {len(missing)}')
    if not missing:
        return

    updated = notfound = 0
    for start in range(0, len(missing), BATCH):
        chunk = missing[start:start + BATCH]
        ids = [iid for _, iid, _ in chunk]
        try:
            found = query_batch(ids)
        except Exception as e:
            print(f'  Error al lot {start}: {e}')
            time.sleep(3)
            continue
        for i, iid, title in chunk:
            if iid in found:
                tmid, tmtype = found[iid]
                data[i]['tmid'] = tmid
                data[i]['tmtype'] = tmtype
                updated += 1
                print(f'  ✓ {tmtype}/{tmid}  {title[:50]}')
            else:
                notfound += 1
                print(f'  ✗ (no a Wikidata)  {title[:50]}')
        # Desa progrés després de cada lot
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        time.sleep(1)  # cortesia amb Wikidata

    print(f'\n✅ Fi: {updated} tmid afegits, {notfound} no trobats a Wikidata')


if __name__ == '__main__':
    main()
