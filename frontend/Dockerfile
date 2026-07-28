FROM node:20-alpine

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build \
    && chown -R node:node /app

USER node
EXPOSE 3000

CMD ["npm", "start"]
