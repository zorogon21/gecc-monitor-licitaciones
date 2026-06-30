# -*- coding: utf-8 -*-
"""
apaseo_el_grande.py — Fuente: Licitaciones del Municipio de Apaseo el
Grande, Gto.

El sitio (WordPress) no tiene una página de archivo navegable para
licitaciones, pero expone la API REST estándar de WordPress
(/wp-json/wp/v2/posts), que sí está habilitada. Se usa el parámetro
'search' para encontrar los posts de licitación (su título siempre
incluye "LICITACIÓN" o el folio "MAG/LPN/..."). Cada post trae las bases
completas como HTML (no solo un PDF), incluyendo la fecha del "Acto de
presentación y apertura de ofertas", que es la fecha límite real — se
extrae con una expresión regular del texto del post.
"""

import json
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://apaseoelgrande.gob.mx/wp-json/wp/v2/posts"
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones — Municipio de Apaseo el Grande"
COMPRADOR = "Municipio de Apaseo el Grande, Guanajuato"
UBICACION = "Guanajuato"

TAG_RE = re.compile(r"<[^>]+>")
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}
FECHA_LIMITE_RE = re.compile(
    r"(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚ]+)\s+DE\s+(\d{4})",
    re.IGNORECASE,
)


def _quitar_tags(html_fragmento):
    texto = TAG_RE.sub(" ", html_fragmento or "")
    return re.sub(r"\s+", " ", texto).strip()


def _extraer_fecha_limite(texto_plano):
    """
    Busca la fecha que acompaña a 'presentación y apertura de ofertas' (el
    acto que marca el cierre real de la licitación). Si no se encuentra esa
    frase, no se adivina con cualquier fecha del documento para evitar
    falsos positivos.
    """
    idx = texto_plano.lower().find("presentaci")
    if idx == -1:
        return ""
    ventana = texto_plano[idx:idx + 200]
    m = FECHA_LIMITE_RE.search(ventana.upper())
    if not m:
        return ""
    dia, mes_txt, anio = m.groups()
    mes = MESES.get(mes_txt.lower())
    if not mes:
        return ""
    try:
        return datetime(int(anio), mes, int(dia), tzinfo=timezone.utc).isoformat()
    except ValueError:
        return ""


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    params = urlencode({
        "search": "LICITACI",
        "per_page": 50,
        "_fields": "id,date,link,title,content",
    })
    req = Request(
        f"{API}?{params}",
        headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"},
    )
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            posts = json.loads(resp.read())
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
        return [], f"Error al consultar la API de Apaseo el Grande: {e}"

    licitaciones = []
    for post in posts:
        try:
            titulo = _quitar_tags(post.get("title", {}).get("rendered", ""))
            contenido = _quitar_tags(post.get("content", {}).get("rendered", ""))
            fecha_publicacion = post.get("date", "")
            if fecha_publicacion and not fecha_publicacion.endswith("Z") and "+" not in fecha_publicacion:
                fecha_publicacion += "Z"  # la API regresa hora local sin sufijo de zona

            licitaciones.append({
                "ocid": f"apgrande-{post.get('id')}",
                "titulo": titulo,
                "descripcion": contenido[:500],
                "comprador": COMPRADOR,
                "ubicacion": UBICACION,
                "fecha_publicacion": fecha_publicacion,
                "fecha_limite": _extraer_fecha_limite(contenido),
                "link": post.get("link", ""),
                "fuente": FUENTE,
            })
        except Exception:
            continue
    return licitaciones, None
