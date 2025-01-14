# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Copier les fichiers de dépendances
COPY package.json yarn.lock ./
RUN yarn install --production --frozen-lockfile

# Copier le code source du client
COPY . .

# Build l'application
ENV NODE_ENV=production
ARG VITE_API_ENDPOINT
ENV VITE_API_ENDPOINT=$VITE_API_ENDPOINT
RUN yarn build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copier les fichiers nécessaires depuis l'étape de build
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/yarn.lock ./yarn.lock

# Exposer le port
ENV PORT=3000
EXPOSE 3000

# Démarrer le serveur de preview Vite
CMD ["yarn", "preview", "--host", "--port", "3000"]
