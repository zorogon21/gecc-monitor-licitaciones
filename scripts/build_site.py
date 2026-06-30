# -*- coding: utf-8 -*-
"""
build_site.py — Genera index.html a partir de data/licitaciones.json.

Página estática, sin frameworks, para que sea simple de mantener. Incluye
filtros por categoría y por estado, hechos en JavaScript plano que corre
en el navegador (no necesita servidor).
"""

import json
import os
from datetime import datetime, timezone
import sys

sys.path.insert(0, os.path.dirname(__file__))
from keywords import CATEGORIES  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LICITACIONES_PATH = os.path.join(DATA_DIR, "licitaciones.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "index.html")


def formatear_fecha(fecha_iso):
    if not fecha_iso:
        return "Sin fecha especificada"
    try:
        dt = datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))
        meses = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
                 "sep", "oct", "nov", "dic"]
        return f"{dt.day} {meses[dt.month]} {dt.year}"
    except Exception:
        return fecha_iso[:10] if len(fecha_iso) >= 10 else fecha_iso


def main():
    if os.path.exists(LICITACIONES_PATH):
        with open(LICITACIONES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"licitaciones": [], "ultima_actualizacion": None}

    licitaciones = data.get("licitaciones", [])
    ultima_act = data.get("ultima_actualizacion")
    ultima_act_fmt = formatear_fecha(ultima_act) if ultima_act else "Aún no se ha ejecutado"

    tarjetas_json = []
    estados = set()
    for lic in licitaciones:
        estado = lic.get("ubicacion") or "Sin estado especificado"
        estados.add(estado)
        tarjetas_json.append({
            "ocid": lic.get("ocid", ""),
            "titulo": lic.get("titulo") or "(Sin título)",
            "descripcion": (lic.get("descripcion") or "")[:400],
            "comprador": lic.get("comprador") or "No especificado",
            "ubicacion": estado,
            "fecha_publicacion": formatear_fecha(lic.get("fecha_publicacion")),
            "fecha_limite": formatear_fecha(lic.get("fecha_limite")),
            "link": lic.get("link") or "",
            "categorias": lic.get("categorias", []),
            "fuente": lic.get("fuente", ""),
        })

    chips_categorias = "".join(
        f'<button class="chip" data-cat="{clave}" style="--chip-color:{info["color"]}">{info["label"]}</button>'
        for clave, info in CATEGORIES.items()
    )
    chips_estados = "".join(
        f'<option value="{e}">{e}</option>' for e in sorted(estados)
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GECC — Monitor de Licitaciones</title>
<style>
  :root {{
    --bg: #0f172a;
    --card-bg: #1e293b;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --border: #334155;
    --accent: #38bdf8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
  }}
  header {{ max-width: 1100px; margin: 0 auto 24px; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
  .subt {{ color: var(--text-dim); font-size: 0.9rem; }}
  .controles {{
    max-width: 1100px; margin: 0 auto 20px;
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
  }}
  .chip {{
    border: 1px solid var(--chip-color, var(--border));
    background: transparent; color: var(--chip-color, var(--text));
    padding: 6px 14px; border-radius: 999px; cursor: pointer;
    font-size: 0.85rem; transition: all 0.15s;
  }}
  .chip.activo {{ background: var(--chip-color, var(--accent)); color: #0f172a; font-weight: 600; }}
  select, input[type=text] {{
    background: var(--card-bg); color: var(--text); border: 1px solid var(--border);
    padding: 7px 12px; border-radius: 8px; font-size: 0.85rem;
  }}
  .grid {{
    max-width: 1100px; margin: 0 auto;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 16px;
  }}
  .card {{
    background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; display: flex; flex-direction: column; gap: 8px;
  }}
  .card h3 {{ margin: 0; font-size: 1rem; line-height: 1.35; }}
  .badges {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .badge {{ font-size: 0.7rem; padding: 3px 9px; border-radius: 999px; color: #0f172a; font-weight: 600; }}
  .meta {{ font-size: 0.8rem; color: var(--text-dim); }}
  .fechas {{
    display: flex; gap: 14px; font-size: 0.78rem;
    border-top: 1px solid var(--border); padding-top: 8px; margin-top: 4px;
  }}
  .fechas div b {{ display: block; color: var(--text); }}
  .desc {{ font-size: 0.83rem; color: var(--text-dim); line-height: 1.4; }}
  a.link-btn {{ margin-top: 6px; align-self: flex-start; color: var(--accent); text-decoration: none; font-size: 0.8rem; font-weight: 600; }}
  a.link-btn:hover {{ text-decoration: underline; }}
  .vacio {{ text-align: center; color: var(--text-dim); padding: 60px 20px; max-width: 1100px; margin: 0 auto; }}
  .contador {{ max-width: 1100px; margin: 0 auto 12px; font-size: 0.85rem; color: var(--text-dim); }}
</style>
</head>
<body>
<header>
  <h1>📋 GECC — Monitor de Licitaciones</h1>
  <div class="subt">Última actualización: {ultima_act_fmt} · Se actualiza automáticamente cada 2 horas</div>
</header>

<div class="controles">
  {chips_categorias}
  <select id="filtroEstado">
    <option value="">Todos los estados</option>
    {chips_estados}
  </select>
  <input type="text" id="buscador" placeholder="Buscar por palabra...">
</div>

<div class="contador" id="contador"></div>
<div class="grid" id="grid"></div>
<div class="vacio" id="vacio" style="display:none">No hay licitaciones que coincidan con el filtro actual.</div>

<script>
const LICITACIONES = {json.dumps(tarjetas_json, ensure_ascii=False)};
const CATEGORIAS = {json.dumps(CATEGORIES, ensure_ascii=False)};

let filtroCategoria = null;
let filtroEstado = "";
let filtroTexto = "";

function render() {{
  const grid = document.getElementById('grid');
  const vacio = document.getElementById('vacio');
  const contador = document.getElementById('contador');
  grid.innerHTML = '';

  const filtradas = LICITACIONES.filter(l => {{
    if (filtroCategoria && !l.categorias.includes(filtroCategoria)) return false;
    if (filtroEstado && l.ubicacion !== filtroEstado) return false;
    if (filtroTexto) {{
      const t = (l.titulo + ' ' + l.descripcion + ' ' + l.comprador).toLowerCase();
      if (!t.includes(filtroTexto.toLowerCase())) return false;
    }}
    return true;
  }});

  contador.textContent = filtradas.length + ' licitacion(es) encontradas de ' + LICITACIONES.length + ' totales detectadas';

  if (filtradas.length === 0) {{
    vacio.style.display = 'block';
    return;
  }}
  vacio.style.display = 'none';

  for (const l of filtradas) {{
    const badges = l.categorias.map(c => {{
      const info = CATEGORIAS[c];
      return `<span class="badge" style="background:${{info.color}}">${{info.label}}</span>`;
    }}).join('');

    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="badges">${{badges}}</div>
      <h3>${{l.titulo}}</h3>
      <div class="meta">🏛️ ${{l.comprador}} &nbsp;·&nbsp; 📍 ${{l.ubicacion}}</div>
      <div class="desc">${{l.descripcion}}</div>
      <div class="fechas">
        <div>Publicación<b>${{l.fecha_publicacion}}</b></div>
        <div>Fecha límite / bases<b>${{l.fecha_limite}}</b></div>
      </div>
      ${{l.link ? `<a class="link-btn" href="${{l.link}}" target="_blank" rel="noopener">Ver convocatoria completa →</a>` : ''}}
    `;
    grid.appendChild(card);
  }}
}}

document.querySelectorAll('.chip').forEach(chip => {{
  chip.addEventListener('click', () => {{
    const cat = chip.dataset.cat;
    if (filtroCategoria === cat) {{
      filtroCategoria = null;
      chip.classList.remove('activo');
    }} else {{
      document.querySelectorAll('.chip').forEach(c => c.classList.remove('activo'));
      filtroCategoria = cat;
      chip.classList.add('activo');
    }}
    render();
  }});
}});

document.getElementById('filtroEstado').addEventListener('change', e => {{
  filtroEstado = e.target.value;
  render();
}});

document.getElementById('buscador').addEventListener('input', e => {{
  filtroTexto = e.target.value;
  render();
}});

render();
</script>
</body>
</html>
"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html generado con {len(tarjetas_json)} licitaciones.")


if __name__ == "__main__":
    main()
