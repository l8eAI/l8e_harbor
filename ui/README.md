# l8e-harbor UI Control Plane

A modern React-based web interface for managing l8e-harbor gateway configurations, designed following Kubernetes ecosystem patterns for familiarity and developer productivity.

## Features

### ✅ **Core Functionality**
- **YAML-First Route Management** - Edit routes with syntax highlighting and validation
- **Integrated Route Testing** - Test endpoints directly from the UI
- **System Status Dashboard** - Monitor health and performance at a glance
- **Authentication Integration** - Works with all l8e-harbor auth adapters
- **Kubernetes-Inspired UX** - Familiar navigation and patterns

### ✅ **Developer Experience**
- **Monaco Editor** - VS Code-quality YAML editing with auto-completion
- **Real-time Validation** - Instant feedback on configuration errors
- **Route Preview** - Visual preview of route configuration before saving
- **Request Testing Tool** - Built-in HTTP client for endpoint testing
- **Responsive Design** - Works on desktop and mobile devices

### ✅ **Production Ready**
- **Role-Based Access** - Harbor-master and captain role support
- **Security Headers** - CSP, XSS protection, HTTPS enforcement
- **Docker Support** - Containerized deployment with nginx
- **Performance Optimized** - Code splitting, lazy loading, caching

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and run
docker-compose up --build

# Access at http://localhost:3000
```

### Option 2: Development Server

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Access at http://localhost:3000
```

### Option 3: Production Build

```bash
# Build for production
npm run build

# Serve with nginx or any static server
npm run preview
```

## Configuration

### Environment Variables

```bash
# API endpoint (development)
VITE_API_BASE_URL=https://localhost:8443

# API endpoint (production - set in nginx config)
API_BASE_URL=https://l8e-harbor.example.com
```

### Runtime Configuration

The UI can be configured at runtime using environment variables in the Docker container:

```yaml
# docker-compose.yml
services:
  l8e-harbor-ui:
    image: l8e-harbor-ui:latest
    environment:
      - API_BASE_URL=https://your-l8e-harbor-instance.com
    ports:
      - "3000:80"
```

## User Guide

### 1. Authentication

The UI supports all l8e-harbor authentication methods:

- **Local Users**: Username/password login
- **Kubernetes ServiceAccounts**: Automatic token-based auth
- **OIDC/OAuth2**: External identity provider integration

### 2. Route Management

**Creating Routes:**
1. Navigate to **Routes** → **Create Route**
2. Use the YAML editor to define your route
3. Preview configuration in the right panel
4. Click **Create Route** to save

**Editing Routes:**
1. Click on any route in the routes list
2. Click **Edit Route** in the route detail view
3. Modify YAML configuration
4. Save changes

**Testing Routes:**
1. Click **Test Route** from route list or detail view
2. Configure HTTP method, path, headers, and body
3. Click **Send Request** to test the endpoint
4. View response status, headers, and body

### 3. System Monitoring

The **System Status** dashboard provides:

- **Service Health** - Overall l8e-harbor status
- **Route Store Sync** - Configuration synchronization status  
- **Secret Provider** - Secret backend connectivity
- **Backend Health** - Downstream service health
- **Performance Metrics** - Request rates, error rates, response times
- **Recent Events** - Configuration changes and system events

## Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│  React Frontend     │───▶│  nginx (Production)  │───▶│  l8e-harbor API     │
│                     │    │  - Static serving    │    │  - Management API   │
│ • YAML Editor       │    │  - API proxy        │    │  - Authentication   │
│ • Route Testing     │    │  - Security headers │    │  - Route CRUD       │
│ • Status Dashboard  │    │  - Gzip compression │    │  - System status    │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

### Technology Stack

- **Frontend**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS
- **Editor**: Monaco Editor (VS Code engine)
- **Icons**: Heroicons
- **HTTP Client**: Native fetch API
- **Validation**: Custom YAML validators
- **Deployment**: nginx + Docker

## Development

### Prerequisites

- Node.js 18+
- npm or yarn
- l8e-harbor backend running locally

### Setup

```bash
# Clone repository
git clone <repository-url>
cd l8e-harbor/ui

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Start development server
npm run dev
```

### Available Scripts

```bash
npm run dev          # Development server with HMR
npm run build        # Production build
npm run preview      # Preview production build locally
npm run lint         # ESLint code linting
npm run type-check   # TypeScript type checking
npm run test         # Run unit tests
```

### Project Structure

```
ui/
├── src/
│   ├── components/
│   │   ├── ui/          # Reusable UI components
│   │   ├── layout/      # App shell components
│   │   └── editor/      # YAML editor components
│   ├── pages/
│   │   ├── routes/      # Route management pages
│   │   ├── system/      # System status pages
│   │   └── auth/        # Authentication pages
│   ├── hooks/           # Custom React hooks
│   ├── types/           # TypeScript type definitions
│   └── utils/           # Utility functions
├── public/              # Static assets
├── nginx.conf           # Production nginx config
├── Dockerfile           # Container build config
└── docker-compose.yml   # Multi-container setup
```

## Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: l8e-harbor-ui
spec:
  replicas: 2
  selector:
    matchLabels:
      app: l8e-harbor-ui
  template:
    metadata:
      labels:
        app: l8e-harbor-ui
    spec:
      containers:
      - name: ui
        image: l8e-harbor-ui:latest
        ports:
        - containerPort: 80
        env:
        - name: API_BASE_URL
          value: "https://l8e-harbor-api:8443"
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: l8e-harbor-ui
spec:
  selector:
    app: l8e-harbor-ui
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

### VM/Systemd

```bash
# Build and extract
docker build -t l8e-harbor-ui .
docker create --name temp l8e-harbor-ui
docker cp temp:/usr/share/nginx/html ./dist
docker rm temp

# Install nginx and configure
sudo cp nginx.conf /etc/nginx/sites-available/l8e-harbor-ui
sudo ln -s /etc/nginx/sites-available/l8e-harbor-ui /etc/nginx/sites-enabled/
sudo cp -r dist/* /var/www/l8e-harbor-ui/
sudo systemctl reload nginx
```

## Security

### Built-in Security Features

- **Content Security Policy** - Prevents XSS attacks
- **HTTPS Enforcement** - Redirects to HTTPS in production
- **Secure Headers** - X-Frame-Options, X-Content-Type-Options, etc.
- **Token Storage** - JWT tokens stored in httpOnly cookies
- **Input Validation** - Client-side and server-side validation
- **Role-Based Access** - UI elements hidden based on user roles

### Production Security Checklist

- [ ] Enable HTTPS with valid TLS certificates
- [ ] Configure CSP headers for your domain
- [ ] Set up proper CORS policies on l8e-harbor backend
- [ ] Use strong JWT signing keys
- [ ] Enable audit logging on backend
- [ ] Monitor for security vulnerabilities
- [ ] Keep dependencies updated

## Performance

### Optimization Features

- **Code Splitting** - Lazy load components and routes
- **Tree Shaking** - Remove unused code from bundles
- **Asset Optimization** - Minified CSS/JS, optimized images
- **HTTP/2 Support** - Multiplexed requests, server push
- **Gzip Compression** - Reduced transfer sizes
- **Browser Caching** - Efficient cache headers

### Performance Targets

- Initial page load: < 2 seconds
- Route navigation: < 500ms
- YAML editor ready: < 1s
- Bundle size: < 500KB gzipped

## Troubleshooting

### Common Issues

**Cannot connect to l8e-harbor API**
```bash
# Check API_BASE_URL configuration
docker logs l8e-harbor-ui

# Verify l8e-harbor is running
curl -k https://localhost:8443/health
```

**Authentication not working**
```bash
# Check network connectivity
curl -k https://localhost:8443/api/v1/.well-known/jwks.json

# Verify CORS headers
curl -H "Origin: http://localhost:3000" https://localhost:8443/api/v1/routes
```

**YAML editor not loading**
```bash
# Check browser console for Monaco loader errors
# Verify monaco-editor assets are served correctly
```

### Debug Mode

Enable debug logging:

```javascript
// In browser console
localStorage.setItem('l8e-harbor-debug', 'true');
location.reload();
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code passes linting and type checks
5. Submit a pull request

### Code Style

- Use TypeScript for all new code
- Follow React hooks patterns
- Use Tailwind for styling
- Add JSDoc comments for complex functions
- Write unit tests for utilities and hooks

## License

Apache License 2.0 - see [LICENSE](../LICENSE) for details.

## Support

- **Documentation**: [docs/](../docs/)
- **Backend API**: [l8e-harbor README](../README.md)
- **Issues**: [GitHub Issues](https://github.com/example/l8e-harbor/issues)

---

**l8e-harbor UI**: Where route management meets developer experience 🌊⚓