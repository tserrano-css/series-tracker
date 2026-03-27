#!/usr/bin/env python3
"""
Regenera series.json a partir del Excel Series.xlsx.
Uso: python update_data.py
     python update_data.py ruta/al/Series.xlsx
"""

import json
import sys
import os
import pandas as pd

def main():
    # Ruta al Excel
    xlsx_path = sys.argv[1] if len(sys.argv) > 1 else "Series.xlsx"

    if not os.path.exists(xlsx_path):
        print(f"❌ No se encuentra el fichero: {xlsx_path}")
        sys.exit(1)

    print(f"📂 Leyendo {xlsx_path}...")
    df = pd.read_excel(xlsx_path, sheet_name='Series')

    series_list = []
    for _, row in df.iterrows():
        vista_val = str(row.get('Vista', '')).strip() if pd.notna(row.get('Vista')) else ''
        vista = vista_val.lower() in ['si', 'sí', 'ahora']
        watching = vista_val.lower() == 'ahora'

        imdb = float(row['IMDB']) if pd.notna(row.get('IMDB')) else None
        fa_raw = row.get('Filmaffinity')
        fa = float(fa_raw) if pd.notna(fa_raw) and float(fa_raw) > 0 else None
        media_raw = row.get('Media')
        media = float(media_raw) if pd.notna(media_raw) and float(media_raw) > 0 else None
        episodes = int(row['# episiodios']) if pd.notna(row.get('# episiodios')) else None
        animacion = str(row.get('Animación', '')).strip().lower() == 'si' if pd.notna(row.get('Animación')) else False

        estreno_raw = row.get('Estreno')
        estreno = str(estreno_raw).strip() if pd.notna(estreno_raw) else ''
        if estreno and estreno != 'nan':
            if '2026' in estreno or '2025' in estreno or '-' in estreno:
                estreno = estreno[:10] if len(estreno) > 10 else estreno
            else:
                estreno = ''
        else:
            estreno = ''

        segunda = str(row.get('2a temp. disp.', '')).strip() if pd.notna(row.get('2a temp. disp.')) else ''
        segunda = '' if segunda in ['nan', 'NaN'] else segunda
        notas = str(row.get('Columna1', '')).strip() if pd.notna(row.get('Columna1')) else ''
        notas = '' if notas in ['nan', 'NaN'] else notas

        series_list.append({
            't': str(row['Serie']).strip(),
            'u': str(row.get('URL', '')).strip() if pd.notna(row.get('URL')) else '',
            'p': str(row.get('Plataforma', '')).strip() if pd.notna(row.get('Plataforma')) else '',
            'i': imdb, 'f': fa, 'm': media,
            'v': vista, 'w': watching, 'a': animacion,
            'e': episodes, 'es': estreno, 's': segunda, 'n': notas,
        })

    output_path = os.path.join(os.path.dirname(xlsx_path), 'series.json')
    with open(output_path, 'w', encoding='utf-8') as fp:
        json.dump(series_list, fp, ensure_ascii=False, separators=(',', ':'))

    print(f"✅ series.json generado con {len(series_list)} series → {output_path}")

if __name__ == '__main__':
    main()
