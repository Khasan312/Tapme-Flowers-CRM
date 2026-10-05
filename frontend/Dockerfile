FROM node:22-bookworm-slim AS build
WORKDIR /frontend
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM caddy:2.10-alpine
COPY --from=build /frontend/dist /srv/frontend
