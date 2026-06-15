# Web Unlocker API

Production-ready FastAPI service that fetches any URL through a remote headless
Chromium (Playwright), extracts the main content as clean Markdown (trafilatura,
with an optional GPT-3.5 fallback), caches results in Redis, rotates proxies, and
protects the endpoint with API-key auth + rate limiting.

## API

`POST /fetch`

```http
POST /fetch
Content-Type: application/json
x-api-key: <your-key>

{ "url": "https://example.com" }
```

Response:

```json
{ "success": true, "content": "clean markdown text", "title": "...", "url": "...", "cached": false }
```

`GET /` — health check.

## Architecture

```
app/
  main.py            # FastAPI app, middleware, error handlers
  config.py          # pydantic-settings configuration
  routers/fetch.py   # /fetch endpoint, auth, rate limiting
  services/browser.py# remote Playwright fetch + proxy retry
  services/cleaner.py# trafilatura -> Markdown, OpenAI fallback
  utils/cache.py     # Redis cache (MD5 key, 1h TTL)
  utils/proxy.py     # randomized proxy rotation
```

## Run locally

```bash
cp .env.example .env   # edit as needed
docker compose up --build
```

Services: `api` (FastAPI :8000), `browser` (Playwright server :3000), `redis` (:6379).

```bash
curl -s -X POST http://localhost:8000/fetch \
  -H 'content-type: application/json' \
  -H 'x-api-key: changeme-dev-key' \
  -d '{"url":"https://example.com"}'
```

## Configuration

See [`.env.example`](.env.example) for all environment variables.
