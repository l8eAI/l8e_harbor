#!/bin/bash
# l8e-harbor Deployment Validation Script
# Tests admin credential generation and basic functionality across deployment methods

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_TYPE="${1:-}"
API_URL="${2:-}"
ADMIN_CREDS_PATH="${3:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Usage information
show_usage() {
    cat << EOF
l8e-harbor Deployment Validation Script

Usage:
    $0 <deployment-type> [api-url] [admin-creds-path]

Deployment Types:
    kubernetes    - Validate Kubernetes/Helm deployment
    docker        - Validate Docker Compose deployment
    vm            - Validate VM/systemd deployment

Examples:
    # Kubernetes validation
    $0 kubernetes https://l8e-harbor-api.default.svc.cluster.local:8443

    # Docker validation
    $0 docker https://localhost:8443 ./shared/admin-credentials.json

    # VM validation
    $0 vm https://localhost:8443 /var/lib/l8e-harbor/admin-credentials.json

EOF
}

# Detect credentials and API URL based on deployment type
detect_deployment_config() {
    case "$DEPLOYMENT_TYPE" in
        kubernetes|k8s)
            log "Detecting Kubernetes deployment configuration..."
            
            # Try to get API URL from service
            if kubectl get svc l8e-harbor-api >/dev/null 2>&1; then
                CLUSTER_IP=$(kubectl get svc l8e-harbor-api -o jsonpath='{.spec.clusterIP}')
                PORT=$(kubectl get svc l8e-harbor-api -o jsonpath='{.spec.ports[0].port}')
                API_URL="${API_URL:-https://$CLUSTER_IP:$PORT}"
            else
                API_URL="${API_URL:-https://localhost:8443}"
            fi
            
            # Get admin credentials from secret
            if kubectl get secret l8e-harbor-admin-creds >/dev/null 2>&1; then
                ADMIN_USERNAME=$(kubectl get secret l8e-harbor-admin-creds -o jsonpath='{.data.username}' | base64 -d)
                ADMIN_PASSWORD=$(kubectl get secret l8e-harbor-admin-creds -o jsonpath='{.data.password}' | base64 -d)
            else
                error "Admin credentials secret not found: l8e-harbor-admin-creds"
            fi
            ;;
            
        docker)
            log "Detecting Docker Compose deployment configuration..."
            API_URL="${API_URL:-https://localhost:8443}"
            ADMIN_CREDS_PATH="${ADMIN_CREDS_PATH:-./shared/admin-credentials.json}"
            
            if [[ -f "$ADMIN_CREDS_PATH" ]]; then
                ADMIN_USERNAME=$(jq -r '.username' "$ADMIN_CREDS_PATH")
                ADMIN_PASSWORD=$(jq -r '.password' "$ADMIN_CREDS_PATH")
            else
                error "Admin credentials file not found: $ADMIN_CREDS_PATH"
            fi
            ;;
            
        vm)
            log "Detecting VM deployment configuration..."
            API_URL="${API_URL:-https://localhost:8443}"
            ADMIN_CREDS_PATH="${ADMIN_CREDS_PATH:-/var/lib/l8e-harbor/admin-credentials.json}"
            
            if [[ -f "$ADMIN_CREDS_PATH" ]]; then
                ADMIN_USERNAME=$(jq -r '.username' "$ADMIN_CREDS_PATH")
                ADMIN_PASSWORD=$(jq -r '.password' "$ADMIN_CREDS_PATH")
            else
                error "Admin credentials file not found: $ADMIN_CREDS_PATH"
            fi
            ;;
            
        *)
            error "Unknown deployment type: $DEPLOYMENT_TYPE"
            show_usage
            exit 1
            ;;
    esac
    
    log "Configuration detected:"
    log "  Deployment Type: $DEPLOYMENT_TYPE"
    log "  API URL: $API_URL"
    log "  Admin Username: $ADMIN_USERNAME"
}

# Test API health endpoint
test_api_health() {
    log "Testing API health endpoint..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -k -f "$API_URL/health" >/dev/null 2>&1; then
            success "✓ API health check passed"
            return 0
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            log "API not ready, waiting 10 seconds... (attempt $attempt/$max_attempts)"
            sleep 10
        fi
    done
    
    error "✗ API health check failed after $max_attempts attempts"
    return 1
}

# Test admin authentication
test_admin_auth() {
    log "Testing admin authentication..."
    
    local login_response
    login_response=$(curl -k -s -X POST "$API_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$ADMIN_USERNAME\", \"password\": \"$ADMIN_PASSWORD\"}" \
        --max-time 30)
    
    if echo "$login_response" | jq -e '.access_token' >/dev/null 2>&1; then
        ACCESS_TOKEN=$(echo "$login_response" | jq -r '.access_token')
        success "✓ Admin authentication successful"
        return 0
    else
        error "✗ Admin authentication failed"
        error "Response: $login_response"
        return 1
    fi
}

# Test authenticated API access
test_authenticated_access() {
    log "Testing authenticated API access..."
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        error "No access token available"
        return 1
    fi
    
    # Test user info endpoint
    local user_info
    user_info=$(curl -k -s -X GET "$API_URL/api/v1/user/me" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        --max-time 15)
    
    if echo "$user_info" | jq -e '.username' >/dev/null 2>&1; then
        local username=$(echo "$user_info" | jq -r '.username')
        local role=$(echo "$user_info" | jq -r '.role')
        success "✓ Authenticated API access successful"
        log "  User: $username"
        log "  Role: $role"
    else
        error "✗ Authenticated API access failed"
        error "Response: $user_info"
        return 1
    fi
    
    # Test routes endpoint
    local routes_response
    routes_response=$(curl -k -s -X GET "$API_URL/api/v1/routes" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        --max-time 15)
    
    if echo "$routes_response" | jq -e 'type' >/dev/null 2>&1; then
        local route_count=$(echo "$routes_response" | jq '. | length')
        success "✓ Routes API access successful"
        log "  Routes count: $route_count"
    else
        warn "⚠ Routes API access may have issues"
        log "Response: $routes_response"
    fi
}

# Test route creation and management
test_route_management() {
    log "Testing route creation and management..."
    
    if [[ -z "$ACCESS_TOKEN" ]]; then
        error "No access token available"
        return 1
    fi
    
    # Create a test route
    local test_route_spec='{
        "id": "test-route-validation",
        "path": "/test-validation",
        "methods": ["GET"],
        "backends": [
            {
                "url": "https://httpbin.org",
                "weight": 1
            }
        ],
        "meta": {
            "description": "Test route for deployment validation",
            "created_by": "validation-script"
        }
    }'
    
    local create_response
    create_response=$(curl -k -s -X POST "$API_URL/api/v1/routes" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$test_route_spec" \
        --max-time 15)
    
    if echo "$create_response" | jq -e '.id' >/dev/null 2>&1; then
        success "✓ Route creation successful"
        
        # Test route retrieval
        local get_response
        get_response=$(curl -k -s -X GET "$API_URL/api/v1/routes/test-route-validation" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            --max-time 15)
        
        if echo "$get_response" | jq -e '.id' >/dev/null 2>&1; then
            success "✓ Route retrieval successful"
        else
            warn "⚠ Route retrieval failed"
        fi
        
        # Clean up: delete test route
        curl -k -s -X DELETE "$API_URL/api/v1/routes/test-route-validation" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            --max-time 15 >/dev/null 2>&1
        
        log "✓ Test route cleaned up"
    else
        warn "⚠ Route creation failed (this may be expected if backend is not accessible)"
        log "Response: $create_response"
    fi
}

# Test JWT key validation
test_jwt_keys() {
    log "Testing JWT key validation..."
    
    case "$DEPLOYMENT_TYPE" in
        kubernetes)
            if kubectl get secret l8e-harbor-jwt-keys >/dev/null 2>&1; then
                success "✓ JWT keys secret exists in Kubernetes"
                
                # Validate key format
                local private_key
                private_key=$(kubectl get secret l8e-harbor-jwt-keys -o jsonpath='{.data.private-key}' | base64 -d | head -1)
                if echo "$private_key" | grep -q "BEGIN PRIVATE KEY"; then
                    success "✓ JWT private key format is valid"
                else
                    warn "⚠ JWT private key format may be invalid"
                fi
            else
                warn "⚠ JWT keys secret not found in Kubernetes"
            fi
            ;;
            
        docker)
            local jwt_keys_dir="./shared/jwt-keys"
            if [[ -f "$jwt_keys_dir/jwt-private.pem" && -f "$jwt_keys_dir/jwt-public.pem" ]]; then
                success "✓ JWT key files exist"
                
                if openssl pkey -in "$jwt_keys_dir/jwt-private.pem" -noout 2>/dev/null; then
                    success "✓ JWT private key is valid"
                else
                    warn "⚠ JWT private key validation failed"
                fi
            else
                warn "⚠ JWT key files not found in $jwt_keys_dir"
            fi
            ;;
            
        vm)
            local jwt_keys_dir="/var/lib/l8e-harbor/jwt-keys"
            if [[ -f "$jwt_keys_dir/jwt-private.pem" && -f "$jwt_keys_dir/jwt-public.pem" ]]; then
                success "✓ JWT key files exist"
                
                if openssl pkey -in "$jwt_keys_dir/jwt-private.pem" -noout 2>/dev/null; then
                    success "✓ JWT private key is valid"
                else
                    warn "⚠ JWT private key validation failed"
                fi
            else
                warn "⚠ JWT key files not found in $jwt_keys_dir"
            fi
            ;;
    esac
}

# Test metrics endpoint
test_metrics() {
    log "Testing metrics endpoint..."
    
    local metrics_response
    metrics_response=$(curl -k -s "$API_URL/metrics" --max-time 10)
    
    if echo "$metrics_response" | grep -q "# HELP"; then
        success "✓ Metrics endpoint is accessible"
        local metric_count=$(echo "$metrics_response" | grep -c "# HELP")
        log "  Metrics available: $metric_count"
    else
        warn "⚠ Metrics endpoint not accessible or not properly formatted"
    fi
}

# Generate validation report
generate_report() {
    log "Generating validation report..."
    
    local report_file="l8e-harbor-validation-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
l8e-harbor Deployment Validation Report
Generated: $(date)
Deployment Type: $DEPLOYMENT_TYPE
API URL: $API_URL

========================================
VALIDATION RESULTS
========================================

Admin Credentials:
  Username: $ADMIN_USERNAME
  Password: [REDACTED]
  Credentials Source: $([[ "$DEPLOYMENT_TYPE" == "kubernetes" ]] && echo "Kubernetes Secret" || echo "$ADMIN_CREDS_PATH")

Test Results:
$(grep -E "✓|✗|⚠" "$0.log" 2>/dev/null || echo "  [Log file not available]")

========================================
NEXT STEPS
========================================

1. Verify all tests passed (look for ✓ symbols above)
2. Address any warnings (⚠) or errors (✗)
3. Test UI access if deployed separately
4. Configure monitoring and alerting
5. Set up backup procedures for critical data
6. Review security settings for production use

For issues, check:
- Service logs
- Network connectivity
- SSL certificate validity
- Resource limits and availability

========================================
EOF
    
    success "✓ Validation report generated: $report_file"
}

# Main validation function
run_validation() {
    log "Starting l8e-harbor deployment validation..."
    
    # Redirect output to log file for report generation
    exec 1> >(tee "$0.log")
    exec 2>&1
    
    detect_deployment_config
    
    # Run validation tests
    test_api_health || exit 1
    test_admin_auth || exit 1
    test_authenticated_access
    test_route_management
    test_jwt_keys
    test_metrics
    
    success "All validation tests completed!"
    generate_report
    
    # Clean up log file
    rm -f "$0.log" 2>/dev/null || true
}

# Handle command line arguments
if [[ $# -eq 0 || "$1" == "--help" || "$1" == "-h" ]]; then
    show_usage
    exit 0
fi

DEPLOYMENT_TYPE="$1"
API_URL="$2"
ADMIN_CREDS_PATH="$3"

# Validate required tools
for tool in curl jq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        error "Required tool not found: $tool"
        exit 1
    fi
done

# Additional tool checks based on deployment type
case "$DEPLOYMENT_TYPE" in
    kubernetes|k8s)
        if ! command -v kubectl >/dev/null 2>&1; then
            error "kubectl is required for Kubernetes validation"
            exit 1
        fi
        ;;
esac

# Run validation
run_validation