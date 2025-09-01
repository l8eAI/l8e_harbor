# Stage 1: Build the React application
# Use a specific Node.js LTS version for reproducibility
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package definitions
# Copying package-lock.json (if it exists) is crucial for reproducible builds.
COPY package.json package-lock.json* ./

# The error `npm ci` occurs because a `package-lock.json` is required but not found.
# Using `npm install` is more flexible and will resolve dependencies from `package.json`.
# We install all dependencies, including devDependencies, as they are needed for the build step.
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the application for production
RUN npm run build

# Stage 2: Serve the static files with a production-grade web server
FROM nginx:1.25-alpine

# Copy the built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the custom nginx configuration. This provides routing for a single-page app.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port 80 for the web server
EXPOSE 80

# Use the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]