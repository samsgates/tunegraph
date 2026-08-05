FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --ignore-scripts

FROM node:24-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 10001 tunegraph && adduser --system --uid 10001 --ingroup tunegraph tunegraph
COPY --from=builder --chown=tunegraph:tunegraph /app/.next/standalone ./
COPY --from=builder --chown=tunegraph:tunegraph /app/.next/static ./.next/static
USER tunegraph
EXPOSE 3000
CMD ["node", "server.js"]
