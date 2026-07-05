import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Single-file Java client for the Dummy REST API servers.
 *
 * Supports three auth modes (matching the server's optional auth config):
 *   - apikey : sent as the "X-API-Key" header
 *   - jwt    : obtained from POST /auth/login, sent as "Authorization: Bearer <token>"
 *   - none   : no auth header (use when the server runs with AUTH_ENABLED=false)
 *
 * Run (Java 11+, no build needed):
 *   java InvokeClient.java                 # demo all 4 servers (default apikey, or none if AUTH_ENABLED=false)
 *   java InvokeClient.java none            # demo all 4 servers with NO auth
 *   java InvokeClient.java jwt             # demo all 4 servers with JWT
 *   java InvokeClient.java bookstore jwt   # demo a single server with JWT
 */
public class InvokeClient {

    static final String API_KEY = envOr("API_KEY", "my-secret-api-key");
    static final String USERNAME = envOr("AUTH_USER", "admin");
    static final String PASSWORD = envOr("AUTH_PASS", "password");
    static final String DEFAULT_AUTH = defaultAuth();

    static String envOr(String name, String def) {
        String v = System.getenv(name);
        return (v == null || v.isBlank()) ? def : v;
    }

    static String defaultAuth() {
        String mode = System.getenv("AUTH_MODE");
        if (mode != null && !mode.isBlank()) return mode;
        String enabled = envOr("AUTH_ENABLED", "true").trim().toLowerCase();
        boolean off = enabled.equals("false") || enabled.equals("0") || enabled.equals("no") || enabled.equals("off");
        return off ? "none" : "apikey";
    }

    static final HttpClient HTTP = HttpClient.newHttpClient();

    // name -> [baseUrl, entity, sampleJsonBody]
    static final Map<String, String[]> SERVERS = new LinkedHashMap<>();
    static {
        SERVERS.put("bookstore", new String[]{"http://localhost:8001", "books",
                "{\"title\":\"Client Test Book\",\"author_id\":1,\"price\":19.5}"});
        SERVERS.put("inventory", new String[]{"http://localhost:8002", "products",
                "{\"name\":\"Client Test Product\",\"sku\":\"CT-001\",\"price\":12.0,\"stock\":10}"});
        SERVERS.put("school", new String[]{"http://localhost:8081", "students",
                "{\"name\":\"Client Test Student\",\"age\":14,\"grade\":\"9\"}"});
        SERVERS.put("hospital", new String[]{"http://localhost:8082", "patients",
                "{\"name\":\"Client Test Patient\",\"age\":30,\"bloodGroup\":\"B+\"}"});
    }

    public static void main(String[] args) {
        String auth = DEFAULT_AUTH;
        String target = null;
        for (String a : args) {
            if (a.equals("apikey") || a.equals("jwt") || a.equals("none")) auth = a;
            else if (SERVERS.containsKey(a)) target = a;
            else {
                System.out.println("Unknown argument: " + a);
                System.out.println("Servers: " + SERVERS.keySet() + " | Auth: apikey, jwt, none");
                return;
            }
        }

        for (Map.Entry<String, String[]> e : SERVERS.entrySet()) {
            if (target != null && !target.equals(e.getKey())) continue;
            demo(e.getKey(), e.getValue(), auth);
        }
    }

    static void demo(String name, String[] cfg, String auth) {
        String base = cfg[0], entity = cfg[1], body = cfg[2];
        System.out.printf("%n=== %s  (%s)  auth=%s ===%n", name.toUpperCase(), base, auth);
        try {
            String[] authHeader = authHeader(base, auth);

            HttpResponse<String> listResp = send("GET", base + "/" + entity, null, authHeader);
            System.out.printf("GET  /%s        -> HTTP %d%n", entity, listResp.statusCode());

            HttpResponse<String> createResp = send("POST", base + "/" + entity, body, authHeader);
            String id = extract(createResp.body(), "id");
            System.out.printf("POST /%s        -> HTTP %d (id=%s)%n", entity, createResp.statusCode(), id);

            HttpResponse<String> getResp = send("GET", base + "/" + entity + "/" + id, null, authHeader);
            System.out.printf("GET  /%s/%s      -> HTTP %d : %s%n", entity, id, getResp.statusCode(), getResp.body());

            HttpResponse<String> delResp = send("DELETE", base + "/" + entity + "/" + id, null, authHeader);
            System.out.printf("DEL  /%s/%s      -> HTTP %d : %s%n", entity, id, delResp.statusCode(), delResp.body());
        } catch (java.net.ConnectException ce) {
            System.out.println("  [skipped] " + name + " server not reachable at " + base);
        } catch (Exception ex) {
            System.out.println("  [error] " + ex.getMessage());
        }
    }

    /** Returns the header name/value pair to use, or null for no auth. */
    static String[] authHeader(String base, String auth) throws Exception {
        if (auth.equals("none")) {
            return null;
        }
        if (auth.equals("jwt")) {
            String loginBody = "{\"username\":\"" + USERNAME + "\",\"password\":\"" + PASSWORD + "\"}";
            HttpResponse<String> resp = send("POST", base + "/auth/login", loginBody, null);
            String token = extract(resp.body(), "access_token");
            return new String[]{"Authorization", "Bearer " + token};
        }
        return new String[]{"X-API-Key", API_KEY};
    }

    static HttpResponse<String> send(String method, String url, String body, String[] authHeader) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(url))
                .header("Content-Type", "application/json");
        if (authHeader != null) b.header(authHeader[0], authHeader[1]);

        HttpRequest.BodyPublisher pub = body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body);
        b.method(method, pub);

        return HTTP.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }

    /** Minimal JSON value extractor for a top-level "key": handles string or numeric values. */
    static String extract(String json, String key) {
        Matcher m = Pattern.compile("\"" + Pattern.quote(key) + "\"\\s*:\\s*\"?([^\",}\\s]+)\"?").matcher(json);
        return m.find() ? m.group(1) : "?";
    }
}
