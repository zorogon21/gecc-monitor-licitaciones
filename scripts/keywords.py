# -*- coding: utf-8 -*-
"""
Listas de palabras y frases clave por categoría de negocio.
Se usan para clasificar licitaciones leyendo el texto completo (título +
descripción), no solo una palabra exacta. Mientras el texto contenga
CUALQUIERA de estas frases, se marca como relacionado a esa categoría.

Para ajustar la sensibilidad del agente, edita estas listas:
- Agrega frases si el agente se está perdiendo licitaciones que sabes que
  existen.
- Agrega frases a NEGATIVE_KEYWORDS si el agente está trayendo basura
  (falsos positivos) de forma repetida.
"""

CATEGORIES = {
    "alumbrado_luminarias": {
        "label": "Alumbrado público y luminarias",
        "color": "#f5a524",
        "keywords": [
            "alumbrado publico", "alumbrado público", "luminaria", "luminarias",
            "lampara led", "lámpara led", "lamparas led", "lámparas led",
            "sistema de iluminacion", "sistema de iluminación",
            "iluminacion vial", "iluminación vial", "iluminacion de calles",
            "iluminación de calles", "postes de luz", "poste de alumbrado",
            "luminaria led", "luminarias led", "infraestructura electrica vial",
            "infraestructura eléctrica vial", "modernizacion del alumbrado",
            "modernización del alumbrado", "sustitucion de luminarias",
            "sustitución de luminarias", "tecnologia led", "tecnología led",
            "equipo electromecanico", "equipo electromecánico",
            "red de alumbrado", "rehabilitacion de alumbrado",
            "rehabilitación de alumbrado", "iluminacion carretera",
            "iluminación carretera", "luminarias solares",
            "alumbrado solar", "parque luminoso",
        ],
    },
    "medidores_agua": {
        "label": "Medidores de agua / sistemas hídricos",
        "color": "#3b82f6",
        "keywords": [
            "medidor de agua", "medidores de agua", "macromedidor",
            "macromedicion", "macromedición", "micromedicion", "micromedición",
            "telemetria de agua", "telemetría de agua", "smart meter",
            "medicion inteligente", "medición inteligente",
            "sistema de medicion", "sistema de medición",
            "red de agua potable", "infraestructura hidraulica",
            "infraestructura hidráulica", "pozo de agua", "pozos de agua",
            "rehabilitacion de pozo", "rehabilitación de pozo",
            "equipo de bombeo", "planta potabilizadora",
            "plataforma de monitoreo de agua", "control de fugas de agua",
            "organismo operador de agua", "comision estatal de agua",
            "comisión estatal del agua", "gestion del agua",
            "gestión del agua",
        ],
    },
    "maquinaria_pesada": {
        "label": "Maquinaria pesada",
        "color": "#a855f7",
        "keywords": [
            "retroexcavadora", "excavadora", "bulldozer", "buldozer",
            "motoconformadora", "motoniveladora", "compactador",
            "compactadora", "cargador frontal", "minicargador",
            "rodillo vibratorio", "grua", "grúa", "lowboy", "plataforma baja",
            "camion pipa", "camión pipa", "pipa de agua", "vactor",
            "renta de maquinaria", "arrendamiento de maquinaria",
            "maquinaria de construccion", "maquinaria de construcción",
            "equipo pesado", "tractocamion", "tractocamión", "vibrocompactador",
            "retroexcavadoras", "excavadoras", "venta de maquinaria",
            "adquisicion de maquinaria", "adquisición de maquinaria",
        ],
    },
    "construccion_obra": {
        "label": "Construcción y obra civil",
        "color": "#10b981",
        "keywords": [
            "pavimentacion", "pavimentación", "construccion de calle",
            "construcción de calle", "construccion de calles",
            "construcción de calles", "rehabilitacion de calle",
            "rehabilitación de calle", "obra civil", "obra publica",
            "obra pública", "construccion de edificio", "construcción de edificio",
            "ampliacion de red", "ampliación de red", "drenaje pluvial",
            "construccion de carretera", "construcción de carretera",
            "bacheo", "concreto hidraulico", "concreto hidráulico",
            "concreto asfaltico", "concreto asfáltico", "guarniciones y banquetas",
            "infraestructura urbana", "rehabilitacion de pavimento",
            "rehabilitación de pavimento", "construccion de puente",
            "construcción de puente", "urbanizacion", "urbanización",
            "red de drenaje", "alcantarillado", "electrificacion",
            "electrificación",
        ],
    },
}

# Frases que, si aparecen, descartan la licitación aunque haya matcheado
# una palabra clave (para reducir falsos positivos obvios)
NEGATIVE_KEYWORDS = [
    "uniformes", "papeleria", "papelería", "material de oficina",
    "servicio de limpieza de oficinas", "renta de fotocopiadoras",
]

# Estados a monitorear con prioridad (Guanajuato primero). El resto de
# estados se incluyen igual, pero esto sirve para ordenar el reporte.
PRIORITY_STATES = [
    "Guanajuato", "Querétaro", "Jalisco", "Nuevo León", "Ciudad de México",
    "Estado de México",
]
