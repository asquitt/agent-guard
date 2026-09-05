# ---------- deps ----------
FROM node:20-alpine AS deps

WORKDIR /app
COPY agentguard-frontend/package.json agentguard-frontend/package-lock.json ./
RUN npm ci --ignore-scripts

# ---------- builder ----------
FROM node:20-alpine AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY agentguard-frontend/ .

ENV NEXT_TELEMETRY_DISABLED=1
RUN mkdir -p public \
    && npm run build

# ---------- runtime ----------
FROM node:20-alpine AS runtime

RUN addgroup -S -g 10001 app \
    && adduser -S -D -H -u 10001 -G app app

WORKDIR /app

COPY --from=builder --chown=10001:10001 /app/.next/standalone ./
COPY --from=builder --chown=10001:10001 /app/.next/static ./.next/static
COPY --from=builder --chown=10001:10001 /app/public ./public

USER 10001:10001

EXPOSE 3000

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:3000/ || exit 1

CMD ["node", "server.js"]
