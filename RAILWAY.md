# Deploying to Railway

`docker-compose.yml` is for local dev. On Railway each component is a **separate
service** inside one project, wired together over Railway's **private network**.

You need 3 services:

| Service   | Source                                            | Listens on |
|-----------|---------------------------------------------------|------------|
| `api`     | this GitHub repo (Dockerfile)                     | `$PORT`    |
| `browser` | Docker image `mcr.microsoft.com/playwright:v1.44.0-jammy` | `3000`     |
| `redis`   | Railway "Redis" database template                 | `6379`     |

## Two Railway gotchas (already handled in this repo)

1. **`$PORT`** — Railway injects the port the `api` must listen on. The Dockerfile
   uses `--port ${PORT:-8000}`, so it works both locally and on Railway.
2. **Private networking is IPv6-only.** Any service other services connect to must
   bind to `::`, not `0.0.0.0`. That matters for the `browser` service start command
   below.

## Step by step (dashboard)

1. **Create project** → "Deploy from GitHub repo" → pick `Sunil-ghodela/wwebunloker`.
   This becomes the `api` service (Railway reads `railway.json` / `Dockerfile`).

2. **Add Redis**: project → "New" → "Database" → "Add Redis". Note its service name
   (default `Redis`).

3. **Add the browser service**: project → "New" → "Empty Service" (or "Docker Image").
   - Source / Image: `mcr.microsoft.com/playwright:v1.44.0-jammy`
   - Start command (note `::` for IPv6 private networking):
     ```
     npx -y playwright@1.44.0 run-server --host :: --port 3000
     ```
   - No public domain needed — it's reached only over the private network.
   - Rename the service to `browser` so the internal hostname is predictable.

4. **Set `api` service variables** (Settings → Variables):
   ```
   PLAYWRIGHT_SERVER_URL = ws://browser.railway.internal:3000/
   REDIS_URL             = ${{Redis.REDIS_URL}}
   DEV_API_KEYS          = <your-secret-key>        # or use API_KEY_HASHES
   REQUEST_RATE_LIMIT    = 5/minute
   OPENAI_API_KEY        = <optional>
   OPENAI_MODEL          = gpt-3.5-turbo
   FREE_PROXY_LIST       = <optional, comma separated>
   ```
   `${{Redis.REDIS_URL}}` is a Railway reference variable — adjust `Redis` if you
   named the database service differently.

5. **Generate a public domain** on the `api` service (Settings → Networking →
   "Generate Domain").

6. **Test**:
   ```bash
   curl -s -X POST https://<your-api>.up.railway.app/fetch \
     -H 'content-type: application/json' \
     -H 'x-api-key: <your-secret-key>' \
     -d '{"url":"https://example.com"}'
   ```

## CLI alternative

```bash
npm i -g @railway/cli
railway login            # interactive (opens browser)
railway init             # create/link project
railway up               # deploy this repo as the api service
# add Redis + browser services in the dashboard, then set variables as above
```
