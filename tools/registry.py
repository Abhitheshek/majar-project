"""Central registry for all tools exposed to the assistant."""

from .github_direct import get_github_tools
from .github_list import get_github_list_tools
from .local_tools import get_local_tools
from .screenshots import get_screenshot_tools
from .repository_sandbox import get_repository_sandbox_tools
from .web_tools import get_web_tools


def load_tools() -> dict[str, list]:
    """Load tool groups without coupling the agent to individual modules."""
    return {
        "local": get_local_tools(),
        "screenshots": get_screenshot_tools(),
        "github": get_github_tools() + get_github_list_tools(),
        "web": get_web_tools(),
        "repository sandbox": get_repository_sandbox_tools(),
    }
