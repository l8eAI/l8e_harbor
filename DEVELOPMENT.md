# l8e-harbor Development Guide

Complete guide for setting up a development environment and contributing to l8e-harbor.

## Prerequisites

### Required Software

- **Python 3.9+** - Core runtime
- **Poetry** - Dependency management and packaging
- **Docker** - For containerization and examples
- **Git** - Version control

### Optional Tools

- **Kubernetes cluster** - For testing K8s features (kind, minikube, or cloud)
- **PostgreSQL** - For testing database route storage
- **Redis** - For testing distributed rate limiting
- **Prometheus** - For metrics testing
- **Jaeger** - For distributed tracing

## Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/example/l8e-harbor.git
cd l8e-harbor
```

### 2. Install Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Install pre-commit hooks (recommended)
poetry run pre-commit install
```

### 3. Environment Configuration

```bash
# Create development config
cp examples/config.yaml dev-config.yaml

# Edit for development
editor dev-config.yaml
```

**Development Config (`dev-config.yaml`)**:
```yaml
mode: vm
server:
  host: 127.0.0.1
  port: 8080        # Use non-privileged port
  workers: 1        # Single worker for debugging

tls:
  enabled: false    # Disable TLS for development

secret_provider: localfs
secret_path: ./dev-data/secrets
route_store: memory
route_store_path: ./dev-data/routes-snapshot.yaml
auth_adapter: local

log_level: DEBUG    # Verbose logging
enable_metrics: true
enable_tracing: false  # Can be enabled with Jaeger

# Development-friendly settings
circuit_breaker:
  default_failure_threshold: 80  # More lenient
  
retry_policy:
  default_max_retries: 1
```

### 4. Run Development Server

```bash
# Create development data directory
mkdir -p dev-data/secrets

# Run with auto-reload
poetry run python -m app.main --config dev-config.yaml --reload

# Alternative: Use poetry script
poetry run dev
```

### 5. Verify Installation

```bash
# Check server health
curl http://localhost:8080/health

# Check metrics
curl http://localhost:8080/metrics

# Get admin credentials
cat dev-data/secrets/admin-credentials.json
```

## Development Workflow

### Code Organization

```
l8e-harbor/
├── app/                    # Main application code
│   ├── __init__.py
│   ├── main.py            # Application entry point
│   ├── api/               # REST API endpoints
│   ├── auth/              # Authentication adapters
│   ├── config/            # Configuration management
│   ├── middleware/        # Request middleware
│   ├── proxy/             # Proxy logic
│   ├── routes/            # Route management
│   ├── secrets/           # Secret providers
│   ├── storage/           # Route storage adapters
│   └── utils/             # Utility functions
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data
├── deployments/           # Deployment configurations
├── examples/              # Example configurations
└── docs/                  # Documentation
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test categories
poetry run pytest tests/unit/           # Unit tests only
poetry run pytest tests/integration/    # Integration tests only

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/unit/test_routes.py

# Run specific test
poetry run pytest tests/unit/test_routes.py::test_create_route
```

### Code Quality Tools

```bash
# Linting and formatting
poetry run ruff check app/              # Check for style issues
poetry run ruff check app/ --fix        # Auto-fix issues
poetry run ruff format app/             # Format code

# Type checking
poetry run mypy app/

# Security scanning
poetry run bandit -r app/

# Run all quality checks
poetry run pre-commit run --all-files
```

### Pre-commit Hooks

The repository includes pre-commit hooks that run automatically:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML, types-requests]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-c', 'pyproject.toml']
```

## Testing

### Test Categories

#### Unit Tests

Test individual components in isolation:

```python
# tests/unit/test_routes.py
import pytest
from app.routes.manager import RouteManager
from app.routes.models import Route, Backend

def test_create_route():
    manager = RouteManager()
    route = Route(
        id="test-route",
        path="/api/test",
        backends=[Backend(url="http://localhost:8080")]
    )
    
    result = manager.create_route(route)
    assert result.id == "test-route"
    assert len(result.backends) == 1
```

#### Integration Tests

Test component interactions:

```python
# tests/integration/test_proxy.py
import pytest
import httpx
from app.main import create_app

@pytest.fixture
async def client():
    app = create_app()
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

async def test_proxy_request(client):
    # Create test route
    route_config = {
        "id": "test-api",
        "path": "/api/test", 
        "backends": [{"url": "http://httpbin.org/json"}]
    }
    
    response = await client.put("/api/v1/routes/test-api", json=route_config)
    assert response.status_code == 201
    
    # Test proxy request
    response = await client.get("/api/test")
    assert response.status_code == 200
```

#### End-to-End Tests

Test complete workflows:

```python
# tests/e2e/test_calculator_example.py
import pytest
import docker
import httpx

@pytest.fixture(scope="module")
def calculator_stack():
    """Start calculator MCP example stack."""
    client = docker.from_env()
    
    # Start docker-compose stack
    compose_file = "examples/calculator-mcp/docker-compose.yml"
    
    # ... setup code ...
    
    yield "http://localhost:18080"
    
    # ... cleanup code ...

async def test_calculator_mcp_flow(calculator_stack):
    """Test complete calculator MCP workflow."""
    base_url = calculator_stack
    
    async with httpx.AsyncClient() as client:
        # Test tools list
        response = await client.post(f"{base_url}/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "calculator" in [tool["name"] for tool in data["result"]["tools"]]
        
        # Test calculator call
        response = await client.post(f"{base_url}/mcp", json={
            "jsonrpc": "2.0", 
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "calculator",
                "arguments": {"expression": "2 + 3 * 4"}
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "14" in data["result"]["content"][0]["text"]
```

### Test Configuration

```python
# tests/conftest.py
import pytest
import tempfile
import shutil
from app.config import Config
from app.main import create_app

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture  
def test_config(temp_dir):
    """Test configuration."""
    return Config(
        mode="vm",
        server_host="127.0.0.1",
        server_port=0,  # Random port
        tls_enabled=False,
        secret_provider="localfs",
        secret_path=f"{temp_dir}/secrets",
        route_store="memory",
        auth_adapter="local",
        log_level="DEBUG"
    )

@pytest.fixture
async def app(test_config):
    """Create test application."""
    app = create_app(config=test_config)
    yield app

@pytest.fixture
async def client(app):
    """HTTP client for testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Mock Services

```python
# tests/mocks/backend_service.py
from fastapi import FastAPI
import uvicorn

class MockBackend:
    def __init__(self, port: int = 8081):
        self.app = FastAPI()
        self.port = port
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        @self.app.get("/api/data")
        async def get_data():
            return {"data": "test response"}
        
        @self.app.post("/api/data") 
        async def post_data(data: dict):
            return {"received": data}
    
    def start(self):
        uvicorn.run(self.app, host="127.0.0.1", port=self.port)

# Usage in tests
@pytest.fixture
async def mock_backend():
    backend = MockBackend(port=8081)
    # Start in background thread
    # ... 
    yield f"http://localhost:8081"
    # Cleanup
```

## Building and Packaging

### harbor-ctl CLI

Build the command-line interface:

```bash
# Install as editable package (for development)
poetry install

# Use CLI during development
poetry run harbor-ctl --help

# Build standalone binary
poetry run pip install pyinstaller
poetry run pyinstaller \
    --onefile \
    --name harbor-ctl \
    --add-data "app:app" \
    app/cli.py

# Binary will be in dist/harbor-ctl
./dist/harbor-ctl --help
```

### Docker Images

```bash
# Build development image
docker build -t l8e-harbor:dev .

# Build with specific tag
docker build -t l8e-harbor:1.0.0 .

# Multi-stage build for smaller image
docker build -f Dockerfile.alpine -t l8e-harbor:alpine .
```

### Python Package

```bash
# Build wheel and source distribution
poetry build

# Check built packages
ls dist/
# l8e_harbor-1.0.0-py3-none-any.whl
# l8e_harbor-1.0.0.tar.gz

# Install from wheel
pip install dist/l8e_harbor-1.0.0-py3-none-any.whl
```

## Debugging

### IDE Configuration

#### VS Code

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "l8e-harbor",
      "type": "python",
      "request": "launch",
      "module": "app.main",
      "args": ["--config", "dev-config.yaml", "--reload"],
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm

1. Set interpreter to Poetry virtual environment
2. Enable pytest as test runner
3. Configure run configuration with dev-config.yaml

### Debug Logging

Enable detailed debug logging:

```python
# app/main.py
import logging

# Configure debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific loggers
logging.getLogger("app.proxy").setLevel(logging.DEBUG)
logging.getLogger("app.auth").setLevel(logging.DEBUG)
logging.getLogger("app.routes").setLevel(logging.DEBUG)
```

### Performance Profiling

```python
# Profile specific functions
import cProfile
import pstats

def profile_request_handling():
    # ... test code ...
    pass

if __name__ == "__main__":
    cProfile.run('profile_request_handling()', 'profile_stats.prof')
    
    # Analyze results
    stats = pstats.Stats('profile_stats.prof')
    stats.sort_stats('cumulative')
    stats.print_stats(20)
```

## Contributing

### Development Process

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/new-auth-adapter
   ```
3. **Make changes with tests**
4. **Run quality checks**:
   ```bash
   poetry run pre-commit run --all-files
   poetry run pytest
   ```
5. **Commit with clear messages**:
   ```bash
   git commit -m "Add LDAP authentication adapter
   
   - Implement LDAP auth adapter with connection pooling
   - Add configuration options for LDAP servers
   - Include comprehensive tests and documentation
   - Update example configurations
   
   Fixes #123"
   ```
6. **Push and create pull request**

### Code Style Guidelines

- **PEP 8 compliance** via Ruff
- **Type hints** for all public functions
- **Docstrings** for classes and public methods
- **Error handling** with specific exceptions
- **Logging** instead of print statements
- **Configuration** via dependency injection

### Example: Adding New Authentication Adapter

```python
# app/auth/adapters/ldap.py
from typing import Optional, Dict, Any
import ldap3
from app.auth.base import AuthAdapter, AuthResult
from app.config import Config

class LDAPAuthAdapter(AuthAdapter):
    """LDAP authentication adapter."""
    
    def __init__(self, config: Dict[str, Any]):
        self.server_url = config["server_url"]
        self.bind_dn = config["bind_dn"] 
        self.bind_password = config["bind_password"]
        self.user_search_base = config["user_search_base"]
        self.user_search_filter = config.get("user_search_filter", "(uid={username})")
        
    async def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate user against LDAP server."""
        try:
            server = ldap3.Server(self.server_url)
            conn = ldap3.Connection(server, self.bind_dn, self.bind_password)
            
            if not conn.bind():
                return AuthResult(success=False, error="LDAP bind failed")
                
            # Search for user
            search_filter = self.user_search_filter.format(username=username)
            conn.search(self.user_search_base, search_filter)
            
            if not conn.entries:
                return AuthResult(success=False, error="User not found")
                
            user_dn = conn.entries[0].entry_dn
            
            # Try to bind as user
            user_conn = ldap3.Connection(server, user_dn, password)
            if user_conn.bind():
                return AuthResult(
                    success=True, 
                    user_id=username,
                    user_role=self._get_user_role(conn, user_dn)
                )
            else:
                return AuthResult(success=False, error="Invalid credentials")
                
        except Exception as e:
            return AuthResult(success=False, error=f"LDAP error: {e}")
    
    def _get_user_role(self, conn: ldap3.Connection, user_dn: str) -> str:
        """Determine user role from LDAP groups."""
        # Implementation details...
        return "crew"  # Default role
```

```python
# tests/unit/auth/test_ldap_adapter.py
import pytest
from unittest.mock import Mock, patch
from app.auth.adapters.ldap import LDAPAuthAdapter

@pytest.fixture
def ldap_config():
    return {
        "server_url": "ldap://localhost:389",
        "bind_dn": "cn=admin,dc=example,dc=com", 
        "bind_password": "admin_password",
        "user_search_base": "ou=users,dc=example,dc=com"
    }

@pytest.fixture
def ldap_adapter(ldap_config):
    return LDAPAuthAdapter(ldap_config)

@patch('app.auth.adapters.ldap.ldap3')
async def test_successful_authentication(mock_ldap3, ldap_adapter):
    # Mock LDAP responses
    mock_server = Mock()
    mock_conn = Mock()
    mock_conn.bind.return_value = True
    mock_conn.entries = [Mock(entry_dn="uid=testuser,ou=users,dc=example,dc=com")]
    
    mock_ldap3.Server.return_value = mock_server
    mock_ldap3.Connection.return_value = mock_conn
    
    result = await ldap_adapter.authenticate("testuser", "password123")
    
    assert result.success is True
    assert result.user_id == "testuser"
    assert result.user_role == "crew"

@patch('app.auth.adapters.ldap.ldap3')  
async def test_invalid_credentials(mock_ldap3, ldap_adapter):
    mock_server = Mock()
    mock_conn = Mock()
    mock_conn.bind.side_effect = [True, False]  # Admin bind succeeds, user bind fails
    mock_conn.entries = [Mock(entry_dn="uid=testuser,ou=users,dc=example,dc=com")]
    
    mock_ldap3.Server.return_value = mock_server
    mock_ldap3.Connection.return_value = mock_conn
    
    result = await ldap_adapter.authenticate("testuser", "wrong_password")
    
    assert result.success is False
    assert "Invalid credentials" in result.error
```

### Documentation

Update documentation when making changes:

- **README.md** - For major features
- **CONFIGURATION.md** - For new config options
- **SECURITY.md** - For security-related changes
- **API docs** - For endpoint changes
- **Examples** - For new adapter types or features

## Release Process

### Versioning

l8e-harbor follows [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Creating a Release

```bash
# Update version
poetry version minor  # or major/patch

# Update changelog
editor CHANGELOG.md

# Commit version bump
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to $(poetry version -s)"

# Create release tag
git tag -a "v$(poetry version -s)" -m "Release v$(poetry version -s)"

# Push changes and tag
git push origin main
git push origin "v$(poetry version -s)"
```

### CI/CD Pipeline

The repository includes GitHub Actions workflows:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run tests
      run: poetry run pytest --cov=app
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Development Issues

**Import Errors**:
```bash
# Ensure virtual environment is activated
poetry shell

# Reinstall dependencies
poetry install --sync
```

**Port Conflicts**:
```bash
# Find processes using port 8080
lsof -i :8080

# Kill process if needed
kill -9 <PID>

# Or use different port in dev-config.yaml
```

**Test Failures**:
```bash
# Run specific failing test with verbose output
poetry run pytest tests/unit/test_routes.py::test_create_route -v

# Run with pdb for debugging
poetry run pytest tests/unit/test_routes.py::test_create_route --pdb
```

**Docker Issues**:
```bash
# Clean up Docker resources
docker system prune -f

# Rebuild images
docker-compose -f examples/calculator-mcp/docker-compose.yml build --no-cache
```

## Next Steps

- Review the [Architecture Overview](docs/architecture.md) 
- Check out [examples/](examples/README.md) for practical use cases
- Read [CONFIGURATION.md](CONFIGURATION.md) for detailed config options
- See [SECURITY.md](SECURITY.md) for security considerations
- Explore [deployments/](deployments/README.md) for deployment guides