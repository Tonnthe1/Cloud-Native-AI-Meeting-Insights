FROM node:20-alpine

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build \
    && npm prune --omit=dev \
    && chown -R node:node /app

ENV NODE_ENV=production
USER node
EXPOSE 3000

CMD ["npm", "start"]
