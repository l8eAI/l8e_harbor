#!/bin/sh
set -e

# Default values
API_BASE_URL=${API_BASE_URL:-"https://localhost:8443"}

# Replace environment variables in nginx config
envsubst '${API_BASE_URL}' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf.tmp && mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

# Create runtime configuration file for the client
cat > /usr/share/nginx/html/config.json << EOF
{
  "apiBaseUrl": "${API_BASE_URL}",
  "version": "0.1.0",
  "buildTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "l8e-harbor UI starting with API_BASE_URL: ${API_BASE_URL}"

# Execute the original command
exec "$@"