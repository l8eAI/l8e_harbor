#!/bin/bash
# l8e-harbor Admin Setup Testing Script
# Comprehensive test suite for admin credential generation across all deployment methods

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_NAMESPACE="l8e-harbor-test"
TEST_PREFIX="l8e-test"

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

# Cleanup function
cleanup() {
    log "Cleaning up test resources..."
    
    # Kubernetes cleanup
    kubectl delete namespace "$TEST_NAMESPACE" --ignore-not-found=true 2>/dev/null || true
    
    # Docker cleanup  
    docker-compose -f "$PROJECT_ROOT/deployments/docker/docker-compose.full.yml" -p "$TEST_PREFIX" down -v 2>/dev/null || true
    docker volume prune -f 2>/dev/null || true
    
    # Remove test files
    rm -rf "/tmp/l8e-harbor-test-*" 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT

# Test Kubernetes admin setup
test_kubernetes_admin_setup() {
    log "Testing Kubernetes admin credential generation..."
    
    # Create test namespace
    kubectl create namespace "$TEST_NAMESPACE" 2>/dev/null || true
    
    # Apply the admin setup job with test namespace
    local temp_job="/tmp/l8e-harbor-test-admin-job.yaml"
    sed "s/{{ \.Values\.namespace | default \"l8e-harbor\" }}/$TEST_NAMESPACE/g" \
        "$PROJECT_ROOT/deployments/kubernetes/admin-setup-job.yaml" > "$temp_job"
    sed -i.bak "s/{{ include \"l8e-harbor\.apiUrl\" \. }}/https:\/\/l8e-harbor-api:8443/g" "$temp_job"
    sed -i.bak "s/{{ include \"l8e-harbor\.uiUrl\" \. }}/http:\/\/l8e-harbor-ui:3000/g" "$temp_job"
    
    # Create a mock API service for testing
    kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: l8e-harbor-api
  namespace: $TEST_NAMESPACE
spec:
  selector:
    app: mock-api
  ports:
  - port: 8443
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mock-api
  namespace: $TEST_NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mock-api
  template:
    metadata:
      labels:
        app: mock-api
    spec:
      containers:
      - name: mock-api
        image: nginx:alpine
        ports:
        - containerPort: 8080
        command: ["/bin/sh"]
        args:
        - -c
        - |
          cat > /etc/nginx/nginx.conf <<'NGINX_EOF'
          events { worker_connections 1024; }
          http {
            server {
              listen 8080;
              location /health { return 200 "OK"; }
              location /api/v1/auth/login { return 200 '{"access_token":"test-token"}'; }
              location /api/v1/users { return 201 '{"username":"admin"}'; }
              location /api/v1/bootstrap { return 201 '{"status":"success"}'; }
            }
          }
          NGINX_EOF
          nginx -g 'daemon off;'
EOF
    
    # Wait for mock API to be ready
    kubectl wait --for=condition=available --timeout=60s deployment/mock-api -n "$TEST_NAMESPACE"
    
    # Apply the admin setup job
    kubectl apply -f "$temp_job" -n "$TEST_NAMESPACE"
    
    # Wait for job completion
    local job_name="l8e-harbor-admin-setup"
    log "Waiting for admin setup job to complete..."
    
    local max_wait=300  # 5 minutes
    local waited=0
    while [ $waited -lt $max_wait ]; do
        local job_status=$(kubectl get job "$job_name" -n "$TEST_NAMESPACE" -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "")
        
        if [[ "$job_status" == "Complete" ]]; then
            success "✓ Kubernetes admin setup job completed successfully"
            break
        elif [[ "$job_status" == "Failed" ]]; then
            error "✗ Kubernetes admin setup job failed"
            kubectl logs job/"$job_name" -n "$TEST_NAMESPACE" || true
            return 1
        fi
        
        sleep 10
        waited=$((waited + 10))
        log "Waiting for job completion... ($waited/${max_wait}s)"
    done
    
    if [ $waited -ge $max_wait ]; then
        error "✗ Kubernetes admin setup job timed out"
        kubectl logs job/"$job_name" -n "$TEST_NAMESPACE" || true
        return 1
    fi
    
    # Verify admin credentials secret exists
    if kubectl get secret l8e-harbor-admin-creds -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
        success "✓ Admin credentials secret created"
        
        # Verify secret contents
        local username=$(kubectl get secret l8e-harbor-admin-creds -n "$TEST_NAMESPACE" -o jsonpath='{.data.username}' | base64 -d)
        local password=$(kubectl get secret l8e-harbor-admin-creds -n "$TEST_NAMESPACE" -o jsonpath='{.data.password}' | base64 -d)
        
        if [[ -n "$username" && -n "$password" ]]; then
            success "✓ Admin credentials are properly populated"
            log "  Username: $username"
            log "  Password: [${#password} characters]"
        else
            error "✗ Admin credentials are empty or invalid"
            return 1
        fi
    else
        error "✗ Admin credentials secret not found"
        return 1
    fi
    
    # Verify JWT keys secret exists
    if kubectl get secret l8e-harbor-jwt-keys -n "$TEST_NAMESPACE" >/dev/null 2>&1; then
        success "✓ JWT keys secret created"
        
        # Verify key format
        local private_key=$(kubectl get secret l8e-harbor-jwt-keys -n "$TEST_NAMESPACE" -o jsonpath='{.data.private-key}' | base64 -d | head -1)
        if echo "$private_key" | grep -q "BEGIN PRIVATE KEY"; then
            success "✓ JWT private key format is valid"
        else
            warn "⚠ JWT private key format may be invalid"
        fi
    else
        error "✗ JWT keys secret not found"
        return 1
    fi
    
    # Show job logs for debugging
    log "Admin setup job logs:"
    kubectl logs job/"$job_name" -n "$TEST_NAMESPACE" | head -20 || true
    
    success "✓ Kubernetes admin setup test passed"
    return 0
}

# Test Docker admin setup
test_docker_admin_setup() {
    log "Testing Docker Compose admin credential generation..."
    
    local test_dir="/tmp/l8e-harbor-test-docker"
    mkdir -p "$test_dir"
    cd "$test_dir"
    
    # Copy necessary files
    cp -r "$PROJECT_ROOT/deployments/docker"/* .
    
    # Create a test docker-compose file with mock services
    cat > docker-compose.test.yml << 'EOF'
version: '3.8'

services:
  # Mock API service for testing
  mock-api:
    image: nginx:alpine
    ports:
      - "18443:8080"
    command: |
      /bin/sh -c "
        cat > /etc/nginx/nginx.conf <<'NGINX_EOF'
        events { worker_connections 1024; }
        http {
          server {
            listen 8080;
            location /health { return 200 'OK'; add_header Content-Type text/plain; }
            location /api/v1/auth/login { 
              return 200 '{\"access_token\":\"test-token\"}'; 
              add_header Content-Type application/json;
            }
            location /api/v1/admin/users { 
              return 201 '{\"username\":\"admin\"}'; 
              add_header Content-Type application/json;
            }
            location /api/v1/bootstrap { 
              return 201 '{\"status\":\"success\"}'; 
              add_header Content-Type application/json;
            }
          }
        }
        NGINX_EOF
        nginx -g 'daemon off;'
      "
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 5s
      timeout: 3s
      retries: 5

  # Admin initialization service
  admin-init:
    build:
      context: .
      dockerfile: admin-init.dockerfile
    environment:
      - API_BASE_URL=http://mock-api:8080
      - UI_BASE_URL=http://localhost:3000
      - ADMIN_USERNAME=admin
      - ADMIN_CREDS_FILE=/shared/admin-credentials.json
      - JWT_KEYS_DIR=/shared/jwt-keys
    volumes:
      - shared-data:/shared
    depends_on:
      mock-api:
        condition: service_healthy
    restart: "no"

volumes:
  shared-data:
    driver: local
EOF
    
    # Build and run the test
    log "Building admin initialization container..."
    docker-compose -f docker-compose.test.yml -p "$TEST_PREFIX" build --no-cache
    
    log "Starting admin initialization test..."
    docker-compose -f docker-compose.test.yml -p "$TEST_PREFIX" up --abort-on-container-exit
    
    # Check if admin-init container completed successfully
    local exit_code=$(docker-compose -f docker-compose.test.yml -p "$TEST_PREFIX" ps -q admin-init | xargs docker inspect --format='{{.State.ExitCode}}')
    
    if [[ "$exit_code" == "0" ]]; then
        success "✓ Docker admin initialization completed successfully"
    else
        error "✗ Docker admin initialization failed with exit code: $exit_code"
        log "Container logs:"
        docker-compose -f docker-compose.test.yml -p "$TEST_PREFIX" logs admin-init || true
        return 1
    fi
    
    # Verify credentials file was created
    local creds_file
    creds_file=$(docker-compose -f docker-compose.test.yml -p "$TEST_PREFIX" run --rm admin-init cat /shared/admin-credentials.json 2>/dev/null || echo "")
    
    if [[ -n "$creds_file" ]]; then
        success "✓ Admin credentials file created"
        
        # Verify JSON structure
        if echo "$creds_file" | jq -e '.username' >/dev/null 2>&1; then
            local username=$(echo "$creds_file" | jq -r '.username')
            local password=$(echo "$creds_file" | jq -r '.password')
            success "✓ Admin credentials are properly structured"
            log "  Username: $username"
            log "  Password: [${#password} characters]"
        else
            error "✗ Admin credentials file is not valid JSON"
            log "Content: $creds_file"
            return 1
        fi
    else
        error "✗ Admin credentials file not found"
        return 1
    fi
    
    # Verify JWT keys were created
    local private_key
    private_key=$(docker-compose -f docker-compose.test.yml -p "$TEST_PREFIX" run --rm admin-init cat /shared/jwt-keys/jwt-private.pem 2>/dev/null || echo "")
    
    if [[ -n "$private_key" ]]; then
        success "✓ JWT keys created"
        
        if echo "$private_key" | grep -q "BEGIN PRIVATE KEY"; then
            success "✓ JWT private key format is valid"
        else
            warn "⚠ JWT private key format may be invalid"
        fi
    else
        error "✗ JWT keys not found"
        return 1
    fi
    
    success "✓ Docker admin setup test passed"
    return 0
}

# Test VM installation script
test_vm_install_script() {
    log "Testing VM installation script (dry run)..."
    
    local install_script="$PROJECT_ROOT/deployments/vm/install.sh"
    
    # Test script syntax
    if bash -n "$install_script"; then
        success "✓ VM install script syntax is valid"
    else
        error "✗ VM install script has syntax errors"
        return 1
    fi
    
    # Test OS detection function
    log "Testing OS detection..."
    if bash -c "source '$install_script'; detect_os"; then
        success "✓ OS detection works"
    else
        warn "⚠ OS detection may have issues on this platform"
    fi
    
    # Test dependency detection
    log "Testing dependency availability..."
    local missing_deps=""
    for dep in curl wget jq openssl python3; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing_deps="$missing_deps $dep"
        fi
    done
    
    if [[ -z "$missing_deps" ]]; then
        success "✓ All required dependencies are available"
    else
        warn "⚠ Missing dependencies (this is expected in some environments): $missing_deps"
    fi
    
    # Test configuration generation functions
    local test_dir="/tmp/l8e-harbor-test-vm"
    mkdir -p "$test_dir"
    cd "$test_dir"
    
    # Mock some functions for testing
    export L8E_CONFIG_DIR="$test_dir/config"
    export L8E_DATA_DIR="$test_dir/data"
    mkdir -p "$L8E_CONFIG_DIR" "$L8E_DATA_DIR"
    
    # Test config creation (extract function and run it)
    log "Testing configuration file generation..."
    if bash -c "
        source '$install_script'
        API_PORT=8443
        UI_PORT=3000
        create_config
    "; then
        if [[ -f "$L8E_CONFIG_DIR/harbor.yaml" ]]; then
            success "✓ Configuration file generation works"
            
            # Validate YAML structure
            if python3 -c "import yaml; yaml.safe_load(open('$L8E_CONFIG_DIR/harbor.yaml'))" 2>/dev/null; then
                success "✓ Generated configuration is valid YAML"
            else
                warn "⚠ Generated configuration may have YAML syntax issues"
            fi
        else
            error "✗ Configuration file was not created"
            return 1
        fi
    else
        error "✗ Configuration file generation failed"
        return 1
    fi
    
    success "✓ VM installation script test passed"
    return 0
}

# Run all tests
run_all_tests() {
    log "Starting comprehensive admin setup testing..."
    
    local failed_tests=""
    
    # Test 1: Kubernetes admin setup
    if test_kubernetes_admin_setup; then
        success "✓ Kubernetes test passed"
    else
        failed_tests="$failed_tests kubernetes"
        warn "⚠ Kubernetes test failed"
    fi
    
    # Test 2: Docker admin setup
    if test_docker_admin_setup; then
        success "✓ Docker test passed"
    else
        failed_tests="$failed_tests docker"
        warn "⚠ Docker test failed"
    fi
    
    # Test 3: VM install script
    if test_vm_install_script; then
        success "✓ VM script test passed"
    else
        failed_tests="$failed_tests vm"
        warn "⚠ VM script test failed"
    fi
    
    # Summary
    log "Test summary:"
    if [[ -z "$failed_tests" ]]; then
        success "✓ All admin setup tests passed!"
        return 0
    else
        warn "⚠ Some tests failed: $failed_tests"
        warn "This may be expected in some environments. Check individual test results above."
        return 1
    fi
}

# Usage information
show_usage() {
    cat << EOF
l8e-harbor Admin Setup Testing Script

Usage:
    $0 [test-type]

Test Types:
    kubernetes    - Test Kubernetes admin credential generation
    docker        - Test Docker Compose admin setup
    vm           - Test VM installation script (dry run)
    all          - Run all tests (default)

Prerequisites:
    - kubectl (for Kubernetes tests)
    - docker and docker-compose (for Docker tests)
    - Standard Unix tools (curl, jq, openssl, python3)

Examples:
    $0                    # Run all tests
    $0 all                # Run all tests
    $0 kubernetes         # Test only Kubernetes setup
    $0 docker            # Test only Docker setup
    $0 vm                # Test only VM script

EOF
}

# Main execution
main() {
    local test_type="${1:-all}"
    
    case "$test_type" in
        kubernetes|k8s)
            test_kubernetes_admin_setup
            ;;
        docker)
            test_docker_admin_setup
            ;;
        vm)
            test_vm_install_script
            ;;
        all|"")
            run_all_tests
            ;;
        --help|-h|help)
            show_usage
            exit 0
            ;;
        *)
            error "Unknown test type: $test_type"
            show_usage
            exit 1
            ;;
    esac
}

# Validate required tools
validate_prerequisites() {
    local missing_tools=""
    
    # Check basic tools
    for tool in curl jq bash; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools="$missing_tools $tool"
        fi
    done
    
    if [[ -n "$missing_tools" ]]; then
        error "Missing required tools: $missing_tools"
        error "Please install these tools before running tests"
        exit 1
    fi
}

# Check if running directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    validate_prerequisites
    main "$@"
fi