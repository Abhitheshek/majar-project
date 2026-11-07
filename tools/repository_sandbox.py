"""Safe, temporary GitHub repository workspaces backed by Docker checks."""

import os
import base64
import shutil
import subprocess
import tempfile
from urllib.parse import unquote, urlparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from github import Github, GithubException
from langchain_core.tools import tool
from rich.console import Console


MAX_FILE_SIZE = 1_000_000
_active_workspace: "RepositoryWorkspace | None" = None
console = Console()


@dataclass
class RepositoryWorkspace:
    owner: str
    repository: str
    root: Path
    default_branch: str
    repository_root: Path

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repository}"

    def resolve(self, relative_path: str) -> Path:
        relative_path = relative_path.replace("\\", "/")
        # Models sometimes repeat the selected folder name. The sandbox root is
        # already that folder, so normalize this harmless duplicate prefix.
        if relative_path == self.root.name:
            relative_path = "."
        elif relative_path.startswith(f"{self.root.name}/"):
            relative_path = relative_path[len(self.root.name) + 1:]
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Path must stay inside the sandbox repository")
        return candidate


def _workspace() -> RepositoryWorkspace:
    if _active_workspace is None:
        raise RuntimeError("No sandbox repository is active. Clone a GitHub repository first.")
    return _active_workspace


def has_active_sandbox() -> bool:
    """Return whether an isolated repository workspace is currently active."""
    return _active_workspace is not None


def _parse_github_url(repository_url: str) -> tuple[str, str, str | None, str]:
    parsed = urlparse(repository_url.strip())
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if parsed.scheme != "https" or parsed.netloc != "github.com" or len(parts) < 2:
        raise ValueError("Use a GitHub HTTPS URL, for example https://github.com/owner/repository")
    owner, repository = parts[0], parts[1].removesuffix(".git")
    branch = None
    subdirectory = ""
    if len(parts) > 2:
        if len(parts) < 4 or parts[2] != "tree":
            raise ValueError("GitHub URLs may optionally use /tree/<branch>/<folder>")
        branch = parts[3]
        subdirectory = "/".join(parts[4:])
    return owner, repository, branch, subdirectory


def _run(
    command: list[str],
    cwd: Path | None = None,
    timeout: int = 120,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if environment:
        env.update(environment)
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def _git_auth_environment(token: str | None) -> dict[str, str]:
    """Provide a GitHub token to one Git process without persisting it anywhere."""
    if not token:
        return {}
    basic_credentials = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
        "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {basic_credentials}",
    }


def _redact(value: str, secret: str | None) -> str:
    return value.replace(secret, "[REDACTED]") if secret else value


def _docker_is_available() -> tuple[bool, str]:
    """Check that the local Docker daemon is reachable before starting a sandbox."""
    try:
        result = _run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=15)
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or "Docker daemon is unavailable"
    except FileNotFoundError:
        return False, "Docker CLI is not installed"
    except subprocess.TimeoutExpired:
        return False, "Docker daemon did not respond in time"


@tool
def clone_github_repository(repository_url: str) -> str:
    """Clone a GitHub repository into an isolated temporary workspace.

    Args:
        repository_url: HTTPS URL such as https://github.com/owner/repository
    """
    global _active_workspace
    try:
        console.print("[cyan]Step 1/3: Validating GitHub repository URL...[/cyan]")
        owner, repository, branch, subdirectory = _parse_github_url(repository_url)
        if (
            _active_workspace
            and _active_workspace.owner == owner
            and _active_workspace.repository == repository
            and _active_workspace.root.name == (Path(subdirectory).name if subdirectory else repository)
        ):
            return f"Sandbox already active for {_active_workspace.full_name} at {_active_workspace.root}. Reusing it."
        console.print("[cyan]Step 2/3: Cloning repository into a temporary sandbox...[/cyan]")
        sandbox_root = Path(tempfile.mkdtemp(prefix="code-assistant-repo-"))
        clone_url = f"https://github.com/{owner}/{repository}.git"
        token = os.getenv("GITHUB_TOKEN")
        command = ["git", "-c", "core.hooksPath=", "clone", "--depth", "1"]
        if branch:
            command.extend(["--branch", branch])
        command.extend([clone_url, str(sandbox_root)])
        result = _run(command, timeout=180, environment=_git_auth_environment(token))
        if result.returncode:
            shutil.rmtree(sandbox_root, ignore_errors=True)
            return f"Clone failed: {_redact(result.stderr.strip(), token)}"

        console.print("[cyan]Step 3/3: Selecting requested project folder...[/cyan]")
        default_branch = _run(["git", "branch", "--show-current"], sandbox_root).stdout.strip() or "main"
        project_root = (sandbox_root / subdirectory).resolve()
        if sandbox_root not in project_root.parents and project_root != sandbox_root or not project_root.is_dir():
            shutil.rmtree(sandbox_root, ignore_errors=True)
            return f"Requested repository folder was not found: {subdirectory}"
        _active_workspace = RepositoryWorkspace(owner, repository, project_root, default_branch, sandbox_root)
        return (
            f"Sandbox ready for {_active_workspace.full_name}. Workspace is isolated at {project_root}. "
            "Use scan_sandbox_repository before making repairs."
        )
    except Exception as error:
        return f"Sandbox clone error: {error}"


@tool
def scan_sandbox_repository() -> str:
    """Inspect the active sandbox for its stack, dependency manifests, and deprecated markers."""
    try:
        workspace = _workspace()
        console.print("[cyan]Scanning dependency manifests and deprecated code markers...[/cyan]")
        manifests = [name for name in ("pyproject.toml", "requirements.txt", "package.json", "pom.xml", "go.mod") if (workspace.root / name).exists()]
        findings: list[str] = []
        for path in workspace.root.rglob("*"):
            if not path.is_file() or ".git" in path.parts or path.stat().st_size > 300_000:
                continue
            if path.suffix not in {".py", ".js", ".ts", ".java", ".md", ".txt"}:
                continue
            try:
                count = path.read_text(encoding="utf-8", errors="ignore").lower().count("deprecated")
                if count:
                    findings.append(f"{path.relative_to(workspace.root)}: {count} deprecated marker(s)")
            except OSError:
                continue
        files = _list_files(workspace.root)
        return (
            f"Repository: {workspace.full_name}\nDefault branch: {workspace.default_branch}\n"
            f"Manifests: {', '.join(manifests) or 'none detected'}\n"
            f"Deprecated markers: {'; '.join(findings[:20]) or 'none found'}\n"
            f"Files (relative to sandbox root): {', '.join(files[:40]) or 'none found'}\n"
            "Use these relative paths with read_sandbox_file. Do not use host file tools."
        )
    except Exception as error:
        return f"Sandbox scan error: {error}"


@tool
def read_sandbox_file(relative_path: str) -> str:
    """Read a file from the active sandbox using a repository-relative path."""
    try:
        console.print(f"[cyan]Reading sandbox file: {relative_path}[/cyan]")
        path = _workspace().resolve(relative_path)
        if not path.is_file():
            return f"File not found: {relative_path}"
        if path.stat().st_size > MAX_FILE_SIZE:
            return f"File is too large to read safely: {relative_path}"
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as error:
        return f"Sandbox read error: {error}"


@tool
def list_sandbox_files(directory: str = ".") -> str:
    """List files in the active sandbox. Paths are relative to its selected project folder."""
    try:
        workspace = _workspace()
        folder = workspace.resolve(directory)
        if not folder.is_dir():
            return f"Sandbox directory not found: {directory}"
        return "\n".join(_list_files(folder, base=workspace.root)) or "No files found."
    except Exception as error:
        return f"Sandbox list error: {error}"


@tool
def write_sandbox_file(relative_path: str, content: str) -> str:
    """Write a file only inside the active temporary sandbox repository."""
    try:
        console.print(f"[cyan]Updating sandbox file: {relative_path}[/cyan]")
        path = _workspace().resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Updated sandbox file: {relative_path}"
    except Exception as error:
        return f"Sandbox write error: {error}"


@tool
def run_sandbox_checks(command: str = "") -> str:
    """Run a check inside a restricted Docker container with no network access.

    Args:
        command: Optional test command. A safe language-aware default is used when omitted.
    """
    try:
        workspace = _workspace()
        console.print("[cyan]Checking Docker sandbox availability...[/cyan]")
        available, detail = _docker_is_available()
        if not available:
            return f"Sandbox check unavailable: {detail}. Start Docker Desktop and retry."
        is_node = (workspace.root / "package.json").exists()
        image = "node:22-alpine" if is_node else "python:3.12-slim"
        default_command = "npm test" if is_node else "python -m compileall -q ."
        console.print(f"[cyan]Running restricted Docker check with {image}...[/cyan]")
        result = _run([
            "docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--memory", "1g", "--cpus", "1",
            "--pids-limit", "256", "-v", f"{workspace.root}:/workspace:rw", "-w", "/workspace",
            image, "sh", "-lc", command or default_command,
        ], timeout=300)
        output = (result.stdout + result.stderr).strip()[-6000:]
        return f"Sandbox check exit code: {result.returncode}\n{output}"
    except Exception as error:
        return f"Sandbox check error: {error}"


@tool
def publish_sandbox_changes(title: str = "Agent repair", body: str = "Automated repair verified in sandbox.") -> str:
    """Publish sandbox changes to a new GitHub branch and open a Pull Request. Never pushes to main."""
    try:
        workspace = _workspace()
        console.print("[cyan]Checking sandbox changes before publishing...[/cyan]")
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return "Error: GITHUB_TOKEN not configured"
        target_path = workspace.root.relative_to(workspace.repository_root)
        status = _run(
            ["git", "status", "--porcelain", "--", str(target_path)], workspace.repository_root
        ).stdout.splitlines()
        if not status:
            return "No sandbox changes to publish."
        branch_name = f"agent/repair-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        repo = Github(token).get_repo(workspace.full_name)
        console.print(f"[cyan]Creating GitHub branch: {branch_name}[/cyan]")
        base = repo.get_branch(workspace.default_branch)
        repo.create_git_ref(f"refs/heads/{branch_name}", base.commit.sha)
        for line in status:
            change_type, relative_path = line[:2], line[3:]
            if " -> " in relative_path:
                return "Publish error: renamed files are not supported yet; repair the rename manually first."
            path = (workspace.repository_root / relative_path).resolve()
            if workspace.repository_root not in path.parents and path != workspace.repository_root:
                return "Publish error: changed file path escaped the repository root."
            if "D" in change_type:
                console.print(f"[cyan]Deleting remote file: {relative_path}[/cyan]")
                existing = repo.get_contents(relative_path, ref=branch_name)
                repo.delete_file(relative_path, title, existing.sha, branch=branch_name)
                continue
            if not path.is_file() or path.stat().st_size > MAX_FILE_SIZE:
                continue
            console.print(f"[cyan]Publishing file: {relative_path}[/cyan]")
            try:
                existing = repo.get_contents(relative_path, ref=branch_name)
                repo.update_file(relative_path, title, path.read_text(encoding="utf-8"), existing.sha, branch=branch_name)
            except GithubException:
                repo.create_file(relative_path, title, path.read_text(encoding="utf-8"), branch=branch_name)
        console.print("[cyan]Creating Pull Request...[/cyan]")
        pull_request = repo.create_pull(title=title, body=body, head=branch_name, base=workspace.default_branch)
        return f"Created branch {branch_name} and Pull Request: {pull_request.html_url}"
    except Exception as error:
        return f"Publish error: {error}"


def get_repository_sandbox_tools() -> list:
    return [clone_github_repository, scan_sandbox_repository, list_sandbox_files, read_sandbox_file, write_sandbox_file, run_sandbox_checks, publish_sandbox_changes]


def _list_files(folder: Path, base: Path | None = None) -> list[str]:
    """Return a bounded, ignored-directory-aware list of workspace files."""
    base = base or folder
    ignored = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    files: list[str] = []
    for path in sorted(folder.rglob("*")):
        if any(part in ignored for part in path.parts) or not path.is_file():
            continue
        files.append(str(path.relative_to(base)).replace("\\", "/"))
    return files
