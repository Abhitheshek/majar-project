"""
Direct GitHub operations using PyGithub - Fast and Simple
"""
import os
from github import Github, GithubException
from langchain_core.tools import tool


@tool
def quick_push_file(owner: str, repo: str, file_path: str, branch: str = "main", message: str = "Update file") -> str:
    """
    Quickly push a single file to GitHub repository.
    
    Args:
        owner: GitHub username
        repo: Repository name
        file_path: Local file path to push
        branch: Branch name (default: main)
        message: Commit message
    
    Returns:
        Success or error message
    """
    try:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return "Error: GITHUB_TOKEN not found in environment"
        
        # Read file content
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' not found"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Initialize GitHub
        g = Github(token)
        repository = g.get_repo(f"{owner}/{repo}")
        
        # Get file name for repo path
        file_name = os.path.basename(file_path)
        
        # Try to update existing file or create new
        try:
            existing_file = repository.get_contents(file_name, ref=branch)
            repository.update_file(
                path=file_name,
                message=message,
                content=content,
                sha=existing_file.sha,
                branch=branch
            )
            return f"✓ Successfully updated {file_name} in {owner}/{repo}"
        except GithubException:
            # File doesn't exist, create it
            repository.create_file(
                path=file_name,
                message=message,
                content=content,
                branch=branch
            )
            return f"✓ Successfully created {file_name} in {owner}/{repo}"
    
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def create_github_repo(name: str, private: bool = False, description: str = "") -> str:
    """
    Create a new GitHub repository.
    
    Args:
        name: Repository name
        private: Make repository private (default: False)
        description: Repository description
    
    Returns:
        Success message with repo URL
    """
    try:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return "Error: GITHUB_TOKEN not found"
        
        g = Github(token)
        user = g.get_user()
        
        repo = user.create_repo(
            name=name,
            private=private,
            description=description,
            auto_init=True
        )
        
        return f"✓ Created repository: {repo.html_url}"
    
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def push_folder(owner: str, repo: str, folder_path: str, branch: str = "main", message: str = "Upload folder") -> str:
    """
    Push entire folder with all files to GitHub repository.
    
    Args:
        owner: GitHub username
        repo: Repository name
        folder_path: Local folder path to push
        branch: Branch name (default: main)
        message: Commit message
    
    Returns:
        Success or error message
    """
    try:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return "Error: GITHUB_TOKEN not found"
        
        if not os.path.exists(folder_path):
            return f"Error: Folder '{folder_path}' not found"
        
        if not os.path.isdir(folder_path):
            return f"Error: '{folder_path}' is not a folder"
        
        g = Github(token)
        repository = g.get_repo(f"{owner}/{repo}")
        
        uploaded = []
        errors = []
        
        # Walk through folder
        for root, dirs, files in os.walk(folder_path):
            # Skip hidden dirs
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                
                local_path = os.path.join(root, file)
                # Get relative path for repo
                rel_path = os.path.relpath(local_path, folder_path)
                repo_path = rel_path.replace('\\', '/')
                
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Try update or create
                    try:
                        existing = repository.get_contents(repo_path, ref=branch)
                        repository.update_file(repo_path, message, content, existing.sha, branch=branch)
                    except:
                        repository.create_file(repo_path, message, content, branch=branch)
                    
                    uploaded.append(repo_path)
                except Exception as e:
                    errors.append(f"{repo_path}: {str(e)}")
        
        result = f"✓ Uploaded {len(uploaded)} files to {owner}/{repo}"
        if errors:
            result += f"\n⚠ {len(errors)} errors: {errors[:3]}"
        return result
    
    except Exception as e:
        return f"Error: {str(e)}"


def get_github_tools():
    """Return list of direct GitHub tools"""
    return [quick_push_file, push_folder, create_github_repo]
