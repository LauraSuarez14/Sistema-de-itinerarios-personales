# Build multi-stage: Angular (Node) compila el bundle de produccion, nginx
# solo sirve los estaticos resultantes (nunca corre Node en el contenedor
# final).
FROM node:20-alpine AS build
WORKDIR /app

# Copia solo los manifiestos primero para aprovechar la cache de capas de
# Docker: `npm ci` no se vuelve a correr si package*.json no cambio.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build -- --configuration production

# ------------------------------------------------------------------------
FROM nginx:1.27-alpine
COPY --from=build /app/dist/itinerarios-frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
