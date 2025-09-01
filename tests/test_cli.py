"""
Tests for harbor-ctl CLI tool.
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typer.testing import CliRunner
import httpx

from app.cli import app, HarborClient, CREDENTIALS_FILE


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_credentials_dir():
    """Create temporary credentials directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_credentials_file(temp_credentials_dir):
    """Create mock credentials file."""
    creds_file = temp_credentials_dir / "credentials"
    creds_data = {
        "server": "http://localhost:8080",
        "username": "admin", 
        "token": "mock-jwt-token"
    }
    with open(creds_file, 'w') as f:
        json.dump(creds_data, f)
    return creds_file


class TestHarborClient:
    """Test HarborClient class."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = HarborClient("http://localhost:8080", "token123")
        
        assert client.server_url == "http://localhost:8080"
        assert client.token == "token123"
        assert client.client.headers["Authorization"] == "Bearer token123"
    
    def test_client_initialization_insecure(self):
        """Test client initialization with insecure flag."""
        client = HarborClient("https://localhost:8443", insecure=True)
        
        assert client.client.verify is False
    
    @patch('httpx.Client.post')
    def test_login_success(self, mock_post):
        """Test successful login."""
        # Mock successful login response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new-token",
            "expires_in": 900,
            "token_type": "bearer"
        }
        mock_post.return_value = mock_response
        
        client = HarborClient("http://localhost:8080")
        result = client.login("admin", "password123")
        
        assert result["access_token"] == "new-token"
        mock_post.assert_called_once_with(
            "http://localhost:8080/api/v1/auth/login",
            json={"username": "admin", "password": "password123"}
        )
    
    @patch('httpx.Client.post')
    def test_login_failure(self, mock_post):
        """Test login failure."""
        # Mock login failure
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=Mock(), response=Mock(status_code=401)
        )
        mock_post.return_value = mock_response
        
        client = HarborClient("http://localhost:8080")
        
        with pytest.raises(httpx.HTTPStatusError):
            client.login("admin", "wrongpass")
    
    @patch('httpx.Client.get')
    def test_get_routes(self, mock_get):
        """Test getting routes."""
        # Mock routes response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "test-route",
                "path": "/api/test",
                "methods": ["GET"],
                "backends": [{"url": "http://backend.com"}]
            }
        ]
        mock_get.return_value = mock_response
        
        client = HarborClient("http://localhost:8080", "token123")
        routes = client.get_routes()
        
        assert len(routes) == 1
        assert routes[0]["id"] == "test-route"
        mock_get.assert_called_once_with(
            "http://localhost:8080/api/v1/routes",
            params={}
        )
    
    @patch('httpx.Client.put')
    def test_create_route(self, mock_put):
        """Test creating a route."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "new-route"}
        mock_put.return_value = mock_response
        
        route_data = {
            "id": "new-route",
            "path": "/api/new",
            "methods": ["GET"],
            "backends": [{"url": "http://new.com"}]
        }
        
        client = HarborClient("http://localhost:8080", "token123")
        result = client.create_or_update_route("new-route", route_data)
        
        assert result["id"] == "new-route"
        mock_put.assert_called_once_with(
            "http://localhost:8080/api/v1/routes/new-route",
            json=route_data
        )
    
    @patch('httpx.Client.delete')
    def test_delete_route(self, mock_delete):
        """Test deleting a route."""
        mock_response = Mock()
        mock_delete.return_value = mock_response
        
        client = HarborClient("http://localhost:8080", "token123")
        client.delete_route("delete-me")
        
        mock_delete.assert_called_once_with(
            "http://localhost:8080/api/v1/routes/delete-me"
        )


class TestLoginCommand:
    """Test login command."""
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('getpass.getpass', return_value='password123')
    @patch('httpx.Client.post')
    def test_login_command_success(self, mock_post, mock_getpass, cli_runner):
        """Test successful login command."""
        # Mock successful login
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "jwt-token",
            "expires_in": 900,
            "token_type": "bearer"
        }
        mock_post.return_value = mock_response
        
        result = cli_runner.invoke(app, [
            "login",
            "--server", "http://localhost:8080",
            "--username", "admin"
        ])
        
        assert result.exit_code == 0
        assert "Login successful" in result.stdout
    
    @patch('getpass.getpass', return_value='wrongpass')
    @patch('httpx.Client.post')
    def test_login_command_failure(self, mock_post, mock_getpass, cli_runner):
        """Test failed login command."""
        # Mock login failure
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=Mock(), response=Mock(status_code=401)
        )
        mock_post.return_value = mock_response
        
        result = cli_runner.invoke(app, [
            "login",
            "--server", "http://localhost:8080", 
            "--username", "admin"
        ])
        
        assert result.exit_code != 0
        assert "Login failed" in result.stdout or "Error" in result.stdout


class TestGetCommand:
    """Test get routes command."""
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.get')
    def test_get_routes_empty(self, mock_get, cli_runner):
        """Test get routes with no routes."""
        # Mock credentials
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "jwt-token"
        }))):
            # Mock empty routes response
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_get.return_value = mock_response
            
            result = cli_runner.invoke(app, ["get", "--server", "http://localhost:8080"])
            
            assert result.exit_code == 0
            assert "No routes found" in result.stdout
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.get')
    def test_get_routes_with_data(self, mock_get, cli_runner):
        """Test get routes with data."""
        # Mock credentials
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "jwt-token"
        }))):
            # Mock routes response
            mock_response = Mock()
            mock_response.json.return_value = [
                {
                    "id": "test-route",
                    "path": "/api/test",
                    "methods": ["GET", "POST"],
                    "backends": [{"url": "http://backend.com", "weight": 100}],
                    "priority": 10,
                    "created_at": "2025-01-01T00:00:00Z"
                }
            ]
            mock_get.return_value = mock_response
            
            result = cli_runner.invoke(app, ["get", "--server", "http://localhost:8080"])
            
            assert result.exit_code == 0
            assert "test-route" in result.stdout
            assert "/api/test" in result.stdout
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.get')
    def test_get_routes_json_output(self, mock_get, cli_runner):
        """Test get routes with JSON output."""
        # Mock credentials
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin", 
            "token": "jwt-token"
        }))):
            # Mock routes response
            routes_data = [{"id": "test", "path": "/test"}]
            mock_response = Mock()
            mock_response.json.return_value = routes_data
            mock_get.return_value = mock_response
            
            result = cli_runner.invoke(app, [
                "get", "--server", "http://localhost:8080", "-o", "json"
            ])
            
            assert result.exit_code == 0
            # Should contain JSON output
            assert '"id": "test"' in result.stdout
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    def test_get_routes_no_auth(self, cli_runner):
        """Test get routes without authentication."""
        # Mock missing credentials file
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = cli_runner.invoke(app, ["get"])
            
            assert result.exit_code != 0
            assert "Authentication required" in result.stdout


class TestApplyCommand:
    """Test apply route command."""
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.put')
    def test_apply_route_success(self, mock_put, cli_runner, temp_credentials_dir):
        """Test successful route application."""
        # Create route file
        route_file = temp_credentials_dir / "route.yaml"
        route_data = {
            "apiVersion": "harbor.l8e/v1",
            "kind": "Route",
            "metadata": {"name": "test-route"},
            "spec": {
                "id": "test-route",
                "path": "/api/test",
                "methods": ["GET"],
                "backends": [{"url": "http://backend.com"}]
            }
        }
        with open(route_file, 'w') as f:
            yaml.dump(route_data, f)
        
        # Mock credentials
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "jwt-token"
        }))):
            # Mock successful route creation
            mock_response = Mock()
            mock_response.json.return_value = {"id": "test-route"}
            mock_put.return_value = mock_response
            
            result = cli_runner.invoke(app, [
                "apply", "-f", str(route_file), "--server", "http://localhost:8080"
            ])
            
            assert result.exit_code == 0
            assert "applied successfully" in result.stdout
    
    def test_apply_route_invalid_file(self, cli_runner):
        """Test apply with invalid file."""
        result = cli_runner.invoke(app, ["apply", "-f", "nonexistent.yaml"])
        
        assert result.exit_code != 0
        assert "Error" in result.stdout or "not found" in result.stdout.lower()
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    def test_apply_route_invalid_yaml(self, cli_runner, temp_credentials_dir):
        """Test apply with invalid YAML."""
        # Create invalid YAML file
        bad_file = temp_credentials_dir / "bad.yaml"
        with open(bad_file, 'w') as f:
            f.write("invalid: yaml: content:")
        
        result = cli_runner.invoke(app, ["apply", "-f", str(bad_file)])
        
        assert result.exit_code != 0


class TestExportCommand:
    """Test export routes command."""
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.get')
    def test_export_routes_to_file(self, mock_get, cli_runner, temp_credentials_dir):
        """Test exporting routes to file."""
        # Mock credentials
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "jwt-token"
        }))):
            # Mock export response
            export_data = """apiVersion: harbor.l8e/v1
kind: RouteList
items:
- id: test-route
  path: /api/test
  methods: [GET]
  backends:
  - url: http://backend.com
"""
            mock_response = Mock()
            mock_response.headers = {"content-type": "application/x-yaml"}
            mock_response.content = export_data.encode()
            mock_get.return_value = mock_response
            
            output_file = temp_credentials_dir / "export.yaml"
            result = cli_runner.invoke(app, [
                "export", "-o", str(output_file), "--server", "http://localhost:8080"
            ])
            
            assert result.exit_code == 0
            assert "exported" in result.stdout.lower()
            
            # Verify file was created
            assert output_file.exists()
            content = output_file.read_text()
            assert "test-route" in content
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.get')
    def test_export_routes_to_stdout(self, mock_get, cli_runner):
        """Test exporting routes to stdout."""
        # Mock credentials  
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "jwt-token"
        }))):
            # Mock export response
            export_data = "apiVersion: harbor.l8e/v1\nkind: RouteList\n"
            mock_response = Mock()
            mock_response.headers = {"content-type": "application/x-yaml"}
            mock_response.content = export_data.encode()
            mock_get.return_value = mock_response
            
            result = cli_runner.invoke(app, [
                "export", "--server", "http://localhost:8080"
            ])
            
            assert result.exit_code == 0
            assert "apiVersion: harbor.l8e/v1" in result.stdout


class TestDeleteCommand:
    """Test delete route command."""
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.delete')
    def test_delete_route_success(self, mock_delete, cli_runner):
        """Test successful route deletion."""
        # Mock credentials
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "jwt-token"
        }))):
            mock_response = Mock()
            mock_delete.return_value = mock_response
            
            result = cli_runner.invoke(app, [
                "delete", "test-route", "--server", "http://localhost:8080"
            ])
            
            assert result.exit_code == 0
            assert "deleted" in result.stdout.lower()
            mock_delete.assert_called_once_with(
                "http://localhost:8080/api/v1/routes/test-route"
            )
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.delete')
    def test_delete_route_not_found(self, mock_delete, cli_runner):
        """Test deleting non-existent route."""
        # Mock credentials
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "jwt-token"
        }))):
            # Mock 404 response
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=Mock(), response=Mock(status_code=404)
            )
            mock_delete.return_value = mock_response
            
            result = cli_runner.invoke(app, [
                "delete", "nonexistent", "--server", "http://localhost:8080"
            ])
            
            assert result.exit_code != 0
            assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestConfigCommand:
    """Test config management commands."""
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    def test_config_set_server(self, cli_runner, temp_credentials_dir):
        """Test setting server configuration."""
        result = cli_runner.invoke(app, [
            "config", "set", "server", "https://new-server.com"
        ])
        
        assert result.exit_code == 0
        assert "Configuration updated" in result.stdout or "set" in result.stdout.lower()
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    def test_config_get_server(self, cli_runner):
        """Test getting server configuration."""
        # Mock existing config
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "jwt-token"
        }))):
            result = cli_runner.invoke(app, ["config", "get", "server"])
            
            assert result.exit_code == 0
            assert "http://localhost:8080" in result.stdout


class TestErrorHandling:
    """Test CLI error handling."""
    
    def test_network_error_handling(self, cli_runner):
        """Test handling of network errors."""
        with patch('httpx.Client.get', side_effect=httpx.ConnectError("Connection refused")):
            result = cli_runner.invoke(app, [
                "get", "--server", "http://unreachable:8080"
            ])
            
            assert result.exit_code != 0
            assert "connection" in result.stdout.lower() or "error" in result.stdout.lower()
    
    def test_invalid_server_url(self, cli_runner):
        """Test handling of invalid server URLs."""
        result = cli_runner.invoke(app, [
            "login", "--server", "not-a-url", "--username", "admin"
        ])
        
        # Should handle gracefully (exact behavior depends on implementation)
        assert result.exit_code != 0 or "error" in result.stdout.lower()
    
    @patch('app.cli.CREDENTIALS_FILE', new_callable=lambda: tempfile.NamedTemporaryFile().name)
    @patch('httpx.Client.get')
    def test_expired_token_handling(self, mock_get, cli_runner):
        """Test handling of expired tokens."""
        # Mock credentials with potentially expired token
        with patch('builtins.open', mock_open(read_data=json.dumps({
            "server": "http://localhost:8080",
            "username": "admin",
            "token": "expired-token"
        }))):
            # Mock 401 unauthorized response
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized", request=Mock(), response=Mock(status_code=401)
            )
            mock_get.return_value = mock_response
            
            result = cli_runner.invoke(app, ["get", "--server", "http://localhost:8080"])
            
            assert result.exit_code != 0
            assert "authentication" in result.stdout.lower() or "login" in result.stdout.lower()