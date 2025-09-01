# l8e-harbor Docker Deployment

This directory contains Docker Compose configurations for running l8e-harbor in development and production environments.

## Files

- `docker-compose.yaml` - Simple setup with basic services
- `docker-compose.full.yml` - Complete setup with UI, admin initialization, and monitoring
- `admin-init.sh` - Bootstrap script for automatic admin account creation
- `config/harbor.yaml` - Configuration file for the l8e-harbor service

## Quick Start

### Full Setup (Recommended)

```bash
# Start all services with automatic admin setup
docker-compose -f docker-compose.full.yml up -d

# Check services are running
docker-compose -f docker-compose.full.yml ps

# Wait for admin initialization to complete
docker-compose -f docker-compose.full.yml logs admin-init
```

### Simple Setup

```bash
# Start basic services only
docker-compose up -d

# Check health
curl http://localhost:8443/health
```

## Admin Account Access

The full Docker Compose setup automatically creates a secure admin account during bootstrap.

### Getting Admin Credentials

**Method 1: View Complete Credentials**
```bash
# Get the complete admin credentials JSON
docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) \
  cat /app/shared/admin-credentials.json
```

**Method 2: Check Initialization Logs**
```bash
# View admin-init service logs
docker-compose -f docker-compose.full.yml logs admin-init

# Look for lines like:
# l8e-harbor Admin Setup Complete!
# Admin Username: admin
# Admin Password: [stored in credentials file]
```

**Method 3: View Setup Summary**
```bash
# Quick summary of admin setup
docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) \
  cat /app/shared/admin-setup-summary.txt
```

### Example Credentials Output

```json
{
    "username": "admin",
    "password": "p3pfQdcG5tKWNDjhNuVshm86kShbVdYv",
    "role": "harbor-master",
    "api_url": "http://l8e-harbor-api:8443",
    "ui_url": "http://localhost:3000",
    "created_at": "2025-09-01T05:48:08Z",
    "created_by": "docker-init",
    "login_instructions": {
        "web_ui": "Open http://localhost:3000 and login with the above credentials",
        "cli": "Use 'harbor-ctl login --server=http://l8e-harbor-api:8443 --username=admin' and enter the password when prompted"
    }
}
```

## Services

### l8e-harbor-api
- **Port**: 18443 (external) → 8443 (internal)
- **Health**: `curl http://localhost:18443/health`
- **API Docs**: `http://localhost:18443/docs`

### l8e-harbor-ui
- **Port**: 3000
- **URL**: `http://localhost:3000`
- **Login**: Use admin credentials from bootstrap

### admin-init
- **Purpose**: One-time admin account creation
- **Status**: Exits after completion
- **Output**: Credentials stored in shared volume

## First Login

### Web UI
1. Navigate to http://localhost:3000
2. Use admin credentials:
   - **Username**: `admin`
   - **Password**: [from credentials file]

### API
```bash
# Get admin password first (requires jq)
ADMIN_PASSWORD=$(docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) \
  cat /app/shared/admin-credentials.json | jq -r '.password')

# Alternative: Extract password without jq
ADMIN_PASSWORD=$(docker exec -u root $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) \
  cat /app/shared/admin-credentials.json | grep -o '"password": "[^"]*"' | cut -d'"' -f4)

# Login via API
curl -X POST http://localhost:18443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}"
```

### CLI (harbor-ctl)
```bash
harbor-ctl login --server=http://localhost:18443 --username=admin
# Enter password when prompted
```

## Troubleshooting

### Admin Account Issues

**Problem**: Can't find admin credentials
```bash
# Check if admin-init completed successfully
docker-compose -f docker-compose.full.yml logs admin-init | grep "Admin Setup Complete"

# Check if credentials file exists
docker exec $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-api) \
  ls -la /app/shared/
```

**Problem**: Admin login fails
```bash
# Verify API is running
curl http://localhost:18443/health

# Check admin-init logs for errors
docker-compose -f docker-compose.full.yml logs admin-init | tail -20

# Reset admin account (removes all data)
docker-compose -f docker-compose.full.yml down -v
docker-compose -f docker-compose.full.yml up -d
```

### Service Issues

**Problem**: Services won't start
```bash
# Check service logs
docker-compose -f docker-compose.full.yml logs

# Check specific service
docker-compose -f docker-compose.full.yml logs l8e-harbor-api

# Rebuild and restart
docker-compose -f docker-compose.full.yml build
docker-compose -f docker-compose.full.yml up -d
```

**Problem**: UI can't connect to API
```bash
# Check API is reachable
curl http://localhost:18443/health

# Check UI logs
docker-compose -f docker-compose.full.yml logs l8e-harbor-ui

# Verify environment variables
docker exec $(docker-compose -f docker-compose.full.yml ps -q l8e-harbor-ui) env | grep API
```

## Development

### Making Changes

```bash
# Rebuild specific service
docker-compose -f docker-compose.full.yml build l8e-harbor-api

# Restart service
docker-compose -f docker-compose.full.yml restart l8e-harbor-api

# View logs
docker-compose -f docker-compose.full.yml logs -f l8e-harbor-api
```

### Reset Everything

```bash
# Stop and remove all containers, volumes, and networks
docker-compose -f docker-compose.full.yml down -v

# Remove images (optional)
docker-compose -f docker-compose.full.yml down --rmi all

# Start fresh
docker-compose -f docker-compose.full.yml up -d
```

## Security Notes

- Admin password is randomly generated (32+ characters)
- Credentials stored with restrictive permissions (600)
- JWT tokens expire after 15 minutes by default
- TLS certificates are auto-generated for development
- All services run as non-root users

## Production Considerations

- Use external secrets management (Vault, AWS Secrets Manager)
- Configure proper TLS certificates
- Set up monitoring and logging
- Use multi-replica deployment
- Configure backup and disaster recovery
- Enable audit logging