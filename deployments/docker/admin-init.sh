#!/bin/bash
set -e

echo "Starting l8e-harbor admin initialization..."

# Configuration
API_BASE_URL=${API_BASE_URL:-"https://l8e-harbor-api:8443"}
UI_BASE_URL=${UI_BASE_URL:-"http://l8e-harbor-ui:3000"}
ADMIN_USERNAME=${ADMIN_USERNAME:-"admin"}
ADMIN_CREDS_FILE=${ADMIN_CREDS_FILE:-"/shared/admin-credentials.json"}
JWT_KEYS_DIR=${JWT_KEYS_DIR:-"/shared/jwt-keys"}

# Wait for API to be ready
echo "Waiting for l8e-harbor API at ${API_BASE_URL}..."
max_attempts=30
attempt=0

until curl -k -f "${API_BASE_URL}/health" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "ERROR: API not ready after $max_attempts attempts"
        exit 1
    fi
    echo "API not ready, waiting 10 seconds... (attempt $attempt/$max_attempts)"
    sleep 10
done

echo "✓ API is ready!"

# Check if admin already exists
if [ -f "$ADMIN_CREDS_FILE" ]; then
    echo "Admin credentials already exist at $ADMIN_CREDS_FILE"
    
    # Validate existing credentials
    EXISTING_PASSWORD=$(jq -r '.password' "$ADMIN_CREDS_FILE")
    LOGIN_RESPONSE=$(curl -k -s -X POST "${API_BASE_URL}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$ADMIN_USERNAME\", \"password\": \"$EXISTING_PASSWORD\"}" \
        --max-time 30)
    
    if echo "$LOGIN_RESPONSE" | jq -e '.access_token' >/dev/null 2>&1; then
        echo "✓ Existing admin credentials are valid"
        exit 0
    else
        echo "⚠ Existing admin credentials are invalid, regenerating..."
        rm -f "$ADMIN_CREDS_FILE"
    fi
fi

# Generate secure admin password (32 chars, alphanumeric + special chars)
ADMIN_PASSWORD=$(openssl rand -base64 48 | tr -d "=+/" | cut -c1-32)

# Generate JWT key pair
echo "Generating JWT key pair..."
mkdir -p "$JWT_KEYS_DIR"

# Generate RSA private key
JWT_PRIVATE_KEY_FILE="${JWT_KEYS_DIR}/jwt-private.pem"
JWT_PUBLIC_KEY_FILE="${JWT_KEYS_DIR}/jwt-public.pem"

# Use simpler openssl commands that work more reliably
openssl genrsa -out "$JWT_PRIVATE_KEY_FILE" 2048
openssl rsa -in "$JWT_PRIVATE_KEY_FILE" -pubout -out "$JWT_PUBLIC_KEY_FILE"

# Encode keys for API
JWT_PRIVATE_KEY_B64=$(base64 -w 0 < "$JWT_PRIVATE_KEY_FILE")
JWT_PUBLIC_KEY_B64=$(base64 -w 0 < "$JWT_PUBLIC_KEY_FILE")

echo "✓ JWT key pair generated"

# Configure l8e-harbor with JWT keys (if service supports dynamic config)
echo "Configuring JWT keys..."

# Create admin user via API
echo "Creating admin user '$ADMIN_USERNAME'..."

# Use a service token or direct API call for user creation
CREATE_USER_RESPONSE=$(curl -k -s -X POST "${API_BASE_URL}/api/v1/admin/users" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Init: true" \
    -d "{
        \"username\": \"$ADMIN_USERNAME\",
        \"password\": \"$ADMIN_PASSWORD\",
        \"role\": \"harbor-master\",
        \"meta\": {
            \"created_by\": \"docker-init\",
            \"created_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
        }
    }" --max-time 30) || CREATE_USER_RESPONSE=""

# If admin endpoint doesn't exist, try bootstrap endpoint
if [ -z "$CREATE_USER_RESPONSE" ] || echo "$CREATE_USER_RESPONSE" | grep -q "404"; then
    echo "Trying bootstrap endpoint..."
    CREATE_USER_RESPONSE=$(curl -k -s -X POST "${API_BASE_URL}/api/v1/bootstrap" \
        -H "Content-Type: application/json" \
        -d "{
            \"admin_username\": \"$ADMIN_USERNAME\",
            \"admin_password\": \"$ADMIN_PASSWORD\",
            \"jwt_private_key\": \"$JWT_PRIVATE_KEY_B64\",
            \"jwt_public_key\": \"$JWT_PUBLIC_KEY_B64\"
        }" --max-time 30) || CREATE_USER_RESPONSE=""
fi

if [ -z "$CREATE_USER_RESPONSE" ]; then
    echo "ERROR: Failed to create admin user"
    exit 1
fi

echo "✓ Admin user creation request sent"

# Wait a moment for user creation to complete
sleep 3

# Validate admin access
echo "Validating admin access..."
LOGIN_RESPONSE=$(curl -k -s -X POST "${API_BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$ADMIN_USERNAME\", \"password\": \"$ADMIN_PASSWORD\"}" \
    --max-time 30)

if echo "$LOGIN_RESPONSE" | jq -e '.access_token' >/dev/null 2>&1; then
    echo "✓ Admin user created and validated successfully"
    
    # Extract token for testing
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
    
    # Test basic API access
    USER_INFO=$(curl -k -s -X GET "${API_BASE_URL}/api/v1/user/me" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        --max-time 15)
    
    if echo "$USER_INFO" | jq -e '.username' >/dev/null 2>&1; then
        echo "✓ Admin API access validated"
    else
        echo "⚠ Admin user created but API access test failed"
    fi
else
    echo "ERROR: Failed to validate admin access"
    echo "Login response: $LOGIN_RESPONSE"
    exit 1
fi

# Store admin credentials securely
echo "Storing admin credentials..."
mkdir -p "$(dirname "$ADMIN_CREDS_FILE")"

cat > "$ADMIN_CREDS_FILE" << EOF
{
    "username": "$ADMIN_USERNAME",
    "password": "$ADMIN_PASSWORD",
    "role": "harbor-master",
    "api_url": "$API_BASE_URL",
    "ui_url": "$UI_BASE_URL",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "created_by": "docker-init",
    "login_instructions": {
        "web_ui": "Open $UI_BASE_URL and login with the above credentials",
        "cli": "Use 'harbor-ctl login --server=$API_BASE_URL --username=$ADMIN_USERNAME' and enter the password when prompted"
    }
}
EOF

# Set secure permissions
chmod 600 "$ADMIN_CREDS_FILE"

echo "✓ Admin credentials stored at: $ADMIN_CREDS_FILE"
echo ""
echo "=========================================="
echo "l8e-harbor Admin Setup Complete!"
echo "=========================================="
echo ""
echo "Admin Username: $ADMIN_USERNAME"
echo "Admin Password: [stored in credentials file]"
echo ""
echo "Web UI: $UI_BASE_URL"
echo "API URL: $API_BASE_URL"
echo ""
echo "To view credentials:"
echo "  docker-compose exec l8e-harbor-api cat /app/shared/admin-credentials.json"
echo ""
echo "To login via CLI:"
echo "  harbor-ctl login --server=$API_BASE_URL --username=$ADMIN_USERNAME"
echo ""
echo "JWT Keys stored at: $JWT_KEYS_DIR/"
echo "=========================================="

# Create a summary file for easy access
SUMMARY_FILE="/shared/admin-setup-summary.txt"
cat > "$SUMMARY_FILE" << EOF
l8e-harbor Admin Setup Summary
Generated: $(date)

Admin Username: $ADMIN_USERNAME
Web UI URL: $UI_BASE_URL
API URL: $API_BASE_URL

Credentials File: $ADMIN_CREDS_FILE
JWT Keys Directory: $JWT_KEYS_DIR

To view full credentials:
  docker-compose exec l8e-harbor-api cat /app/shared/admin-credentials.json

To login:
  1. Web UI: Open $UI_BASE_URL
  2. CLI: harbor-ctl login --server=$API_BASE_URL --username=$ADMIN_USERNAME
EOF

echo "✓ Setup summary saved to: $SUMMARY_FILE"