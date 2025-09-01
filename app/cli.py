"""
harbor-ctl CLI client for l8e-harbor management.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

app = typer.Typer(
    name="harbor-ctl",
    help="l8e-harbor management CLI",
    add_completion=False
)

console = Console()

# Default configuration
DEFAULT_SERVER = "https://localhost:8443"
CREDENTIALS_FILE = Path.home() / ".l8e-harbor" / "credentials"


class HarborClient:
    """Client for interacting with l8e-harbor Management API."""
    
    def __init__(self, server_url: str, token: Optional[str] = None, insecure: bool = False):
        self.server_url = server_url.rstrip('/')
        self.token = token
        self.client = httpx.Client(
            verify=not insecure,
            timeout=30.0,
            headers={"Authorization": f"Bearer {token}"} if token else {}
        )
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get access token."""
        response = self.client.post(
            f"{self.server_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    def get_routes(self, path: Optional[str] = None, backend: Optional[str] = None) -> Dict[str, Any]:
        """Get routes list."""
        params = {}
        if path:
            params["path"] = path
        if backend:
            params["backend"] = backend
        
        response = self.client.get(f"{self.server_url}/api/v1/routes", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_route(self, route_id: str) -> Dict[str, Any]:
        """Get single route."""
        response = self.client.get(f"{self.server_url}/api/v1/routes/{route_id}")
        response.raise_for_status()
        return response.json()
    
    def create_route(self, route_id: str, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update route."""
        response = self.client.put(
            f"{self.server_url}/api/v1/routes/{route_id}",
            json=route_data
        )
        response.raise_for_status()
        return response.json()
    
    def delete_route(self, route_id: str) -> Dict[str, Any]:
        """Delete route."""
        response = self.client.delete(f"{self.server_url}/api/v1/routes/{route_id}")
        response.raise_for_status()
        return response.json()
    
    def bulk_apply(self, routes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply multiple routes."""
        response = self.client.post(
            f"{self.server_url}/api/v1/routes:bulk-apply",
            json=routes
        )
        response.raise_for_status()
        return response.json()
    
    def export_routes(self) -> Dict[str, Any]:
        """Export all routes."""
        response = self.client.get(f"{self.server_url}/api/v1/routes:export")
        response.raise_for_status()
        return response.json()


def get_client(
    server: Optional[str] = None,
    insecure: bool = False,
    credentials: Optional[str] = None
) -> HarborClient:
    """Create Harbor client with authentication."""
    server_url = server or os.environ.get("HARBOR_SERVER", DEFAULT_SERVER)
    
    # Load credentials
    token = None
    if credentials:
        creds_file = Path(credentials)
    else:
        creds_file = CREDENTIALS_FILE
    
    if creds_file.exists():
        try:
            with open(creds_file, 'r') as f:
                creds = json.load(f)
                token = creds.get("access_token")
        except Exception as e:
            console.print(f"[red]Warning: Failed to load credentials: {e}[/red]")
    
    # Check for token in environment
    if not token:
        token = os.environ.get("HARBOR_TOKEN")
    
    return HarborClient(server_url, token, insecure)


def save_credentials(access_token: str, expires_in: int):
    """Save credentials to file."""
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    creds = {
        "access_token": access_token,
        "expires_in": expires_in,
        "token_type": "bearer"
    }
    
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds, f, indent=2)
    
    # Set secure permissions
    os.chmod(CREDENTIALS_FILE, 0o600)


@app.command()
def login(
    username: str = typer.Option(..., "--username", "-u", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password (will prompt if not provided)"),
    server: Optional[str] = typer.Option(None, "--server", help="Server URL"),
    insecure: bool = typer.Option(False, "--insecure-skip-tls-verify", help="Skip TLS verification")
):
    """Login to l8e-harbor and save credentials."""
    if not password:
        password = typer.prompt("Password", hide_input=True)
    
    client = get_client(server, insecure)
    
    try:
        result = client.login(username, password)
        save_credentials(result["access_token"], result["expires_in"])
        console.print("[green]✓[/green] Login successful")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]✗[/red] Invalid credentials")
        else:
            console.print(f"[red]✗[/red] Login failed: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Login failed: {e}")
        sys.exit(1)


@app.command("get")
def get_routes(
    path: Optional[str] = typer.Option(None, "--path", help="Filter by path prefix"),
    backend: Optional[str] = typer.Option(None, "--backend", help="Filter by backend URL"),
    output: str = typer.Option("table", "-o", help="Output format: table, json, yaml"),
    server: Optional[str] = typer.Option(None, "--server", help="Server URL"),
    insecure: bool = typer.Option(False, "--insecure-skip-tls-verify", help="Skip TLS verification"),
    credentials: Optional[str] = typer.Option(None, "--credentials", help="Credentials file path")
):
    """Get routes."""
    client = get_client(server, insecure, credentials)
    
    try:
        result = client.get_routes(path, backend)
        routes = result["routes"]
        
        if output == "json":
            print(json.dumps(routes, indent=2))
        elif output == "yaml":
            print(yaml.dump(routes, default_flow_style=False))
        else:  # table
            if not routes:
                console.print("[yellow]No routes found[/yellow]")
                return
            
            table = Table(title="Routes")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Path", style="green")
            table.add_column("Methods", style="blue")
            table.add_column("Backends", style="magenta")
            table.add_column("Priority", style="yellow")
            
            for route in routes:
                backends = ", ".join([str(b["url"]) for b in route["backends"]])
                methods = ", ".join(route["methods"])
                table.add_row(
                    route["id"],
                    route["path"],
                    methods,
                    backends,
                    str(route["priority"])
                )
            
            console.print(table)
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]✗[/red] Authentication required. Run 'harbor-ctl login' first.")
        else:
            console.print(f"[red]✗[/red] Failed to get routes: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to get routes: {e}")
        sys.exit(1)


@app.command()
def apply(
    file: str = typer.Option(..., "-f", "--file", help="Route definition file (YAML or JSON)"),
    server: Optional[str] = typer.Option(None, "--server", help="Server URL"),
    insecure: bool = typer.Option(False, "--insecure-skip-tls-verify", help="Skip TLS verification"),
    credentials: Optional[str] = typer.Option(None, "--credentials", help="Credentials file path")
):
    """Apply route configuration from file."""
    client = get_client(server, insecure, credentials)
    
    # Load route definition
    file_path = Path(file)
    if not file_path.exists():
        console.print(f"[red]✗[/red] File not found: {file}")
        sys.exit(1)
    
    try:
        with open(file_path, 'r') as f:
            if file_path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to parse file: {e}")
        sys.exit(1)
    
    try:
        # Handle different file formats
        if data.get("kind") == "Route":
            # Single route
            route_id = data["spec"]["id"]
            result = client.create_route(route_id, data["spec"])
            console.print(f"[green]✓[/green] Route '{route_id}' applied successfully")
        elif data.get("kind") == "RouteList":
            # Multiple routes
            routes = [item["spec"] for item in data.get("items", [])]
            result = client.bulk_apply(routes)
            console.print(f"[green]✓[/green] Applied {len(routes)} routes successfully")
        else:
            # Assume raw route spec
            route_id = data.get("id") or input("Enter route ID: ")
            result = client.create_route(route_id, data)
            console.print(f"[green]✓[/green] Route '{route_id}' applied successfully")
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]✗[/red] Authentication required. Run 'harbor-ctl login' first.")
        elif e.response.status_code == 403:
            console.print("[red]✗[/red] Insufficient permissions. harbor-master role required.")
        else:
            console.print(f"[red]✗[/red] Failed to apply route: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to apply route: {e}")
        sys.exit(1)


@app.command()
def delete(
    route_id: str = typer.Argument(..., help="Route ID to delete"),
    server: Optional[str] = typer.Option(None, "--server", help="Server URL"),
    insecure: bool = typer.Option(False, "--insecure-skip-tls-verify", help="Skip TLS verification"),
    credentials: Optional[str] = typer.Option(None, "--credentials", help="Credentials file path"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation")
):
    """Delete a route."""
    if not yes:
        if not typer.confirm(f"Are you sure you want to delete route '{route_id}'?"):
            console.print("Aborted.")
            return
    
    client = get_client(server, insecure, credentials)
    
    try:
        client.delete_route(route_id)
        console.print(f"[green]✓[/green] Route '{route_id}' deleted successfully")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]✗[/red] Authentication required. Run 'harbor-ctl login' first.")
        elif e.response.status_code == 403:
            console.print("[red]✗[/red] Insufficient permissions. harbor-master role required.")
        elif e.response.status_code == 404:
            console.print(f"[red]✗[/red] Route '{route_id}' not found")
        else:
            console.print(f"[red]✗[/red] Failed to delete route: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to delete route: {e}")
        sys.exit(1)


@app.command()
def export(
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output file path"),
    format: str = typer.Option("yaml", "--format", help="Output format: yaml, json"),
    server: Optional[str] = typer.Option(None, "--server", help="Server URL"),
    insecure: bool = typer.Option(False, "--insecure-skip-tls-verify", help="Skip TLS verification"),
    credentials: Optional[str] = typer.Option(None, "--credentials", help="Credentials file path")
):
    """Export all routes."""
    client = get_client(server, insecure, credentials)
    
    try:
        result = client.export_routes()
        
        if format == "json":
            content = json.dumps(result, indent=2)
        else:  # yaml
            content = yaml.dump(result, default_flow_style=False)
        
        if output:
            with open(output, 'w') as f:
                f.write(content)
            console.print(f"[green]✓[/green] Routes exported to {output}")
        else:
            print(content)
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]✗[/red] Authentication required. Run 'harbor-ctl login' first.")
        else:
            console.print(f"[red]✗[/red] Failed to export routes: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to export routes: {e}")
        sys.exit(1)


@app.command()
def config(
    action: str = typer.Argument(..., help="Action: view, set-server"),
    value: Optional[str] = typer.Argument(None, help="Value for set actions")
):
    """Manage CLI configuration."""
    if action == "view":
        config_info = {
            "server": os.environ.get("HARBOR_SERVER", DEFAULT_SERVER),
            "credentials_file": str(CREDENTIALS_FILE),
            "credentials_exist": CREDENTIALS_FILE.exists()
        }
        
        panel = Panel.fit(
            f"[cyan]Server:[/cyan] {config_info['server']}\n"
            f"[cyan]Credentials File:[/cyan] {config_info['credentials_file']}\n"
            f"[cyan]Credentials Exist:[/cyan] {'Yes' if config_info['credentials_exist'] else 'No'}",
            title="Harbor CLI Configuration"
        )
        console.print(panel)
    
    elif action == "set-server":
        if not value:
            console.print("[red]✗[/red] Server URL required")
            sys.exit(1)
        
        # For simplicity, just show how to set the environment variable
        console.print(f"[green]Set environment variable:[/green] export HARBOR_SERVER={value}")
    
    else:
        console.print(f"[red]✗[/red] Unknown action: {action}")
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()