# Build stage
FROM dart:stable AS build

WORKDIR /app

# Copy pubspec files first for better caching
COPY pubspec.* ./

# Get dependencies
RUN dart pub get

# Copy source code
COPY . .

# Generate Serverpod code (this creates the generated/ directory)
RUN dart run serverpod generate || true

# Build the server executable
RUN dart compile exe bin/main.dart -o bin/server

# Runtime stage - minimal image
FROM debian:bookworm-slim

# Install required runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the compiled server binary
COPY --from=build /app/bin/server /app/bin/server

# Copy config files
COPY --from=build /app/config /app/config

# Expose ports: 8080 for API, 8081 for Insights
EXPOSE 8080 8081

# Run the server
CMD ["/app/bin/server"]
