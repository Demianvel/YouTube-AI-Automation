using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Data.Sqlite;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient();
builder.Services.AddSingleton<LicenseStore>();
var app = builder.Build();

var store = app.Services.GetRequiredService<LicenseStore>();
await store.InitializeAsync();

app.MapGet("/health", () => Results.Ok(new { service = "clinix-mx-billing", status = "ok" }));

app.MapPost("/api/checkout", async (CheckoutRequest request, IConfiguration config, IHttpClientFactory http, CancellationToken ct) =>
{
    var plan = request.Plan?.ToLowerInvariant() ?? "professional";
    var currency = request.Currency?.ToLowerInvariant();
    var priceId = (plan, currency) switch
    {
        ("professional", "mxn") => config["Stripe:PriceMxn"] ?? "price_1UCRy4AgBbQ9FA5L0ncvfAlo",
        ("professional", "usd") => config["Stripe:PriceUsd"] ?? "price_1UCRyGAgBbQ9FA5L6nm4gdfL",
        ("maintenance", "usd") => config["Stripe:MaintenancePriceUsd"] ?? "price_1UCSBmAgBbQ9FA5LGiS6BUE6",
        ("permanent", "usd") => config["Stripe:PermanentPriceUsd"] ?? "price_1UCS8yAgBbQ9FA5LUo6XLTQj",
        _ => null
    };

    if (priceId is null)
        return Results.BadRequest(new { error = "Combinación de plan/moneda no soportada." });

    var secret = config["Stripe:SecretKey"];
    if (string.IsNullOrWhiteSpace(secret))
        return Results.Problem("Stripe no está configurado en el servidor.", statusCode: 503);

    var successUrl = config["App:SuccessUrl"] ?? "https://clinix.mx/pago-exitoso?session_id={CHECKOUT_SESSION_ID}";
    var cancelUrl = config["App:CancelUrl"] ?? "https://clinix.mx/pago-cancelado";
    var reference = request.LicenseId ?? Guid.NewGuid().ToString("N");
    var mode = plan == "permanent" ? "payment" : "subscription";

    using var client = http.CreateClient();
    client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", secret);
    using var content = new FormUrlEncodedContent(new Dictionary<string, string>
    {
        ["mode"] = mode,
        ["line_items[0][price]"] = priceId,
        ["line_items[0][quantity]"] = "1",
        ["success_url"] = successUrl,
        ["cancel_url"] = cancelUrl,
        ["allow_promotion_codes"] = "true",
        ["billing_address_collection"] = "auto",
        ["client_reference_id"] = reference,
        ["metadata[product]"] = "clinix-mx",
        ["metadata[plan]"] = plan,
        ["metadata[currency]"] = currency ?? "usd",
        ["metadata[license_id]"] = reference
    });

    var response = await client.PostAsync("https://api.stripe.com/v1/checkout/sessions", content, ct);
    var body = await response.Content.ReadAsStringAsync(ct);
    if (!response.IsSuccessStatusCode)
        return Results.Content(body, "application/json", Encoding.UTF8, (int)response.StatusCode);

    using var json = JsonDocument.Parse(body);
    return Results.Ok(new { url = json.RootElement.GetProperty("url").GetString(), plan, currency });
});

app.MapPost("/api/stripe/webhook", async (HttpRequest request, IConfiguration config, LicenseStore store, ILogger<Program> logger, CancellationToken ct) =>
{
    var webhookSecret = config["Stripe:WebhookSecret"];
    if (string.IsNullOrWhiteSpace(webhookSecret))
        return Results.Problem("Stripe webhook no está configurado.", statusCode: 503);

    using var reader = new StreamReader(request.Body);
    var payload = await reader.ReadToEndAsync(ct);
    var signature = request.Headers["Stripe-Signature"].FirstOrDefault();
    if (!StripeWebhookVerifier.Verify(payload, signature, webhookSecret)) return Results.Unauthorized();

    using var json = JsonDocument.Parse(payload);
    var root = json.RootElement;
    var eventId = root.GetProperty("id").GetString() ?? Guid.NewGuid().ToString("N");
    var eventType = root.GetProperty("type").GetString() ?? "unknown";
    if (!await store.TryBeginEventAsync(eventId, eventType, payload, ct))
        return Results.Ok(new { received = true, duplicate = true });

    try
    {
        var obj = root.GetProperty("data").GetProperty("object");
        switch (eventType)
        {
            case "checkout.session.completed":
                await store.HandleCheckoutCompletedAsync(obj, ct);
                break;
            case "invoice.paid":
                await store.HandleInvoicePaidAsync(obj, ct);
                break;
            case "invoice.payment_failed":
                await store.HandleInvoiceFailedAsync(obj, ct);
                break;
            case "customer.subscription.deleted":
                await store.HandleSubscriptionDeletedAsync(obj, ct);
                break;
        }
        await store.CompleteEventAsync(eventId, "processed", ct);
        logger.LogInformation("Stripe event processed: {EventType}", eventType);
        return Results.Ok(new { received = true });
    }
    catch (Exception ex)
    {
        await store.CompleteEventAsync(eventId, "failed", ct);
        logger.LogError(ex, "Stripe event failed: {EventType}", eventType);
        return Results.StatusCode(500);
    }
});

app.MapGet("/api/license/{licenseKey}", async (string licenseKey, LicenseStore store, CancellationToken ct) =>
    Results.Ok(await store.GetLicenseAsync(licenseKey, ct)));

app.MapGet("/api/updates/manifest", (IConfiguration config) => Results.Ok(new
{
    version = config["Updates:Version"] ?? "1.0.0",
    downloadUrl = config["Updates:DownloadUrl"] ?? "",
    sha256 = config["Updates:Sha256"] ?? "",
    mandatory = bool.TryParse(config["Updates:Mandatory"], out var m) && m,
    releaseNotes = config["Updates:ReleaseNotes"] ?? ""
}));

app.MapPost("/api/admin/licenses/{licenseKey}/extend", async (string licenseKey, AdminExtendRequest request, HttpRequest httpRequest, IConfiguration config, LicenseStore store, CancellationToken ct) =>
{
    if (!AdminAuth.IsAuthorized(httpRequest, config["Admin:ApiKey"])) return Results.Unauthorized();
    if (request.Days is not (30 or 90 or 365) && !request.Permanent) return Results.BadRequest(new { error = "Days debe ser 30, 90 o 365, o Permanent=true." });
    var result = await store.ManualExtendAsync(licenseKey, request.Days, request.Permanent, request.Maintenance, ct);
    return result ? Results.Ok(new { licenseKey, updated = true }) : Results.NotFound();
});

app.Run();

public sealed record CheckoutRequest(string? Currency, string? LicenseId, string? Plan);
public sealed record AdminExtendRequest(int Days = 0, bool Permanent = false, bool Maintenance = false);

public static class AdminAuth
{
    public static bool IsAuthorized(HttpRequest request, string? configuredKey) =>
        !string.IsNullOrWhiteSpace(configuredKey) && request.Headers.TryGetValue("X-Admin-Key", out var supplied) &&
        CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(configuredKey), Encoding.UTF8.GetBytes(supplied.ToString()));
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
        return signatures.Any(s => CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(expected), Encoding.UTF8.GetBytes(s.ToLowerInvariant())));
    }
}

public sealed class LicenseStore
{
    private readonly string _connectionString;
    public LicenseStore(IConfiguration config)
    {
        var db = config["Database:Path"] ?? "clinix-billing.db";
        _connectionString = new SqliteConnectionStringBuilder { DataSource = db, Mode = SqliteOpenMode.ReadWriteCreate, Cache = SqliteCacheMode.Shared }.ToString();
    }

    public async Task InitializeAsync()
    {
        await using var c = new SqliteConnection(_connectionString); await c.OpenAsync();
        var cmd = c.CreateCommand();
        cmd.CommandText = @"
CREATE TABLE IF NOT EXISTS stripe_events(event_id TEXT PRIMARY KEY,type TEXT NOT NULL,payload TEXT NOT NULL,received_at TEXT NOT NULL,processed_at TEXT,status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS licenses(license_key TEXT PRIMARY KEY,email TEXT,stripe_customer_id TEXT,plan TEXT NOT NULL,status TEXT NOT NULL,expires_at TEXT,maintenance_expires_at TEXT,stripe_subscription_id TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,license_key TEXT NOT NULL,action TEXT NOT NULL,created_at TEXT NOT NULL,source TEXT NOT NULL);
";
        await cmd.ExecuteNonQueryAsync();
    }

    public async Task<bool> TryBeginEventAsync(string id, string type, string payload, CancellationToken ct)
    {
        await using var c = new SqliteConnection(_connectionString); await c.OpenAsync(ct); await using var tx = await c.BeginTransactionAsync(ct);
        var exists = c.CreateCommand(); exists.Transaction = tx; exists.CommandText = "SELECT 1 FROM stripe_events WHERE event_id=$id"; exists.Parameters.AddWithValue("$id", id);
        if (await exists.ExecuteScalarAsync(ct) is not null) return false;
        var cmd = c.CreateCommand(); cmd.Transaction = tx; cmd.CommandText = "INSERT INTO stripe_events(event_id,type,payload,received_at,status) VALUES($id,$type,$payload,$at,'processing')";
        cmd.Parameters.AddWithValue("$id", id); cmd.Parameters.AddWithValue("$type", type); cmd.Parameters.AddWithValue("$payload", payload); cmd.Parameters.AddWithValue("$at", DateTimeOffset.UtcNow.ToString("O")); await cmd.ExecuteNonQueryAsync(ct); await tx.CommitAsync(ct); return true;
    }

    public async Task CompleteEventAsync(string id, string status, CancellationToken ct)
    { await using var c = new SqliteConnection(_connectionString); await c.OpenAsync(ct); var cmd=c.CreateCommand(); cmd.CommandText="UPDATE stripe_events SET status=$s,processed_at=$at WHERE event_id=$id"; cmd.Parameters.AddWithValue("$s",status); cmd.Parameters.AddWithValue("$at",DateTimeOffset.UtcNow.ToString("O")); cmd.Parameters.AddWithValue("$id",id); await cmd.ExecuteNonQueryAsync(ct); }

    public async Task HandleCheckoutCompletedAsync(JsonElement o, CancellationToken ct)
    {
        var meta=o.GetProperty("metadata"); var plan=meta.TryGetProperty("plan",out var p)?p.GetString():"professional"; var key=meta.TryGetProperty("license_id",out var k)?k.GetString():null; if(string.IsNullOrWhiteSpace(key)) key=GenerateKey();
        var email=o.TryGetProperty("customer_details",out var cd)&&cd.TryGetProperty("email",out var em)?em.GetString():null; var customer=o.TryGetProperty("customer",out var cu)?cu.GetString():null; var sub=o.TryGetProperty("subscription",out var su)?su.GetString():null;
        if(plan=="permanent") await UpsertAsync(key,email,customer,"permanent","active",null,null,sub,"stripe-permanent",ct);
        else await UpsertAsync(key,email,customer,plan!,"pending",DateTimeOffset.UtcNow.AddDays(plan=="maintenance"?0:30),plan=="maintenance"?DateTimeOffset.UtcNow.AddYears(1):null,sub,"stripe-checkout",ct);
    }

    public async Task HandleInvoicePaidAsync(JsonElement o, CancellationToken ct)
    {
        var sub=o.TryGetProperty("subscription",out var s)?s.GetString():null; if(string.IsNullOrWhiteSpace(sub)) return;
        var key=await FindBySubscriptionAsync(sub,ct); if(key is null) return;
        var plan=await GetPlanAsync(key,ct); if(plan=="maintenance") await ExtendAsync(key,365,true,ct); else await ExtendAsync(key,30,false,ct);
    }

    public async Task HandleInvoiceFailedAsync(JsonElement o, CancellationToken ct)
    { var sub=o.TryGetProperty("subscription",out var s)?s.GetString():null; if(sub is null)return; var key=await FindBySubscriptionAsync(sub,ct); if(key is not null) await SetStatusAsync(key,"payment_failed",ct); }
    public async Task HandleSubscriptionDeletedAsync(JsonElement o, CancellationToken ct)
    { var sub=o.TryGetProperty("id",out var s)?s.GetString():null; if(sub is null)return; var key=await FindBySubscriptionAsync(sub,ct); if(key is not null) await SetStatusAsync(key,"cancelled",ct); }

    public async Task<bool> ManualExtendAsync(string key,int days,bool permanent,bool maintenance,CancellationToken ct)
    { if(!await ExistsAsync(key,ct))return false; if(permanent) await SetPermanentAsync(key,ct); else if(maintenance) await ExtendAsync(key,days,true,ct); else await ExtendAsync(key,days,false,ct); return true; }
    public async Task<object?> GetLicenseAsync(string key,CancellationToken ct)
    { await using var c=new SqliteConnection(_connectionString); await c.OpenAsync(ct); var cmd=c.CreateCommand(); cmd.CommandText="SELECT license_key,email,plan,status,expires_at,maintenance_expires_at FROM licenses WHERE license_key=$k"; cmd.Parameters.AddWithValue("$k",key); await using var r=await cmd.ExecuteReaderAsync(ct); if(!await r.ReadAsync(ct))return null; return new { licenseKey=r.GetString(0),email=r.IsDBNull(1)?null:r.GetString(1),plan=r.GetString(2),status=r.GetString(3),expiresAt=r.IsDBNull(4)?null:r.GetString(4),maintenanceExpiresAt=r.IsDBNull(5)?null:r.GetString(5)}; }

    private async Task UpsertAsync(string key,string? email,string? customer,string plan,string status,DateTimeOffset? exp,DateTimeOffset? maint,string? sub,string source,CancellationToken ct)
    { await using var c=new SqliteConnection(_connectionString); await c.OpenAsync(ct); var now=DateTimeOffset.UtcNow.ToString("O"); var cmd=c.CreateCommand(); cmd.CommandText=@"INSERT INTO licenses(license_key,email,stripe_customer_id,plan,status,expires_at,maintenance_expires_at,stripe_subscription_id,created_at,updated_at) VALUES($k,$e,$c,$p,$s,$x,$m,$sub,$n,$n) ON CONFLICT(license_key) DO UPDATE SET email=COALESCE($e,email),stripe_customer_id=COALESCE($c,stripe_customer_id),plan=$p,status=$s,expires_at=COALESCE($x,expires_at),maintenance_expires_at=COALESCE($m,maintenance_expires_at),stripe_subscription_id=COALESCE($sub,stripe_subscription_id),updated_at=$n"; foreach(var q in new[]{("$k",(object)key),("$e",(object?)email??DBNull.Value),("$c",(object?)customer??DBNull.Value),("$p",plan),("$s",status),("$x",(object?)exp?.ToString("O")??DBNull.Value),("$m",(object?)maint?.ToString("O")??DBNull.Value),("$sub",(object?)sub??DBNull.Value),("$n",now)})cmd.Parameters.AddWithValue(q.Item1,q.Item2); await cmd.ExecuteNonQueryAsync(ct); }
    private async Task ExtendAsync(string key,int days,bool maintenance,CancellationToken ct){await using var c=new SqliteConnection(_connectionString);await c.OpenAsync(ct);var col=maintenance?"maintenance_expires_at":"expires_at";var cmd=c.CreateCommand();cmd.CommandText=$"UPDATE licenses SET {col}=CASE WHEN {col} IS NULL OR datetime({col})<datetime('now') THEN datetime('now','+{days} days') ELSE datetime({col},'+{days} days') END,status='active',updated_at=$at WHERE license_key=$k";cmd.Parameters.AddWithValue("$at",DateTimeOffset.UtcNow.ToString("O"));cmd.Parameters.AddWithValue("$k",key);await cmd.ExecuteNonQueryAsync(ct);}
    private async Task SetPermanentAsync(string key,CancellationToken ct){await using var c=new SqliteConnection(_connectionString);await c.OpenAsync(ct);var cmd=c.CreateCommand();cmd.CommandText="UPDATE licenses SET plan='permanent',status='active',expires_at=NULL,updated_at=$at WHERE license_key=$k";cmd.Parameters.AddWithValue("$at",DateTimeOffset.UtcNow.ToString("O"));cmd.Parameters.AddWithValue("$k",key);await cmd.ExecuteNonQueryAsync(ct);}
    private async Task SetStatusAsync(string key,string status,CancellationToken ct){await using var c=new SqliteConnection(_connectionString);await c.OpenAsync(ct);var cmd=c.CreateCommand();cmd.CommandText="UPDATE licenses SET status=$s,updated_at=$at WHERE license_key=$k";cmd.Parameters.AddWithValue("$s",status);cmd.Parameters.AddWithValue("$at",DateTimeOffset.UtcNow.ToString("O"));cmd.Parameters.AddWithValue("$k",key);await cmd.ExecuteNonQueryAsync(ct);}
    private async Task<bool> ExistsAsync(string key,CancellationToken ct){await using var c=new SqliteConnection(_connectionString);await c.OpenAsync(ct);var cmd=c.CreateCommand();cmd.CommandText="SELECT 1 FROM licenses WHERE license_key=$k";cmd.Parameters.AddWithValue("$k",key);return await cmd.ExecuteScalarAsync(ct) is not null;}
    private async Task<string?> FindBySubscriptionAsync(string sub,CancellationToken ct){await using var c=new SqliteConnection(_connectionString);await c.OpenAsync(ct);var cmd=c.CreateCommand();cmd.CommandText="SELECT license_key FROM licenses WHERE stripe_subscription_id=$s";cmd.Parameters.AddWithValue("$s",sub);return (await cmd.ExecuteScalarAsync(ct))?.ToString();}
    private async Task<string?> GetPlanAsync(string key,CancellationToken ct){await using var c=new SqliteConnection(_connectionString);await c.OpenAsync(ct);var cmd=c.CreateCommand();cmd.CommandText="SELECT plan FROM licenses WHERE license_key=$k";cmd.Parameters.AddWithValue("$k",key);return (await cmd.ExecuteScalarAsync(ct))?.ToString();}
    private static string GenerateKey()=>"CLX-"+Convert.ToHexString(RandomNumberGenerator.GetBytes(10));
}
