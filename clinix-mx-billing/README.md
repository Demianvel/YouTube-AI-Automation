# Clinix MX Billing

Servicio de facturación de Clinix MX con Stripe Billing + Checkout.

## Precios live configurados

- Professional MXN: **399 MXN/mes** — `price_1UCRy4AgBbQ9FA5L0ncvfAlo`
- Professional USD: **25 USD/mes** — `price_1UCRyGAgBbQ9FA5L6nm4gdfL`
- Producto: `prod_VCrhgf8L1gKf7O`

Los IDs de producto/precio no son secretos. **Nunca** guardar `sk_live_*` ni `whsec_*` en Git.

## Flujo

1. Clinix/web llama `POST /api/checkout` con `currency: mxn` o `usd`.
2. El servicio crea una Stripe Checkout Session en modo `subscription`.
3. El cliente completa el pago en Stripe.
4. Stripe envía eventos al endpoint `POST /api/stripe/webhook`.
5. El servidor verifica la firma `Stripe-Signature`.
6. El siguiente paso es persistir eventos de forma idempotente y extender la licencia 30 días únicamente ante un pago confirmado (`invoice.paid`).

## Variables de entorno

```text
Stripe__SecretKey=sk_live_...
Stripe__WebhookSecret=whsec_...
Stripe__PriceMxn=price_1UCRy4AgBbQ9FA5L0ncvfAlo
Stripe__PriceUsd=price_1UCRyGAgBbQ9FA5L6nm4gdfL
App__SuccessUrl=https://clinix.mx/pago-exitoso?session_id={CHECKOUT_SESSION_ID}
App__CancelUrl=https://clinix.mx/pago-cancelado
```

Para producción, las claves deben vivir en el secret manager del hosting/GitHub Actions, nunca en el repositorio.

## Liquidación

El cliente puede pagar en la moneda del Price seleccionado. La moneda final de liquidación/payout depende de las capacidades y configuración de la cuenta Stripe del negocio; este servicio no convierte ni promete ARS automáticamente.

## Seguridad

- No se almacenan datos de tarjetas.
- El checkout es alojado por Stripe.
- Se verifica la firma del webhook y una ventana temporal de 5 minutos.
- Se requiere idempotencia antes de activar/extender licencias.
- No registrar información clínica en metadata de Stripe.
