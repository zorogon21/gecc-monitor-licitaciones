# GECC — Monitor de Licitaciones

Este repositorio busca automáticamente licitaciones públicas relevantes para
GECC/CONSENER cada 2 horas, las clasifica por categoría de negocio, y las
muestra en una página web que se actualiza sola.

## Categorías que detecta
- Alumbrado público y luminarias
- Medidores de agua / sistemas hídricos
- Maquinaria pesada
- Construcción y obra civil

## Fuente de datos (versión 1)
Por ahora usa la **API oficial de Contrataciones Abiertas del Gobierno de
México** (`api.datos.gob.mx`), que cubre dependencias federales, paraestatales
(CFE, Pemex, IMSS, etc.) y contratos estatales/municipales que tienen
financiamiento federal.

**Importante:** esto NO cubre el 100% de licitaciones estatales y municipales
puramente locales (las que se pagan solo con presupuesto del estado o
municipio, sin participación federal) — por ejemplo, una licitación 100%
pagada por el municipio de Celaya con su propio presupuesto puede no
aparecer aquí. Esa es la siguiente fase del proyecto: agregar el portal
estatal de Guanajuato y portales municipales uno por uno (ver sección
"Próximos pasos" abajo).

## Cómo activarlo (pasos únicos, solo la primera vez)

### 1. Sube estos archivos a tu repositorio
Arrastra toda esta carpeta a `github.com/zorogon21/gecc-monitor-licitaciones`
usando "Add file → Upload files" en la página de tu repositorio, o si
prefieres usar git desde tu computadora, los comandos están en la página de
inicio del repo.

### 2. Activa GitHub Pages
1. Ve a tu repositorio → pestaña **Settings**.
2. En el menú izquierdo, da clic en **Pages**.
3. En "Build and deployment" → "Source", selecciona **GitHub Actions**.
4. Guarda.

### 3. Activa el flujo automático
1. Ve a la pestaña **Actions** de tu repositorio.
2. Si te pide habilitar Actions, dale clic a habilitar.
3. Busca el flujo llamado **"Monitor de licitaciones GECC"**.
4. Dale clic en **"Run workflow"** para forzar la primera corrida manual
   (no hace falta esperar las 2 horas la primera vez).

### 4. Encuentra tu link
Después de que corra por primera vez (toma 1-2 minutos), tu página va a
estar disponible en:

```
https://zorogon21.github.io/gecc-monitor-licitaciones/
```

Ese es el link que puedes compartir con tu papá o guardar en favoritos.

## Cómo revisar que está funcionando
- Pestaña **Actions** de tu repo: ahí ves cada corrida, si fue exitosa (✅)
  o falló (❌), y los logs detallados si algo sale mal.
- El archivo `data/run_log.json` también guarda un historial simple de cada
  corrida y cualquier error.

## Cómo ajustar qué detecta el agente
Todo el "cerebro" de qué palabras buscar vive en `scripts/keywords.py`.
Cada categoría tiene una lista de frases — si el agente se está perdiendo
algo que sabes que existe, agrega la frase ahí. Si está trayendo basura
repetida, agrégala a `NEGATIVE_KEYWORDS`.

## Próximos pasos (fase 2)
- Agregar el portal estatal de compras de Guanajuato.
- Agregar portales municipales de Celaya, Cortazar, Dolores Hidalgo y
  Villagrán (la mayoría publica licitaciones como PDFs sueltos en su sitio
  de transparencia, así que requiere un lector específico por municipio).
- Agregar más estados conforme veamos qué tan seguido salen licitaciones
  relevantes fuera de Guanajuato.
- Opcional: usar un modelo de IA (en vez de solo palabras clave) para leer
  cada descripción completa y decidir relevancia con más precisión —
  requeriría agregar una clave de API de Anthropic como "secreto" del
  repositorio.
