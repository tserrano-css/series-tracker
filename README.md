# Series Tracker

Web personal para gestionar mi colección de series.

## Estructura del proyecto

```
series-tracker/
├── index.html        ← La web
├── series.json       ← Datos de las series (generado automáticamente)
├── update_data.py    ← Script para actualizar los datos desde Excel
├── Series.xlsx       ← Tu Excel (no subir a GitHub si quieres privacidad)
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

## Actualizar los datos

Cuando actualices el Excel, ejecuta:

```bash
python update_data.py
# o si el Excel está en otra ruta:
python update_data.py /ruta/a/Series.xlsx
```

Luego sube los cambios a GitHub:

```bash
git add series.json
git commit -m "Actualizar series"
git push
```

## Publicar en GitHub Pages

1. Ve a tu repositorio en GitHub
2. **Settings** → **Pages**
3. Source: `Deploy from branch` → rama `main` → carpeta `/root`
4. Guardar

La web estará disponible en:
`https://TU_USUARIO.github.io/series-tracker`

## Dependencias del script Python

```bash
pip install pandas openpyxl
```
