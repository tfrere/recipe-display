# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Copier les fichiers de dépendances
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

# Copier le code source du client
COPY . .

# Build l'application
ENV NODE_ENV=production
ARG VITE_API_ENDPOINT
ENV VITE_API_ENDPOINT=$VITE_API_ENDPOINT
RUN yarn build

# Production stage
FROM nginx:alpine

# Copier les fichiers buildés dans le répertoire par défaut de Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copier le fichier de configuration Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Exposer le port
EXPOSE 80

# Démarrer Nginx
CMD ["nginx", "-g", "daemon off;"]
