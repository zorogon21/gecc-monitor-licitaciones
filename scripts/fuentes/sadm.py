# -*- coding: utf-8 -*-
"""
sadm.py — Fuente: Licitaciones Públicas de Compras de Servicios de Agua y
Drenaje de Monterrey, I.P.D. (SADM).

https://www.sadm.gob.mx/SADM/index.jsp?id_html=licit_pub_compras es HTML
estático (no requiere navegador) con enlaces a los PDFs de bases de cada
concurso, con clave SADM-GCS-COP-NNN-AAAA. A diferencia de las demás
fuentes, esta página NO expone fecha de publicación ni fecha límite en
ningún lado del HTML (ni tabla, ni texto de vigencia) — se dejan vacías
en vez de inventarlas.

El título tampoco es confiable la mayoría de las veces: solo algunos
nombres de archivo incluyen una descripción del objeto (ej.
"...COP-006-2023_SUMINISTRO_DE_MEDIDORES_DE_CHORRO_MULTIPLE.pdf"); el
resto son solo la clave sin descripción (ej.
"BASES_SADM-GCS-COP-032-2026.pdf"). Cuando no hay descripción en el
nombre del archivo, el título queda como la sola clave — clasificar() en
ese caso probablemente no encuentre ninguna categoría de negocio, lo cual
es el comportamiento correcto (no se puede clasificar lo que no se puede
leer), en vez de forzar una coincidencia.

Se incluye esta fuente a pesar de estas limitaciones porque cubre
licitaciones de medidores de agua, relevantes para GECC.
"""

import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://www.sadm.gob.mx/SADM/index.jsp?id_html=licit_pub_compras"
REQUEST_TIMEOUT = 30
FUENTE = "Licitaciones Públicas de Compras — SADM"
COMPRADOR = "Servicios de Agua y Drenaje de Monterrey, I.P.D."
UBICACION = "Nuevo León"

ENLACE_RE = re.compile(
    r'href="(https://www\.sadm\.gob\.mx/SADM/archivos/uploaded_files/'
    r'((?:BASES|Convocatoria|CONVOCATORIA)[^"]*)\.pdf)"',
    re.IGNORECASE,
)
CLAVE_RE = re.compile(r"SADM-GCS-COP-\d+-\d{4}", re.IGNORECASE)
PREFIJO_RE = re.compile(r"^(BASES|Convocatoria|CONVOCATORIA)[_\-\s]*", re.IGNORECASE)


def _titulo_desde_archivo(nombre_archivo, clave):
    """
    Si el nombre de archivo trae texto extra después del prefijo (BASES_/
    Convocatoria_) y la clave (la descripción del objeto), lo usa como
    título. Si no, regresa solo la clave — nunca se inventa una
    descripción.
    """
    if not clave:
        return nombre_archivo.replace("_", " ").strip()

    resto = CLAVE_RE.sub("", nombre_archivo, count=1)
    resto = PREFIJO_RE.sub("", resto)
    resto = re.sub(r"^[_\-\sVv0-9]*", "", resto)  # tira sufijos tipo "_V2" antes de la descripción real
    resto = resto.replace("_", " ").strip()
    return f"{clave}: {resto}" if resto else clave


def obtener_licitaciones():
    """Devuelve (licitaciones, error), mismo formato que las demás fuentes."""
    req = Request(URL, headers={"User-Agent": "GECC-Monitor-Licitaciones/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError) as e:
        return [], f"Error al consultar el portal de SADM: {e}"

    licitaciones = []
    vistos = set()
    for link, nombre_archivo in ENLACE_RE.findall(html):
        if link in vistos:
            continue
        vistos.add(link)

        clave_m = CLAVE_RE.search(nombre_archivo)
        clave = clave_m.group(0) if clave_m else ""
        identificador = clave or nombre_archivo
        titulo = _titulo_desde_archivo(nombre_archivo, clave)

        licitaciones.append({
            "ocid": f"sadm-{identificador}",
            "titulo": titulo,
            "descripcion": "",
            "comprador": COMPRADOR,
            "ubicacion": UBICACION,
            "fecha_publicacion": "",
            "fecha_limite": "",
            "link": link,
            "fuente": FUENTE,
        })
    return licitaciones, None
