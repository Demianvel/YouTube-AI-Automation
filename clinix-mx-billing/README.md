# Clinix MX Billing

Servicio de facturación de Clinix MX con Stripe Checkout + Billing.

## Precios live

- Professional MXN: **399 MXN/mes** — `price_1UCRy4AgBbQ9FA5L0ncvfAlo`
- Professional USD: **25 USD/mes** — `price_1UCRyGAgBbQ9FA5L6nm4gdfL`
- Licencia permanente Enterprise: **2,500 USD, pago único** — `price_1UCS8yAgBbQ9FA5LUo6XLTQj`
- Mantenimiento y soporte: **650 USD/año, recurrente** — `price_1UCSBmAgBbQ9FA5LGiS6BUE6`
- Producto mantenimiento: `prod_VCrv9o2kvmuKku`

Los IDs de productos/precios no son secretos. Nunca guardar `sk_live_*`, `whsec_*` ni la clave administrativa en Git.

## Checkout

`POST /api/checkout`

```json
{"plan":"professional","currency":"mxn"}
{"plan":"professional","currency":"usd"}
{"plan":"maintenance","currency":"usd","licenseId":"CLX-..."}
{"plan":"permanent","currency":"usd"}
```

La licencia permanente usa Checkout `payment`. Professional y Mantenimiento usan Checkout `subscription`.

## Webhooks y activación automática

`POST /api/stripe/webhook` verifica `Stripe-Signature` y persiste el `event_id` antes de procesarlo para evitar duplicados.

- `checkout.session.completed`: registra la licencia/contrato.
- `invoice.paid`: extiende Professional 30 días o Mantenimiento 365 días.
- `invoice.payment_failed`: marca el contrato como `payment_failed`.
- `customer.subscription.deleted`: marca la suscripción como cancelada.

La licencia permanente no caduca. El mantenimiento es un derecho separado y puede vencer sin borrar ni bloquear los datos del cliente.

## Administración manual

`POST /api/admin/licenses/{licenseKey}/extend`

Header requerido en servidor: `X-Admin-Key`.

Ejemplos:

```json
{"Days":365,"Maintenance":true}
{"Days":30}
{"Permanent":true}
```

En producción, `Admin__ApiKey` debe vivir en un secret manager. Para una consola administrativa completa se recomienda añadir autenticación de usuario + MFA y auditoría por operador antes de exponerla públicamente.

## Estado de licencia

`GET /api/license/{licenseKey}` devuelve el estado, expiración de licencia y expiración de mantenimiento. No devuelve datos clínicos.

## Actualizaciones automáticas

`GET /api/updates/manifest` expone versión, URL, SHA-256, obligatoriedad y notas de la última versión. El cliente Windows debe descargar la actualización con un updater separado, validar hash/firma y reiniciar la aplicación. El servidor no debe reemplazar el `.exe` que está ejecutándose.

## Variables de entorno

```text
Stripe__SecretKey=sk_live_...
Stripe__WebhookSecret=whsec_...
Stripe__PriceMxn=price_1UCRy4AgBbQ9FA5L0ncvfAlo
Stripe__PriceUsd=price_1UCRyGAgBbQ9FA5L6nm4gdfL
Stripe__MaintenancePriceUsd=price_1UCSBmAgBbQ9FA5LGiS6BUE6
Stripe__PermanentPriceUsd=price_1UCS8yAgBbQ9FA5LUo6XLTQj
Database__Path=clinix-billing.db
Admin__ApiKey=...
Updates__Version=1.0.0
Updates__DownloadUrl=...
Updates__Sha256=...
Updates__Mandatory=false
Updates__ReleaseNotes=...
App__SuccessUrl=https://clinix.mx/pago-exitoso?session_id={CHECKOUT_SESSION_ID}
App__CancelUrl=https://clinix.mx/pago-cancelado
```

## Seguridad

- No se almacenan datos de tarjetas.
- Checkout es alojado por Stripe.
- Firma de webhook y ventana temporal de 5 minutos.
- Idempotencia por `event_id`.
- No se almacenan datos clínicos en Stripe metadata.
- La base de datos contiene estado de licencias y facturación, no historias clínicas.

## Producción pendiente

Configurar el endpoint de webhook en Stripe apuntando al despliegue HTTPS real y guardar secretos en el proveedor de hosting/secret manager. También hay que integrar el updater Windows con el manifest y publicar releases firmadas.
