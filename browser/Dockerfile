# Standalone Playwright browser server for Railway.
# Bind to :: so it is reachable over Railway's IPv6-only private network.
FROM mcr.microsoft.com/playwright:v1.44.0-jammy
EXPOSE 3000
CMD ["npx", "-y", "playwright@1.44.0", "run-server", "--host", "::", "--port", "3000"]
