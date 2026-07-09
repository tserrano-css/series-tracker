#!/usr/bin/env python3
"""
Fetch Filmaffinity scores via a real browser (undetected-chromedriver).

Filmaffinity is behind Cloudflare, which blocks plain `requests` (403
"Just a moment..."). A real, non-headless Chrome passes the challenge, so
this script drives a visible browser. It reuses a single browser session
so the Cloudflare clearance cookie is kept and only the first request is slow.

Requires: pip install undetected-chromedriver selenium
(and Google Chrome installed on the system)

Usage: python fetch_filmaffinity.py
       python fetch_filmaffinity.py --chrome-version 149
"""
import json, re, sys, time
from urllib.parse import quote

import undetected_chromedriver as uc

JSON_PATH = 'C:/TSS/proyectos/series-tracker/series.json'

# Chrome major version. Override with --chrome-version N if uc downloads the
# wrong driver (error "only supports Chrome version X / current is Y").
CHROME_VERSION = None
if '--chrome-version' in sys.argv:
    CHROME_VERSION = int(sys.argv[sys.argv.index('--chrome-version') + 1])

sys.stdout.reconfigure(encoding='utf-8')


def _new_chrome(version_main):
    options = uc.ChromeOptions()
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    return uc.Chrome(options=options, version_main=version_main)


def make_driver():
    try:
        return _new_chrome(CHROME_VERSION)
    except Exception as e:
        # Recover from "only supports Chrome version X / current is Y" by
        # parsing the actual installed version and retrying with it.
        m = re.search(r'Current browser version is (\d+)', str(e))
        if m:
            ver = int(m.group(1))
            print(f'  Ajustant driver a Chrome {ver}…')
            return _new_chrome(ver)
        raise


def extract_score(html):
    m = re.search(r'itemprop="ratingValue"[^>]*content="([\d.]+)"', html)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _on_cloudflare(html):
    low = html.lower()
    return 'just a moment' in low or 'challenge-platform' in low or 'cf-challenge' in low


def poll_page(driver, checker, tries=8, wait=1.5):
    """Poll driver.page_source until `checker(html)` returns non-None, waiting
    while Cloudflare's 'Just a moment…' interstitial is still up. Returns the
    checker's value, or None if it never appeared within tries*wait seconds."""
    for _ in range(tries):
        html = driver.page_source
        if not _on_cloudflare(html):
            val = checker(html)
            if val is not None:
                return val
        time.sleep(wait)
    return checker(driver.page_source)


def imdb_score(driver, imdb_url):
    """Fetch the IMDB rating from an IMDB title URL (real browser bypasses 503)."""
    def _score(html):
        m = re.search(r'"aggregateRating":\{[^}]*"ratingValue":([\d.]+)', html)
        return float(m.group(1)) if m else None
    try:
        driver.get(imdb_url)
        time.sleep(1.5)
        return poll_page(driver, _score)
    except Exception as e:
        print(f'  Error: {e}')
    return None


def parse_results(html):
    """Return list of (film_id, year|None) from a Filmaffinity search page,
    in the order they appear. Each result is a `se-it` block."""
    results = []
    for block in html.split('se-it')[1:]:
        link = re.search(r'/es/(film\d+\.html)', block)
        if not link:
            continue
        year = re.search(r'ye-w[^>]*>\s*(\d{4})', block)
        results.append((link.group(1), int(year.group(1)) if year else None))
    return results


def pick_best(results, year):
    """Choose the result whose year matches `year` (exact, else within ±1),
    otherwise fall back to the first result."""
    if not results:
        return None
    if year:
        for fid, y in results:
            if y == year:
                return fid
        for fid, y in results:
            if y and abs(y - year) <= 1:
                return fid
    return results[0][0]


def score_from_url(driver, fa_url):
    """Fetch the score directly from a known Filmaffinity film URL."""
    try:
        driver.get(fa_url)
        time.sleep(1)
        return poll_page(driver, extract_score)
    except Exception as e:
        print(f'  Error: {e}')
    return None


def search_score(driver, title, year=None):
    """Search Filmaffinity by title, pick the best result by year.
    Returns (score, film_url) — film_url is None if nothing was found."""
    try:
        url = f'https://www.filmaffinity.com/es/search.php?stext={quote(title)}&stype=title'
        driver.get(url)
        time.sleep(1)

        # Wait past Cloudflare until the page is either a film sheet (has a
        # score) or a results list (has result blocks).
        def _ready(html):
            if extract_score(html) is not None:
                return 'film'
            if parse_results(html):
                return 'results'
            return None
        poll_page(driver, _ready)
        html = driver.page_source

        # Case 1: the search redirected straight to a single film page
        score = extract_score(html)
        if score is not None:
            return score, driver.current_url

        # Case 2: results page — pick best match by year, then visit it
        fid = pick_best(parse_results(html), year)
        if fid:
            film_url = f'https://www.filmaffinity.com/es/{fid}'
            driver.get(film_url)
            time.sleep(1)
            return poll_page(driver, extract_score), film_url
    except Exception as e:
        print(f'  Error: {e}')
    return None, None


def calc_media(i, f, tm):
    vals = [v for v in [i, f, tm] if v and v > 0]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


def main():
    # --refresh: re-fetch every series that already has a stored FA url,
    #            updating its score (fast, goes straight to the url).
    # default:   only fill series that don't have a score yet.
    refresh = '--refresh' in sys.argv

    with open(JSON_PATH, encoding='utf-8') as fp:
        data = json.load(fp)

    if refresh:
        work = [(i, s) for i, s in enumerate(data) if s.get('fu')]
        print(f'Refrescant puntuacions via URL guardada: {len(work)}')
    else:
        work = [(i, s) for i, s in enumerate(data) if not s.get('f')]
        print(f'Series sense puntuació Filmaffinity: {len(work)}')
    if not work:
        return

    print('Obrint navegador (es passarà el repte de Cloudflare)…')
    driver = make_driver()

    updated = errors = 0
    try:
        for n, (i, s) in enumerate(work, 1):
            fa_url = s.get('fu')
            if fa_url:
                # Known URL → fetch directly, no search needed
                score = score_from_url(driver, fa_url)
                found_url = fa_url
                tag = '↗'
            else:
                # Unknown → search by title, disambiguate by year, save the url
                score, found_url = search_score(driver, s['t'], s.get('yr'))
                tag = '🔍'

            if score:
                data[i]['f'] = score
                if found_url:
                    data[i]['fu'] = found_url
                data[i]['m'] = calc_media(data[i].get('i'), score, data[i].get('tm'))
                updated += 1
                status = f'✓ {score}'
            else:
                errors += 1
                status = '✗'
            print(f"[{n:4}/{len(work)}] {tag} {status} {s['t'][:52]}")

            if n % 25 == 0:
                with open(JSON_PATH, 'w', encoding='utf-8') as fp:
                    json.dump(data, fp, ensure_ascii=False, separators=(',', ':'))
                print(f'  → Guardat ({updated} actualitzats fins ara)\n')
    finally:
        driver.quit()

    with open(JSON_PATH, 'w', encoding='utf-8') as fp:
        json.dump(data, fp, ensure_ascii=False, separators=(',', ':'))

    print(f'\n✅ Fi: {updated} puntuacions actualitzades, {errors} no trobades')


if __name__ == '__main__':
    main()
