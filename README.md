```markdown
# Bot de Ofertas Universitarias

Este proyecto es un bot en Python que obtiene ofertas de dos fuentes (API y scraping) de convocatorias universitarias y envía notificaciones a través de Telegram. Además, permite actualizar el seguimiento de ofertas mediante comandos de Telegram. El script filtra las ofertas según criterios específicos y las guarda en un archivo JSON para comparar en ejecuciones futuras, notificando ofertas nuevas y actualizaciones según la configuración.

## Características

- **Obtención de datos de dos fuentes:**
  - **UAB (API de edictes):** Se filtran y procesan las ofertas usando la API.
  - **UB (Scraping):** Se extraen datos de la página web mediante BeautifulSoup.
- **Filtrado avanzado:**
  - Se consideran ofertas que cumplan con la siguiente condición:
    - `concepte` = `"Tipus de documents"`,  
      `categoria` = `"Convocatòria"` y  
      `subcategoria` = `"Selecció de PAS"`.
  - Si una oferta no cumple el criterio anterior, solo se incluirá si tiene el flag de seguimiento (`seguiment = True`).
  - Se utilizan listas de palabras clave para filtrar el título:
    - `FILTER_TITLE_KEYWORDS` (para la API) y `SCRAP_FILTER_PHRASES` (para el scraping). Ejemplo: `["sociologia", "polítiques"]`.
- **Gestión de ofertas:**
  - Se genera un identificador único (`idEdicte`) para cada oferta.
    - Para la API, se utiliza el `id_edicte` real.
    - Para el scraping, se genera un id numérico a partir de los 10 primeros caracteres del título (usando SHA‑256).
  - Se guarda la información en un archivo JSON, lo que permite detectar ofertas nuevas y actualizaciones entre ejecuciones.
- **Notificaciones mediante Telegram:**
  - Se envían mensajes diferenciados para **Ofertas Nuevas** y **Actualizaciones**.
  - Se procesan comandos entrantes de Telegram para activar el seguimiento de una oferta mediante `/seguiment {idEdicte}`.
- **Configuración flexible:**
  - Parámetros de filtrado, conexión a la API, rutas, etc. son fácilmente configurables en el script.

## Requisitos y Dependencias

- **Python 3**
- **Bibliotecas Python:**
  - `requests`
  - `beautifulsoup4`
  - `lxml` (opcional, para acelerar el parsing de HTML)
- **Instalación de dependencias:**
  ```bash
  pip3 install requests beautifulsoup4 lxml
  ```

## Configuración

1. **Credenciales de Telegram:**
   - Reemplaza `YOUR_BOT_TOKEN` y `YOUR_CHAT_ID` en el script con los valores correspondientes a tu bot y el chat donde se enviarán las notificaciones.

2. **Listas de palabras clave:**
   - Edita las variables `FILTER_TITLE_KEYWORDS` y `SCRAP_FILTER_PHRASES` para añadir o modificar los términos de filtrado (por ejemplo: `["sociologia", "polítiques"]`).

3. **Otros parámetros configurables:**
   - Modifica `API_URL`, `SCRAP_URL_BASE`, `MAX_DAYS_API`, `MAX_DAYS_SCRAP` y `MAX_RESULT_SCRAP` según los requerimientos de tu fuente de datos.
   - `JSON_FILE` es la ruta del archivo donde se guardará el historial de ofertas.

## Uso

El script se ejecuta de forma única para obtener y comparar las ofertas actuales con las previas, enviando notificaciones por Telegram para ofertas nuevas y actualizaciones de aquellas ofertas que tienen el flag de seguimiento activado.

Para ejecutar el script:
```bash
/usr/bin/python3 /ruta/completa/al/script.py
```

## Procesamiento de Comandos de Telegram

El script consulta los comandos pendientes mediante la API de Telegram.  
Para activar el seguimiento de una oferta, envía el comando:
```
/seguiment {idEdicte}
```
- El script busca en el archivo JSON la oferta con el identificador `{idEdicte}` y activa su flag de seguimiento (`"seguiment": True`).
- Con el seguimiento activado, futuras actualizaciones de esa oferta se notificarán incluso si no cumple el filtro inicial.

## Ejecución Programada en Raspbian

Para que el script se ejecute automáticamente (por ejemplo, cada día a las 8:00 AM) en Raspbian, utiliza **cron**:

1. Abre el archivo de cron:
   ```bash
   crontab -e
   ```
2. Añade la siguiente línea (reemplaza la ruta correcta al script):
   ```
   0 8 * * * /usr/bin/python3 /ruta/completa/al/script.py >> /ruta/completa/al/log_script.log 2>&1
   ```
   Esto ejecutará el script cada día a las 8:00 AM y redirigirá la salida a un archivo de log.

## Estructura del JSON

El archivo JSON (`ofertas_sociologia.json`) contiene una lista de diccionarios, cada uno con la siguiente estructura:

```json
{
  "titulo": "Ejemplo de título",
  "fecha_publicacion": "2023-07-22",
  "estado": "oberta",
  "enlace": "https://ejemplo.com/detalle",
  "concepte": "Tipus de documents",
  "categoria": "Convocatòria",
  "subcategoria": "Selecció de PAS",
  "idEdicte": "1234567890",
  "seguiment": false,
  "universitat": "UAB"  // o "UB"
}
```

## Notas Finales

- Asegúrate de que el JSON no tenga registros antiguos con estructuras incompatibles. En caso de errores, considera eliminar el archivo JSON para reiniciar la base de datos.
- El script diferencia y separa las notificaciones en dos grupos:  
  - **Ofertas Nuevas:** aquellas ofertas que aparecen por primera vez.  
  - **Actualizaciones:** ofertas que ya existían y están marcadas en seguimiento.

¡Con esta configuración, tendrás un bot de Telegram que te notificará de las convocatorias que te interesan y sus actualizaciones!
```
