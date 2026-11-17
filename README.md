# Recepción automatizada de facturas

Solución para la actividad técnica: n8n recibe un PDF, la API local extrae los datos con Ollama y n8n consulta el ERP de pruebas. Solo se intenta registrar una factura válida cuando `RUN_MODE=live`. Los rechazos generan un aviso al buzón de prueba en modo live.

## Direcciones de esta instalación

- Formulario para cargar PDF: `http://localhost:5678/form/recepcion-facturas`
- Workflow n8n: `http://localhost:5678/workflow/HrCWQAp89AwyjdO7`
- API local de extracción: `http://127.0.0.1:8000/docs`
- ERP de pruebas: `http://192.168.15.113:8000/docs`
- Buzón local de prueba: `http://192.168.15.113:8025`

La exportación del workflow está en [`workflows/recepcion_facturas.json`](workflows/recepcion_facturas.json). Al importarla en otra instancia de n8n, configura allí credenciales Bearer del ERP y SMTP; los secretos no están en el archivo exportado.

## Flujo

1. El formulario de n8n recibe un PDF.
2. n8n envía el PDF a `POST /api/documents/upload` en la API local.
3. La API extrae RUC emisor, número, fecha, orden, subtotal gravado al 15 %, IVA y total. `EXTRACTION_MODE=ai` usa Ollama.
4. n8n consulta al ERP: `GET /proveedores/{ruc}`, `GET /ordenes-compra/{numero}` y `GET /facturas`.
5. n8n valida que el proveedor exista y esté activo, que la orden esté aprobada y corresponda al proveedor, que los importes cuadren y que la factura no esté duplicada.
6. Con `RUN_MODE=dry`, n8n informa el resultado sin hacer el alta ni enviar correo.
7. Con `RUN_MODE=live`, n8n usa `POST /facturas` solo para facturas válidas. Si no se registra, envía un aviso con número, RUC y motivo. Una factura registrada no genera aviso.

El ERP es la fuente de verdad para proveedores, órdenes y facturas. La API local solo recibe y extrae el PDF.

## Configuración y arranque

1. Copia `.env.example` a `.env`. El `.env` local está excluido de Git.
2. Instala y descarga el modelo local de Ollama indicado en `OLLAMA_MODEL`.
3. Inicia Ollama y la API desde la carpeta del proyecto:

   ```powershell
   ollama serve
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

4. Inicia n8n en la instalación local y activa el workflow de recepción de facturas. La instancia usada para esta solución está en `C:\Users\USER\Documents\Andy\n8n-clasificador-de-imagenes`.
5. Abre el formulario de n8n y sube el PDF.

Para la corrida evaluada, cambia `RUN_MODE=dry` a `RUN_MODE=live` en `.env` y reinicia la API. El workflow lee el valor actual desde `/health`. No subas cada factura más de una vez; n8n consulta `/facturas` para detectar duplicados antes del alta.

## Credenciales

- El token Bearer del ERP está guardado como credencial cifrada de n8n; no se incluye en el workflow ni en el repositorio.
- La credencial SMTP de esta instalación usa el buzón de prueba local `192.168.15.113:1025`, sin usuario, contraseña ni TLS, con destino `avisos-andy@prueba.local`.
- El documento de actividad indica `192.168.1.2` para SMTP/bandeja, pero esa IP no respondía desde esta máquina; aquí se usa el servicio equivalente accesible en `192.168.15.113`.
- No se guardan contraseñas de Gmail, Outlook ni tokens dentro del código.

## Facturas de la actividad

Las consultas de lectura al ERP indicaron que F1 y F2 tienen proveedor activo y orden aprobada. Para F3, el ERP respondió que no existe el proveedor ni la orden `OC-2026-0110`, por lo que debe rechazarse y avisarse en modo live. No se deben ejecutar las facturas de prueba durante la preparación; la corrida evaluada debe hacerse una sola vez frente al evaluador.

## Datos extraídos

- Se usa el RUC del emisor, no el RUC comprador.
- Se ignoran la clave de acceso/autorización y otros identificadores ajenos a los campos pedidos.
- El subtotal es `SUBTOTAL 15 %`; no se toma `SUBTOTAL 0 %` ni `DESCUENTO`.
- La suma de subtotal e IVA se compara con el total con tolerancia de 0,02.
- Si falta texto seleccionable o la extracción no es fiable, la factura queda sin registrar y pasa a revisión.

## Seguridad

- `RUN_MODE=dry` es el modo de desarrollo: sin POST de alta y sin correo.
- `.env`, base de datos local, cargas y logs no deben subirse al repositorio.
- El workflow contiene referencias a credenciales de n8n, no el token del ERP ni contraseñas SMTP.
- Durante la preparación no se registraron facturas en el ERP.
