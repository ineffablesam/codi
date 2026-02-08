# Build stage
FROM ghcr.io/cirruslabs/flutter:stable AS build

ARG SERVERPOD_URL=http://localhost:8080/
ENV SERVERPOD_URL=$SERVERPOD_URL

WORKDIR /app

# Copy pubspec files first for dependency caching
COPY pubspec.* ./

# Copy local client package dependency
COPY ../{{PROJECT_NAME}}_client ../{{PROJECT_NAME}}_client

# Get dependencies
RUN flutter pub get

# Copy source code
COPY . .

# Build web app with Serverpod URL configured
RUN flutter build web --release --dart-define=SERVERPOD_URL=$SERVERPOD_URL

# Runtime stage with nginx
FROM nginx:alpine

# Copy built web app
COPY --from=build /app/build/web /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
