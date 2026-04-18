# Etapa 1: Build del SPA
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .

# En Docker, el frontend hace peticiones al mismo host (Nginx proxy)
ENV VITE_API_URL=""
RUN npm run build

# Etapa 2: Servir con Nginx liviano
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
