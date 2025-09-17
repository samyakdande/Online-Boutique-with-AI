"""
Command-line interface for AI-Powered Boutique Agents.

This module provides the main CLI for managing agents, deployments,
and development workflows.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ai_agents.core.adk import agent_manager
from ai_agents.core.config import settings
from ai_agents.core.logging import get_logger

app = typer.Typer(
    name="ai-agents",
    help="AI-Powered Online Boutique Enhancement CLI",
    add_completion=False
)

console = Console()
logger = get_logger(__name__)


@app.command()
def version():
    """Show version information."""
    from ai_agents import __version__
    console.print(f"AI-Powered Boutique Agents v{__version__}")


@app.command()
def config():
    """Show current configuration."""
    console.print("[bold blue]Current Configuration:[/bold blue]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Environment", settings.environment)
    table.add_row("Debug Mode", str(settings.debug))
    table.add_row("Log Level", settings.log_level)
    table.add_row("Google Cloud Project", settings.google_cloud_project)
    table.add_row("Cluster Name", settings.k8s_cluster_name)
    table.add_row("Hot Reload", str(settings.dev_hot_reload_enabled))
    
    console.print(table)


@app.command()
def agents():
    """List all available agents."""
    from ai_agents.core.config import AGENT_CONFIGS
    
    console.print("[bold blue]Available Agents:[/bold blue]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Version", style="yellow")
    table.add_column("Capabilities", style="blue")
    
    for agent_id, config in AGENT_CONFIGS.items():
        capabilities = ", ".join(config["capabilities"])
        table.add_row(
            config["id"],
            config["name"],
            config["version"],
            capabilities
        )
    
    console.print(table)


@app.command()
def status():
    """Show agent status."""
    try:
        agent_status = agent_manager.get_agent_status()
        
        if not agent_status:
            console.print("[yellow]No agents are currently running.[/yellow]")
            return
        
        console.print("[bold blue]Agent Status:[/bold blue]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Agent ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("State", style="yellow")
        table.add_column("Uptime", style="blue")
        table.add_column("Requests", style="magenta")
        table.add_column("Error Rate", style="red")
        
        for agent_id, status in agent_status.items():
            uptime = f"{status['uptime']:.1f}s"
            error_rate = f"{status['error_rate']:.2%}"
            
            table.add_row(
                agent_id,
                status["name"],
                status["state"],
                uptime,
                str(status["request_count"]),
                error_rate
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting agent status: {e}[/red]")


@app.command()
def start(
    agent_id: Optional[str] = typer.Argument(None, help="Agent ID to start (or 'all' for all agents)")
):
    """Start agents."""
    async def _start():
        try:
            if agent_id is None or agent_id == "all":
                console.print("[blue]Starting all agents...[/blue]")
                await agent_manager.start_all_agents()
                console.print("[green]All agents started successfully![/green]")
            else:
                console.print(f"[blue]Starting agent: {agent_id}[/blue]")
                await agent_manager.start_agent(agent_id)
                console.print(f"[green]Agent {agent_id} started successfully![/green]")
        except Exception as e:
            console.print(f"[red]Error starting agents: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_start())


@app.command()
def stop(
    agent_id: Optional[str] = typer.Argument(None, help="Agent ID to stop (or 'all' for all agents)")
):
    """Stop agents."""
    async def _stop():
        try:
            if agent_id is None or agent_id == "all":
                console.print("[blue]Stopping all agents...[/blue]")
                await agent_manager.stop_all_agents()
                console.print("[green]All agents stopped successfully![/green]")
            else:
                console.print(f"[blue]Stopping agent: {agent_id}[/blue]")
                await agent_manager.stop_agent(agent_id)
                console.print(f"[green]Agent {agent_id} stopped successfully![/green]")
        except Exception as e:
            console.print(f"[red]Error stopping agents: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_stop())


@app.command()
def dev():
    """Start development server with hot reload."""
    console.print("[bold blue]Starting AI-Powered Boutique development server...[/bold blue]")
    
    if not settings.dev_hot_reload_enabled:
        console.print("[yellow]Hot reload is disabled. Enable it in configuration.[/yellow]")
    
    try:
        from ai_agents.dev.server import start_dev_server
        asyncio.run(start_dev_server())
    except KeyboardInterrupt:
        console.print("\n[yellow]Development server stopped.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting development server: {e}[/red]")
        sys.exit(1)


@app.command()
def test(
    coverage: bool = typer.Option(False, "--coverage", help="Run with coverage"),
    integration: bool = typer.Option(False, "--integration", help="Run integration tests"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Run tests."""
    import subprocess
    
    cmd = ["pytest"]
    
    if coverage:
        cmd.extend(["--cov=ai_agents", "--cov-report=html", "--cov-report=term"])
    
    if integration:
        cmd.extend(["-m", "integration"])
    else:
        cmd.extend(["-m", "not integration"])
    
    if verbose:
        cmd.append("-v")
    
    console.print(f"[blue]Running tests: {' '.join(cmd)}[/blue]")
    
    try:
        result = subprocess.run(cmd, check=True)
        console.print("[green]Tests completed successfully![/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Tests failed with exit code {e.returncode}[/red]")
        sys.exit(e.returncode)


@app.command()
def test_mcp():
    """Test MCP server functionality."""
    console.print("[blue]Testing Boutique API MCP Server...[/blue]")
    
    async def _test_mcp():
        try:
            from ai_agents.mcp_servers.boutique_api import BoutiqueAPIMCPServer
            
            # Create and initialize server
            server = BoutiqueAPIMCPServer()
            await server.initialize()
            
            console.print("[green]✓ Server initialized successfully[/green]")
            
            # Test getting products
            products = await server._get_products({})
            console.print(f"[green]✓ Found {len(products['products'])} products[/green]")
            
            # Test search
            search_result = await server._search_products({"query": "watch"})
            console.print(f"[green]✓ Search found {len(search_result['products'])} products[/green]")
            
            # Test cart operations
            cart = await server._get_cart({"user_id": "test_user"})
            console.print(f"[green]✓ Cart retrieved with {cart['total_items']} items[/green]")
            
            # Test recommendations
            recs = await server._get_recommendations({"user_id": "test_user", "product_ids": []})
            console.print(f"[green]✓ Got {len(recs['recommendations'])} recommendations[/green]")
            
            console.print("[bold green]🎉 All MCP server tests passed![/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ MCP server test failed: {e}[/red]")
            sys.exit(1)
    
    asyncio.run(_test_mcp())


@app.command()
def deploy(
    environment: str = typer.Argument("development", help="Deployment environment"),
    cluster: Optional[str] = typer.Option(None, help="Kubernetes cluster name")
):
    """Deploy agents to Kubernetes."""
    console.print(f"[blue]Deploying to {environment} environment...[/blue]")
    
    try:
        from ai_agents.deployment.deploy import deploy_agents
        asyncio.run(deploy_agents(environment, cluster))
        console.print(f"[green]Deployment to {environment} completed successfully![/green]")
    except Exception as e:
        console.print(f"[red]Deployment failed: {e}[/red]")
        sys.exit(1)


@app.command()
def logs(
    agent_id: Optional[str] = typer.Argument(None, help="Agent ID to show logs for"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(100, "--lines", "-n", help="Number of lines to show")
):
    """Show agent logs."""
    import subprocess
    
    if agent_id:
        cmd = ["kubectl", "logs", f"deployment/{agent_id}", "-n", settings.kubernetes.namespace]
    else:
        cmd = ["kubectl", "logs", "-l", "app=ai-agents", "-n", settings.kubernetes.namespace]
    
    if follow:
        cmd.append("-f")
    
    cmd.extend(["--tail", str(lines)])
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error getting logs: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Log streaming stopped.[/yellow]")


def main():
    """Main CLI entry point."""
    try:
        app()
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if settings.debug:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()