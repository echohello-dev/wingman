FROM oven/bun:1.3.14 AS dependencies
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile --ignore-scripts

FROM node:24-bookworm-slim
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY package.json *.mjs ./
RUN mkdir /data && chown node:node /data
USER node
ENV PI_DATA_DIR=/data PI_HOST=0.0.0.0
EXPOSE 8002
CMD ["node", "server.mjs"]
