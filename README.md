# Series Tracker

Web personal para gestionar mi colección de series.

## Estructura del proyecto

```
series-tracker/
├── index.html               ← La web (incluye modo admin con GitHub API)
├── series.json              ← Datos de las series (generado/actualizado por los scripts)
├── update_data.py           ← Regenera series.json desde Series.xlsx
├── fetch_posters.py         ← Rellena posters (campo g) vía TMDB
├── fetch_years.py           ← Rellena año de inicio (campo yr) vía TMDB
├── fetch_tmdb_ids.py        ← Rellena ID de TMDB (campos tmid/tmtype) para enlaces directos
├── fetch_tmdb_scores.py     ← Rellena puntuación TMDB (campo tm) y episodios (campo e)
├── fetch_filmaffinity.py    ← Rellena puntuación Filmaffinity (campo f) y su URL (campo fu)
├── local_server.py          ← Servidor local: sirve la web + lanza scripts desde el navegador
├── Series.xlsx              ← Tu Excel (no subir a GitHub si quieres privacidad)
└── README.md
```

## Ver la web en local

Como `index.html` carga `series.json` via `fetch()`, necesita un servidor local:

```bash
# Opción 1: local_server.py (recomendado)
python local_server.py
# Abrir http://localhost:8080
```

`local_server.py` sirve los ficheros estáticos **y** expone endpoints locales que
permiten actualizar puntuaciones de IMDb y Filmaffinity desde la propia web usando un
navegador real (ver más abajo). Con el simple `python -m http.server 8080` la web
funciona igual, pero esos botones de IMDb/Filmaffinity no estarán disponibles.

## Scripts de datos (Python)

Todos los scripts de `fetch_*.py` son **idempotentes**: sólo rellenan campos vacíos
(no sobrescriben datos ya existentes) y guardan progreso cada 100-200 series por si
se interrumpen a mitad. Se ejecutan una sola vez desde tu PC — no forman parte de la
web pública.

### `update_data.py` — Regenerar desde Excel
Lee `Series.xlsx` (hoja `Series`) y reconstruye `series.json` desde cero, preservando
los posters (`g`) ya existentes por título/URL. Úsalo cuando edites el Excel maestro.

```bash
python update_data.py [ruta/al/Series.xlsx]
```

### `fetch_posters.py` — Posters (TMDB)
Busca el poster de cada serie sin campo `g`, usando el IMDB ID extraído de la URL
(`u`) contra la API `find` de TMDB. Requiere API key de TMDB.

```bash
python fetch_posters.py <TMDB_API_KEY>
```

### `fetch_years.py` — Año de inicio (TMDB)
Rellena el campo `yr` (año de estreno/primera emisión) para las series que no lo
tienen, vía TMDB. Se muestra en la web junto al título: `Arcane (2021)`.

```bash
python fetch_years.py [TMDB_API_KEY]
```

### `fetch_tmdb_ids.py` — IDs de TMDB
Rellena `tmid` (ID numérico) y `tmtype` (`tv` o `movie`) para poder enlazar
directamente a la ficha de TMDB desde la web, y para que el botón de admin
"Actualizar puntuaciones" pueda hacer fetch directo sin tener que re-buscar.

```bash
python fetch_tmdb_ids.py [TMDB_API_KEY]
```

### `fetch_tmdb_scores.py` — Puntuación TMDB y episodios
Rellena `tm` (puntuación TMDB) y actualiza `e` (número de episodios) para **todas**
las series (no sólo las vacías, refresca todas). Recalcula la media `m` con las
puntuaciones disponibles (IMDB + Filmaffinity + TMDB). Es el equivalente en línea de
comandos del botón de admin **🔄 Actualizar puntuaciones** de la web.

```bash
python fetch_tmdb_scores.py [TMDB_API_KEY]
```

### `fetch_filmaffinity.py` — Puntuación Filmaffinity (navegador real)
Filmaffinity no tiene API pública y está protegido por **Cloudflare**, que bloquea
las peticiones con `requests` (403 "Just a moment…"). Para saltárselo, este script
usa **undetected-chromedriver**, que controla un Chrome real (visible, no headless —
en modo headless Cloudflare lo detecta). Reutiliza una única sesión de navegador, así
que sólo la primera petición pasa por el reto de Cloudflare y el resto van rápidas.

Para cada serie sin nota (`f`):
1. Busca por título en Filmaffinity.
2. **Desambigua por año**: de los resultados, elige el que coincide con el año de
   inicio (`yr`, exacto o ±1), no simplemente el primero — así distingue homónimos
   (p.ej. sèrie vs película, o dos series del mismo nombre de años distintos).
3. Extrae la nota (`itemprop="ratingValue"`) y **guarda la URL de Filmaffinity** en
   el campo `fu`.

En ejecuciones posteriores, si la serie ya tiene `fu`, va **directo a esa URL** sin
volver a buscar (más rápido y sin riesgo de match incorrecto).

```bash
pip install undetected-chromedriver selenium   # requiere Chrome instalado
python fetch_filmaffinity.py
# Refrescar la nota de TODAS las series que ya tienen URL guardada (vía fu):
python fetch_filmaffinity.py --refresh
# Si da error de versión de driver, forzar la de tu Chrome:
python fetch_filmaffinity.py --chrome-version 149
```

> **Nota:** IMDB bloquea las peticiones con `requests` (`503 Forbidden`), pero el
> mismo truco de navegador real sí funciona. La nota de IMDb no se rellena desde este
> script sino desde el botón del formulario de edición de la web (ver la sección de
> `local_server.py` más abajo).

### Orden recomendado tras regenerar el Excel

```bash
python update_data.py
python fetch_posters.py <TMDB_API_KEY>
python fetch_years.py <TMDB_API_KEY>
python fetch_tmdb_ids.py <TMDB_API_KEY>
python fetch_tmdb_scores.py <TMDB_API_KEY>
python fetch_filmaffinity.py
git add series.json
git commit -m "Actualizar series"
git push
```

## Modo admin (editar desde la web)

Haciendo 5 clics rápidos sobre el logo se activa el modo admin, que permite editar,
añadir y eliminar series directamente desde el navegador, sin tocar el Excel. Los
cambios se guardan en `series.json` vía la API de GitHub (necesita un Personal Access
Token con permiso de escritura sobre el repo, se pide y se guarda en `localStorage`
la primera vez).

El botón **🔄 Actualizar puntuaciones** de la barra de admin hace lo mismo que
`fetch_tmdb_scores.py` pero desde el propio navegador (TMDB sí permite peticiones
CORS desde JavaScript), pidiendo tu TMDB API key la primera vez.

## `local_server.py` — actualizar IMDb/Filmaffinity desde la web

TMDB se puede consultar directamente desde el navegador (permite CORS), pero IMDb y
Filmaffinity lo bloquean. Para poder actualizarlos también desde la web, `local_server.py`
—además de servir los ficheros— mantiene abierta **una sesión de navegador real**
(undetected-chromedriver) y expone estos endpoints locales:

- `POST /run-script { name: 'filmaffinity' }` y `GET /script-status` — lanzan y
  monitorizan `fetch_filmaffinity.py` en segundo plano.
- `GET /fetch-scores?imdb_url=&title=&year=&fa_url=` — devuelve la nota de IMDb y de
  Filmaffinity (y la URL de FA encontrada) de una sola serie.

Con la web abierta vía `local_server.py`, en modo admin aparecen:

- **🔄 Actualizar puntuaciones i episodis** (dentro del formulario de edición de cada
  serie): rellena TMDB + episodios (vía navegador), e IMDb + Filmaffinity + URL de FA
  (vía `/fetch-scores`), recalcula la media y muestra un resumen de lo que cambió.
- **🎬 Actualitzar Filmaffinity** (barra de admin): lanza `fetch_filmaffinity.py` para
  todas las series que faltan, mostrando el progreso en directo.

Estos botones sólo aparecen/funcionan cuando la web se sirve desde `localhost` con
`local_server.py`; en GitHub Pages sólo está disponible la actualización de TMDB.

## Publicar en GitHub Pages

1. Ve a tu repositorio en GitHub
2. **Settings** → **Pages**
3. Source: `Deploy from branch` → rama `main` → carpeta `/root`
4. Guardar

La web estará disponible en:
`https://TU_USUARIO.github.io/series-tracker`

## Dependencias de los scripts Python

```bash
pip install pandas openpyxl requests
# Sólo para fetch_filmaffinity.py (requiere Chrome instalado):
pip install undetected-chromedriver selenium
```
