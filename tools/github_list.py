"""
Direct GitHub listing tools
"""
import os
from github import Github
from langchain_core.tools import tool
from rich.console import Console
from rich.table import Table

console = Console()


@tool
def list_my_repos() -> str:
    """
    List all repositories for the authenticated GitHub user.
    
    Returns:
        List of user's repositories with details
    """
    try:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return "Error: GITHUB_TOKEN not found"
        
        console.print("[cyan]📂 Fetching your repositories...[/cyan]")
        
        g = Github(token)
        user = g.get_user()
        
        table = Table(title=f"📂 {user.login}'s Repositories")
        table.add_column("Name", style="cyan")
        table.add_column("Private", style="yellow")
        table.add_column("Stars", style="green")
        table.add_column("Language", style="blue")
        
        repos = []
        for repo in user.get_repos():
            table.add_row(
                repo.name,
                "🔒" if repo.private else "🌐",
                str(repo.stargazers_count),
                repo.language or "N/A"
            )
            repos.append(f"• {repo.name} ({repo.html_url})")
        
        console.print(table)
        console.print(f"[green]✓ Found {len(repos)} repositories[/green]")
        
        return "\n".join(repos)
    
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_repo_info(owner: str, repo: str) -> str:
    """
    Get detailed information about a specific repository.
    
    Args:
        owner: Repository owner username
        repo: Repository name
    
    Returns:
        Repository details
    """
    try:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return "Error: GITHUB_TOKEN not found"
        
        console.print(f"[cyan]📂 Getting info for {owner}/{repo}...[/cyan]")
        
        g = Github(token)
        repository = g.get_repo(f"{owner}/{repo}")
        
        info = f"""
**{repository.full_name}**

{repository.description or 'No description'}

**Stats:**
- ⭐ Stars: {repository.stargazers_count}
- 🍴 Forks: {repository.forks_count}
- 👁️ Watchers: {repository.watchers_count}
- 🐛 Issues: {repository.open_issues_count}

**Details:**
- Language: {repository.language or 'N/A'}
- Created: {repository.created_at.strftime('%Y-%m-%d')}
- Updated: {repository.updated_at.strftime('%Y-%m-%d')}
- Default Branch: {repository.default_branch}
- Private: {'Yes' if repository.private else 'No'}

**Links:**
- URL: {repository.html_url}
- Clone: {repository.clone_url}
"""
        
        console.print(f"[green]✓ Retrieved info[/green]")
        return info
    
    except Exception as e:
        return f"Error: {str(e)}"


def get_github_list_tools():
    """Return list of GitHub listing tools"""
    return [list_my_repos, get_repo_info]
