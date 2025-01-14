FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy source code
COPY . .

# Build the app with the API endpoint from build arg
ARG VITE_API_ENDPOINT
ENV VITE_API_ENDPOINT=$VITE_API_ENDPOINT
RUN yarn build

# Install serve globally with yarn
RUN yarn global add serve

# Start the application
CMD serve -s dist -p ${PORT:-3000}
