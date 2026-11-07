"""
Web Search and Documentation Tools
"""
import os
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from rich.console import Console

console = Console()


@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo and return results.
    
    Args:
        query: Search query
        num_results: Number of results to return (default: 5)
    
    Returns:
        Search results with titles and snippets
    """
    try:
        console.print(f"[cyan]🔍 Searching web for: {query}[/cyan]")
        
        # DuckDuckGo HTML search
        url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        console.print("[dim]→ Fetching results...[/dim]")
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for result in soup.find_all('div', class_='result')[:num_results]:
            title_elem = result.find('a', class_='result__a')
            snippet_elem = result.find('a', class_='result__snippet')
            
            if title_elem and snippet_elem:
                title = title_elem.get_text(strip=True)
                snippet = snippet_elem.get_text(strip=True)
                link = title_elem.get('href', '')
                
                results.append(f"**{title}**\n{snippet}\n{link}\n")
        
        console.print(f"[green]✓ Found {len(results)} results[/green]")
        return "\n".join(results) if results else "No results found"
    
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def read_webpage(url: str) -> str:
    """
    Read and extract text content from a webpage.
    
    Args:
        url: URL of the webpage to read
    
    Returns:
        Extracted text content
    """
    try:
        console.print(f"[cyan]📄 Reading webpage: {url}[/cyan]")
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        console.print("[dim]→ Fetching page...[/dim]")
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit to first 3000 chars
        text = text[:3000]
        
        console.print(f"[green]✓ Extracted {len(text)} characters[/green]")
        return text
    
    except Exception as e:
        return f"Error reading webpage: {str(e)}"


@tool
def search_langchain_docs(query: str) -> str:
    """
    Search LangChain official documentation.
    
    Args:
        query: Search query for LangChain docs
    
    Returns:
        Relevant documentation content
    """
    try:
        console.print(f"[cyan]📚 Searching LangChain docs: {query}[/cyan]")
        
        # Search LangChain docs
        search_url = f"https://python.langchain.com/docs/search?q={query}"
        console.print("[dim]→ Querying documentation...[/dim]")
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract search results
        results = []
        for item in soup.find_all('a', class_='search-result')[:3]:
            title = item.get_text(strip=True)
            link = "https://python.langchain.com" + item.get('href', '')
            results.append(f"**{title}**\n{link}\n")
        
        if not results:
            # Fallback: direct search
            console.print("[dim]→ Trying direct search...[/dim]")
            search_query = f"site:python.langchain.com {query}"
            return search_web.invoke({"query": search_query, "num_results": 3})
        
        console.print(f"[green]✓ Found {len(results)} docs[/green]")
        return "\n".join(results)
    
    except Exception as e:
        return f"Error searching docs: {str(e)}"


@tool
def search_langgraph_docs(query: str) -> str:
    """
    Search LangGraph official documentation.
    
    Args:
        query: Search query for LangGraph docs
    
    Returns:
        Relevant documentation content
    """
    try:
        console.print(f"[cyan]📚 Searching LangGraph docs: {query}[/cyan]")
        console.print("[dim]→ Querying documentation...[/dim]")
        
        search_query = f"site:langchain-ai.github.io/langgraph {query}"
        result = search_web.invoke({"query": search_query, "num_results": 3})
        
        console.print("[green]✓ Retrieved docs[/green]")
        return result
    
    except Exception as e:
        return f"Error searching docs: {str(e)}"


@tool
def search_mcp_docs(query: str) -> str:
    """
    Search Model Context Protocol (MCP) documentation.
    
    Args:
        query: Search query for MCP docs
    
    Returns:
        Relevant MCP documentation
    """
    try:
        console.print(f"[cyan]📚 Searching MCP docs: {query}[/cyan]")
        console.print("[dim]→ Querying documentation...[/dim]")
        
        search_query = f"site:modelcontextprotocol.io {query}"
        result = search_web.invoke({"query": search_query, "num_results": 3})
        
        console.print("[green]✓ Retrieved docs[/green]")
        return result
    
    except Exception as e:
        return f"Error searching docs: {str(e)}"


@tool
def search_python_docs(query: str) -> str:
    """
    Search Python official documentation.
    
    Args:
        query: Search query for Python docs
    
    Returns:
        Relevant Python documentation
    """
    try:
        console.print(f"[cyan]📚 Searching Python docs: {query}[/cyan]")
        console.print("[dim]→ Querying documentation...[/dim]")
        
        search_query = f"site:docs.python.org {query}"
        result = search_web.invoke({"query": search_query, "num_results": 3})
        
        console.print("[green]✓ Retrieved docs[/green]")
        return result
    
    except Exception as e:
        return f"Error searching docs: {str(e)}"


@tool
def search_stackoverflow(query: str) -> str:
    """
    Search Stack Overflow for programming questions and answers.
    
    Args:
        query: Search query
    
    Returns:
        Top Stack Overflow results
    """
    try:
        console.print(f"[cyan]💬 Searching Stack Overflow: {query}[/cyan]")
        console.print("[dim]→ Querying Stack Overflow...[/dim]")
        
        search_query = f"site:stackoverflow.com {query}"
        result = search_web.invoke({"query": search_query, "num_results": 5})
        
        console.print("[green]✓ Retrieved answers[/green]")
        return result
    
    except Exception as e:
        return f"Error searching Stack Overflow: {str(e)}"


@tool
def get_library_info(library_name: str) -> str:
    """
    Get information about a Python library from PyPI.
    
    Args:
        library_name: Name of the Python library
    
    Returns:
        Library information including description, version, and links
    """
    try:
        console.print(f"[cyan]📦 Getting info for: {library_name}[/cyan]")
        console.print("[dim]→ Fetching from PyPI...[/dim]")
        
        url = f"https://pypi.org/pypi/{library_name}/json"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        info = data['info']
        result = f"""
**{info['name']}** v{info['version']}

{info['summary']}

**Author:** {info.get('author', 'N/A')}
**License:** {info.get('license', 'N/A')}
**Homepage:** {info.get('home_page', 'N/A')}
**PyPI:** https://pypi.org/project/{library_name}/

**Description:**
{info.get('description', 'No description')[:500]}
"""
        
        console.print(f"[green]✓ Retrieved library info[/green]")
        return result
    
    except Exception as e:
        return f"Error getting library info: {str(e)}"


def get_web_tools():
    """Return list of web tools"""
    return [
        search_web,
        read_webpage,
        search_langchain_docs,
        search_langgraph_docs,
        search_mcp_docs,
        search_python_docs,
        search_stackoverflow,
        get_library_info,
    ]
