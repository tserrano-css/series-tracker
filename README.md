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
├── fetch_filmaffinity.py    ← Rellena puntuación Filmaffinity (campo f) vía scraping
├── Series.xlsx              ← Tu Excel (no subir a GitHub si quieres privacidad)
└── README.md
```

## Ver la web en local

Como `index.html` carga `series.json` via `fetch()`, necesita un servidor local:

```bash
# Opción 1: Python (recomendado)
python -m http.server 8000
# Abrir http://localhost:8000

# Opción 2: Node.js
npx serve .
```

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

### `fetch_filmaffinity.py` — Puntuación Filmaffinity (scraping)
Filmaffinity no tiene API pública ni cabeceras CORS, así que no se puede llamar desde
el navegador — sólo funciona vía scraping local. Busca cada serie sin campo `f` por
título en Filmaffinity y extrae la nota media de la ficha. Incluye una pausa de ~0.8s
entre peticiones para no saturar el servidor.

```bash
python fetch_filmaffinity.py
```

> **Nota:** IMDB tampoco se puede actualizar automáticamente — su web devuelve
> `503 Forbidden` ante peticiones automatizadas (protección anti-bot), así que ese
> campo (`i`) sólo se puede editar manualmente desde el formulario de edición de la web.

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
```
