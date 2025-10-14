AGENT TOOLING GUIDE

Purpose

This file tells an LLM/Agent exactly how to call the MCP server tools and the helper tools available in this environment. Be brief: show exact parameter shapes, examples, error handling, and operational principles the agent must follow.

Principles (follow always)

- Good Taste: Prefer simple, universal solutions. Avoid special-case branching in tool use.
- Never Break Userspace: Do not make changes that break existing functionality or user environments.
- Simplicity Obsession: Keep tool usage at one level of indirection; avoid deep nesting.
- Pragmatism: If data or context is insufficient, ask for it rather than guessing.

MCP Tools (how to call)

The MCP server implements tools that an MCP client (LLM) can call by name using JSON arguments. Example tools and exact shapes are below.

1) cgm_process_issue
- Purpose: Process an issue via the CGM pipeline
- Required fields: task_type, repository_name, issue_description
- Optional: repository_context (object)

Example call (JSON body that the MCP client passes to the Server.callTool API):

{
  "task_type": "issue_resolution",
  "repository_name": "my-project",
  "issue_description": "Tests failing when submitting empty form",
  "repository_context": { "path": "/path/to/repo", "language": "python" }
}

Response: The server returns a CGMResponse JSON object. If you need a task id to poll, read response.task_id and call cgm_get_task_status.

2) cgm_get_task_status
- Purpose: Query a stored task result
- Required fields: task_id

Example: { "task_id": "<uuid>" }

3) cgm_health_check
- Purpose: Get server/LLM health
- No parameters: {} 

MCP Resource Access

Resources are listed under URIs like cgm://health and cgm://tasks. Request them via the MCP readResource API; responses are JSON strings.

Helper tools available to the Agent (this environment)

These are the environment helper functions exposed to the agent. Use them when appropriate.

1) task_tracker
- Purpose: Track and manage task progress inside the agent session
- Use cases: planning multi-step work, marking tasks in_progress/done
- Example call (plan):

{
  "command": "plan",
  "task_list": [
    {"id":"1","title":"Run tests","status":"todo","notes":"Run pytest -q"}
  ]
}

- Example call (view): { "command": "view" }

2) str_replace_editor
- Purpose: View or edit repository files
- Modes: view, create, str_replace, insert, undo_edit
- Important: str_replace requires an exact-match old_str including whitespace; insert needs an insert_line index (1-based).

Example: create a new file

{
  "command": "create",
  "path": "/workspace/cgm-mcp/docs/EXAMPLE.md",
  "file_text": "Example content\n"
}

Example: insert after line 56 in README.md

{
  "command": "insert",
  "path": "/workspace/cgm-mcp/README.md",
  "insert_line": 56,
  "new_str": "- [Agent Tooling Guide](#agent-tooling-guide)\n"
}

3) execute_bash
- Purpose: Run shell commands in a persistent shell session
- Use for git, tests, and running scripts
- Security: Considered MEDIUM risk (modifies files). Avoid commands that exfiltrate secrets.

Example:

{ "command": "git add . && git commit -m \"docs: add agent tooling guide\" -m \"Co-authored-by: openhands <openhands@all-hands.dev>\"", "is_input": "false", "timeout": 30 }

4) execute_ipython_cell
- Purpose: Run Python code in an IPython kernel for quick experiments
- Provide only the code string

Example:

{ "code": "print('hello from ipython')" }

5) browser
- Purpose: Interact with webpages (automated clicks/forms) when strictly necessary
- Use only for pages that cannot be reached via API. Actions are given as a small list of commands.

6) think
- Purpose: Log internal reasoning / planning. Non-operative; does not change files. Use to record hypotheses.

7) request_condensation
- Purpose: Ask the system to condense long conversation history into a summary.

8) finish
- Purpose: Signal that the agent has completed its task. Include a short summary of actions and next steps.

Multi-tool parallel execution

- Use multi_tool_use.parallel only if the tools operate independently and in parallel. Provide an array of tool usages. Do not use parallel for operations that must be sequential or share state.

Error handling and best practices

- Always validate server responses. If a tool returns an error string, surface it and do not assume success.
- For file edits with str_replace: always call view() first, capture the exact lines, and then call str_replace with exact old_str.
- When running shell commands that change repository state, commit with a clear message and Co-authored-by: openhands <openhands@all-hands.dev> (per repository policy). Do not push to remote.
- If a requested operation would break existing behaviour (API changes, removing files), ask the user for confirmation.

What to ask the user for when missing context

- Absolute repository path if not present in repository_context
- Desired branch name for changes (do not push to remote unless asked)
- Whether tests should be run automatically after edits

Examples (end-to-end)

- To process an issue and check result:
  1) Call MCP tool cgm_process_issue with JSON from above
  2) Read tool response; get task_id
  3) Call cgm_get_task_status periodically until status is completed
  4) If patches are returned, use str_replace_editor to apply exact edits

- To add documentation file and commit:
  1) Use str_replace_editor.create to create file
  2) Use execute_bash to run git add and git commit (set git user if missing)

Appendix: quick reference

- str_replace_editor.view -> view files and line ranges
- str_replace_editor.str_replace -> replace exact block
- str_replace_editor.insert -> insert after line N (1-based)
- task_tracker.plan/view -> plan and inspect tasks
- execute_bash -> single command string; prefer chaining with &&
- execute_ipython_cell -> run python snippets
- finish -> send final message and outcomes

