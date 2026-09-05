using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/health", () => Results.Ok(new { service = "clinix-mx-billing", status = "ok" }));

app.MapPost("/api/checkout", async (CheckoutRequest request, IConfiguration config, HttpClientFactory http) =>
{
    var priceId = request.Currency?.ToLowerInvariant() switch
    {
        "mxn" => config["Stripe:PriceMxn"] ?? "price_1UCRy4AgBbQ9FA5L0ncvfAlo",
        "usd" => config["Stripe:PriceUsd"] ?? "price_1UCRyGAgBbQ9FA5L6nm4gdfL",
        _ => null
    };

    if (priceId is null)
        return Results.BadRequest(new { error = "Moneda no soportada. Use mxn o usd." });

    var secret = config["Stripe:SecretKey"];
    if (string.IsNullOrWhiteSpace(secret))
        return Results.Problem("Stripe no está configurado en el servidor.", statusCode: 503);

    var successUrl = config["App:SuccessUrl"] ?? "https://clinix.mx/pago-exitoso?session_id={CHECKOUT_SESSION_ID}";
    var cancelUrl = config["App:CancelUrl"] ?? "https://clinix.mx/pago-cancelado";

    using var client = http.CreateClient();
    using var content = new FormUrlEncodedContent(new Dictionary<string, string>
    {
        ["mode"] = "subscription",
        ["line_items[0][price]"] = priceId,
        ["line_items[0][quantity]"] = "1",
        ["success_url"] = successUrl,
        ["cancel_url"] = cancelUrl,
        ["allow_promotion_codes"] = "true",
        ["billing_address_collection"] = "auto",
        ["client_reference_id"] = request.LicenseId ?? Guid.NewGuid().ToString("N"),
        ["metadata[product]"] = "clinix-mx",
        ["metadata[plan]"] = "professional",
        ["metadata[currency] = request.Currency!.ToLowerInvariant()" ] = ""
    });

    content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/x-www-form-urlencoded");
    client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", secret);
    var response = await client.PostAsync("https://api.stripe.com/v1/checkout/sessions", content);
    var body = await response.Content.ReadAsStringAsync();

    if (!response.IsSuccessStatusCode)
        return Results.StatusCode((int)response.StatusCode);

    using var json = JsonDocument.Parse(body);
    var url = json.RootElement.GetProperty("url").GetString();
    return Results.Ok(new { url });
});

app.MapPost("/api/stripe/webhook", async (HttpRequest request, IConfiguration config, CancellationToken ct) =>
{
    var webhookSecret = config["Stripe:WebhookSecret"];
    if (string.IsNullOrWhiteSpace(webhookSecret))
        return Results.Problem("Stripe webhook no está configurado.", statusCode: 503);

    using var reader = new StreamReader(request.Body);
    var payload = await reader.ReadToEndAsync(ct);
    var signature = request.Headers["Stripe-Signature"].FirstOrDefault();

    if (!StripeWebhookVerifier.Verify(payload, signature, webhookSecret))
        return Results.Unauthorized();

    using var eventJson = JsonDocument.Parse(payload);
    var eventType = eventJson.RootElement.GetProperty("type").GetString();

    // TODO: persistir eventos idempotentes y actualizar la licencia Clinix.
    // Eventos principales: checkout.session.completed, invoice.paid,
    // invoice.payment_failed, customer.subscription.updated/deleted.
    app.Logger.LogInformation("Stripe event received: {EventType}", eventType);

    return Results.Ok(new { received = true });
});

app.Run();

public sealed record CheckoutRequest(string? Currency, string? LicenseId);

public sealed class HttpClientFactory
{
    private readonly IHttpClientFactory _factory;
    public HttpClientFactory(IHttpClientFactory factory) => _factory = factory;
    public HttpClient CreateClient() => _factory.CreateClient();
}

public static class StripeWebhookVerifier
{
    public static bool Verify(string payload, string? signatureHeader, string secret)
    {
        if (string.IsNullOrWhiteSpace(signatureHeader)) return false;

        string? timestamp = null;
        var signatures = new List<string>();
        foreach (var part in signatureHeader.Split(','))
        {
            var pieces = part.Split('=', 2);
            if (pieces.Length != 2) continue;
            if (pieces[0] == "t") timestamp = pieces[1];
            if (pieces[0] == "v1") signatures.Add(pieces[1]);
        }

        if (!long.TryParse(timestamp, out var unixTimestamp)) return false;
        if (Math.Abs(DateTimeOffset.UtcNow.ToUnixTimeSeconds() - unixTimestamp) > 300) return false;

        var signedPayload = $"{timestamp}.{payload}";
        using var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(secret));
        var expected = Convert.ToHexString(hmac.ComputeHash(Encoding.UTF8.GetBytes(signedPayload))).ToLowerInvariant();

        return signatures.Any(s => CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(expected), Encoding.UTF8.GetBytes(s.ToLowerInvariant())));
    }
}
