# -*- coding: utf-8 -*-
"""
guanajuato_estatal.py — Fuente: licitaciones de obra pública del Gobierno
del Estado de Guanajuato.

La página https://obrapublica.guanajuato.gob.mx/licitaciones/ pinta la
tabla con un grid de JavaScript (DevExtreme) que en realidad no calcula
nada en el navegador: simplemente hace un POST a un servicio web público
(WS_Expediente_Digital.asmx) y pinta el JSON que recibe. Por eso esta fuente
llama ese mismo servicio directamente, sin necesitar un navegador.

El servicio no expone una fecha límite de presentación de propuestas en un
campo estructurado (solo liga a PDFs por etapa: convocatoria, visita, junta
de aclaraciones, apertura, fallo), así que 'fecha_limite' se deja vacía.
"""

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = (
    "https://guanajuatoconstruye.mx/ws_netsicom/WS_Expediente_Digital/"
    "WS_Expediente_Digital.asmx/TraerLicitacionesWEB"
)
REQUEST_TIMEOUT = 30
FUENTE = "Obra Pública del Estado de Guanajuato"
COMPRADOR = "Secretaría de Obra Pública del Estado de Guanajuato"
UBICACION = "Guanajuato"


def _fecha_iso(valor):
    """Convierte el formato '/Date(epoch_ms)/' del servicio a ISO 8601."""
    if not valor or not isinstance(valor, str):
        return ""
    try:
        epoch_ms = int(valor.replace("/Date(", "").replace(")/", ""))
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()
    except (ValueError, OverflowError):
        return ""


def obtener_licitaciones():
    """
    Devuelve (licitaciones, error). 'licitaciones' es una lista de dicts con
    los mismos campos que usan las demás fuentes (titulo, descripcion,
    comprador, ubicacion, fecha_publicacion, fecha_limite, link, fuente,
    ocid). 'error' es None si todo salió bien, o un texto descriptivo si
    algo falló.
    """
    req = Request(
        ENDPOINT,
        data=b"{}",
        headers={
            "User-Agent": "GECC-Monitor-Licitaciones/1.0",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            sobre = json.loads(resp.read())
            registros = json.loads(sobre.get("d") or "[]")
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, ValueError) as e:
        return [], f"Error al consultar el servicio de Guanajuato estatal: {e}"

    licitaciones = []
    for r in registros:
        try:
            lici_id = r.get("lici_id") or r.get("ID")
            if lici_id is None:
                continue
            tipo = (r.get("TipoLicitación") or "").strip()
            clave = (r.get("lici_cve") or "").strip()
            licitaciones.append({
                "ocid": f"gto-estatal-{lici_id}",
                "titulo": (r.get("lici_nombre") or "").strip(),
                "descripcion": f"{tipo} — Clave: {clave}".strip(" —"),
                "comprador": COMPRADOR,
                "ubicacion": UBICACION,
                "fecha_publicacion": (
                    _fecha_iso(r.get("lici_fechapublicaLGT"))
                    or _fecha_iso(r.get("lici_jntaclara_fecha"))
                ),
                "fecha_limite": "",
                "link": r.get("Convocatoria") or "",
                "fuente": FUENTE,
            })
        except Exception:
            continue
    return licitaciones, None
