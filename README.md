# Code Assistant

An interactive terminal coding assistant built with LangGraph. It can inspect local projects, run tests, search documentation, create code screenshots, and perform GitHub operations after confirmation for remote-changing actions.

## Requirements

- Python 3.10 or later
- A Groq or Google API key

## Install and run

```bash
cd codeAssistent
python -m pip install -r requirements.txt
```

Create a `.env` file in this directory:

```env
GROQ_API_KEY=your_groq_key
# Or use: GOOGLE_API_KEY=your_google_key
# Optional for GitHub tools: GITHUB_TOKEN=your_github_token
```

Start the assistant for the current directory:

```bash
python main.py
```

Or point it at a project:

```bash
python main.py C:\path\to\project
```

## Commands

- `help` — show usage guidance
- `tools` — list loaded tools
- `clear` — start a new conversation session
- `exit`, `quit`, or `q` — close the assistant

## Project layout

```text
codeAssistent/
├── main.py                 # CLI entry point
├── agent.py                # Compatibility import for older integrations
├── app/
│   ├── agent.py            # Application orchestration
│   ├── invocation.py       # Model retry and fallback invocation policy
│   └── session.py          # Interactive terminal session and commands
├── requirements.txt        # Runtime dependencies
├── core/
│   ├── config.py           # Environment-backed settings
│   ├── llm.py              # Groq/Gemini setup
│   ├── memory.py           # Rolling five-message memory and compression
│   ├── prompts.py          # Shared LLM prompts
│   ├── state.py            # LangGraph state definition
│   └── workflow.py         # LangGraph nodes, edges, and routing
├── tools/
│   ├── registry.py         # Centralized tool loading
│   ├── executor.py         # Tool execution and confirmation policy
│   ├── repository_sandbox.py # GitHub clone, Docker checks, and PR publishing
│   ├── local_tools.py      # File inspection, writes, tests, project scan
│   ├── web_tools.py        # Web and documentation lookup
│   ├── github_direct.py    # GitHub write operations
│   ├── github_list.py      # GitHub read operations
│   └── screenshots.py      # Screen and code-image tools
└── utils/
    └── display.py          # Rich console rendering
```

## Notes

- Chat history is stored locally in `checkpoints.db` and is intentionally not removed during cleanup.
- The assistant keeps the latest five messages in full detail. Older messages are compressed into a persistent conversation summary and supplied as context for later requests.
- Gemini fallback uses `gemini-2.5-flash`, an available fast model. Groq is used first whenever both API keys are configured.
- GitHub write operations require confirmation in the terminal.
- GitHub repair uses a temporary sandbox and restricted Docker checks. Publishing creates a new branch and Pull Request; it never directly pushes to the default branch.
- Private GitHub repositories are supported when `GITHUB_TOKEN` is set. The token is passed only to the temporary Git clone process and is never stored in the clone URL or sandbox workspace.
- Do not commit `.env`, checkpoint sidecar files, generated screenshots, or backup files; they are excluded through `.gitignore`.
