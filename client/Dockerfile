FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy source code
COPY . .

# Build the app
RUN yarn build

# Install serve globally with yarn
RUN yarn global add serve

# Print environment for debugging
CMD echo "Starting server on port ${PORT:-3000}" && \
    serve -s dist -l ${PORT:-3000}
