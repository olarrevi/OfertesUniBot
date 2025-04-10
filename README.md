# Bot OfertesUni para Convocatorias Universitarias

Este proyecto contiene un script en Python que consulta y filtra ofertas de dos fuentes (la API de edictes de la UAB y el scraping de la UB) para detectar convocatorias de Selecció de PAS. El sistema envía notificaciones a través de un bot de Telegram y permite marcar convocatorias para recibir actualizaciones a través del comando `/seguiment {idEdicte}`.

## Características

- **Consulta de Ofertas:**  
  - Obtiene ofertas desde la API de la UAB y mediante scraping de la web de la UB.
  - Aplica filtros para incluir solo ofertas que sean:
    - Convocatorias (concepte = "Tipus de documents", categoría = "Convocatòria" y subcategoría = "Selecció de PAS").
    - **O** que estén marcadas para seguimiento (campo `"seguiment": True`).

- **Filtrado por Palabras Clave:**  
  - Permite usar una lista de palabras clave para filtrar el título de la oferta.  
    Por ejemplo: `["sociologia", "polítiques"]`.

- **Notificaciones vía Telegram:**  
  - Envía dos tipos de mensajes:
    - **Ofertas Nuevas:** para convocatorias recién detectadas.
    - **Actualizaciones:** para ofertas que ya existen y están marcadas en seguimiento.
  
- **Gestión de Seguimiento:**  
  - A través del comando `/seguiment {idEdicte}` puedes marcar una oferta para seguimiento.
  - Esto permite recibir notificaciones de actualizaciones en ofertas que, de otro modo, no se mostrarían.

- **Persistencia con JSON:**  
  - Las ofertas procesadas se guardan en un archivo JSON (`ofertas_sociologia.json`) que se utiliza para detectar novedades y actualizaciones (utilizando el campo `idEdicte`).

## Requisitos

- **Python 3:** (Se recomienda Python 3.7 o superior)
- **Dependencias en Python:**
  - [requests](https://pypi.org/project/requests/)
  - [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
- **Acceso a Internet:**  
  Para las consultas a la API y el scraping.

- **Cuenta y Bot de Telegram:**  
  - Necesitas un bot con su token (configurado en `TELEGRAM_BOT_TOKEN`).
  - El ID del chat (configurado en `TELEGRAM_CHAT_ID`).

## Instalación

1. **Descarga el Script:**  
   Clona este repositorio o descarga el archivo `OfertesUniBot.py` a tu sistema.

2. **Instala las Dependencias:**  
   Ejecuta el siguiente comando para instalar las librerías necesarias:
   ```bash
   pip3 install requests beautifulsoup4
   ```

3. **Configura el Script:**  
   - Edita `OfertesUniBot.py` y reemplaza los siguientes parámetros con tus datos:
     - `TELEGRAM_BOT_TOKEN` – Tu token de bot de Telegram.
     - `TELEGRAM_CHAT_ID` – El identificador del chat donde se enviarán las notificaciones.
   - Ajusta, si lo deseas, las listas de palabras clave:
     - `FILTER_TITLE_KEYWORDS` para la API.
     - `SCRAP_FILTER_PHRASES` para el scraping.
   - Puedes modificar otros parámetros globales (por ejemplo, `MAX_DAYS_API`, `MAX_DAYS_SCRAP`).

## Uso

El script se ejecuta de forma única (por ejemplo, una vez al día) y realiza las siguientes acciones:

1. **Procesa Comandos de Telegram:**  
   - Consulta la API de Telegram para detectar comandos pendientes.
   - Si se recibe el comando `/seguiment {idEdicte}`, actualiza el archivo JSON para marcar esa oferta con `"seguiment": True` y envía una confirmación.

2. **Obtiene Ofertas:**  
   - Consulta las ofertas de la API (UAB) y realiza scraping de las ofertas de la UB.
   - Cada oferta es procesada y se genera un identificador único `idEdicte` (usando el valor directo de la API o generado a partir del título para UB).

3. **Filtra Ofertas:**  
   - Se incluyen solo aquellas ofertas que cumplan:
     - Las condiciones de convocatoria:  
       `concepte == "Tipus de documents"`,  
       `categoria == "Convocatòria"` y  
       `subcategoria == "Selecció de PAS"`.
     - **O** que tengan el campo `"seguiment": True`.

4. **Detecta Novedades y Actualizaciones:**  
   - Compara las ofertas actuales (filtradas) con las almacenadas en `ofertas_sociologia.json` (usando `idEdicte`).
   - Se separa la notificación en:
     - **Ofertas Nuevas:** Convocatorias recién detectadas.
     - **Actualizaciones:** Ofertas que ya existían y que están marcadas en seguimiento.

5. **Envía Notificaciones vía Telegram:**  
   - Se envían mensajes separados para "Ofertas Nuevas" y "Actualizaciones".

### Ejecución Manual

Para ejecutar el script manualmente, utiliza:
```bash
/usr/bin/python3 /ruta/al/script/OfertesUniBot.py
```

## Programación en Raspbian

Puedes programar la ejecución diaria del script utilizando cron:

1. Abre el crontab:
   ```bash
   crontab -e
   ```
2. Agrega la siguiente línea (ajusta la ruta y la hora según tu necesidad):
   ```
   0 8 * * * /usr/bin/python3 /ruta/al/script/OfertesUniBot.py >> /ruta/al/log_script.log 2>&1
   ```
3. Guarda y cierra el editor para que la tarea se programe.

## Comandos de Telegram

- **Activar Seguimiento:**  
  Envía un mensaje con el siguiente formato:
  ```
  /seguiment {idEdicte}
  ```
  Por ejemplo:
  ```
  /seguiment 1234567890
  ```
  Este comando marcará la oferta con ese `idEdicte` para seguimiento, lo que permitirá que futuras actualizaciones sean notificadas.

## Estructura del Archivo JSON

El archivo `ofertas_sociologia.json` almacena las ofertas procesadas con la siguiente estructura:
```json
{
  "titulo": "Título de la oferta",
  "fecha_publicacion": "AAAA-MM-DD (o DD-MM-YYYY dependiendo de la fuente)",
  "estado": "Estado de la oferta",
  "enlace": "URL de la oferta",
  "concepte": "Tipus de documents",
  "categoria": "Convocatòria",
  "subcategoria": "Selecció de PAS",
  "idEdicte": "Identificador único (provisto o generado)",
  "seguiment": false,
  "universitat": "UAB" // o "UB"
}
```

## Notas Adicionales

- **Estructura de la Web y API:**  
  Si la estructura de la API o de la página web cambia, puede ser necesario modificar la lógica de filtrado o de scraping.
- **Historial de Ofertas:**  
  Si encuentras problemas con el historial de ofertas (por ejemplo, ofertas sin `idEdicte`), puedes eliminar manualmente el archivo JSON para regenerar una nueva versión.
- **Depuración y Logs:**  
  Se recomienda redirigir la salida del script a un archivo de log para facilitar el seguimiento de errores y eventos importantes.

## Licencia

Este proyecto se distribuye con fines educativos y puede ser modificado según tus necesidades.

## Contacto

Para dudas o sugerencias, puedes contactar a [oriollarrea111@gmail.com] o abrir un issue en el repositorio.
```
