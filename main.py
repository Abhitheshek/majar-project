#!/usr/bin/env python3
"""
Professional Code Assistant - Main Entry Point
Clean, modern implementation with proper error handling
"""
import asyncio
import sys
from pathlib import Path
from rich.console import Console

from core.config import config
from app.agent import CodeAssistantAgent

console = Console()

async def main():
    """Main entry point for the Code Assistant"""
    try:
        # Validate configuration
        if not config.validate_api_keys():
            console.print("[bold red]❌ Error: No valid API key found![/bold red]")
            console.print("[yellow]Please set GROQ_API_KEY or GOOGLE_API_KEY in .env file[/yellow]")
            sys.exit(1)
        
        # Get project directory from command line
        project_dir = sys.argv[1] if len(sys.argv) > 1 else None
        if project_dir:
            project_path = Path(project_dir)
            if not project_path.exists():
                console.print(f"[bold red]❌ Error: Directory '{project_dir}' does not exist[/bold red]")
                sys.exit(1)
        
        # Initialize and run agent
        agent = CodeAssistantAgent(working_directory=project_dir)
        await agent.initialize()
        await agent.run()
        
    except KeyboardInterrupt:
        console.print("\n[bold cyan]👋 Interrupted by user[/bold cyan]")
    except Exception as e:
        console.print(f"[bold red]❌ Fatal error: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
    finally:
        # Cleanup
        if 'agent' in locals():
            await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
