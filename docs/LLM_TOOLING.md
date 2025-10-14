LLM Tooling Guide for MCP

Purpose

This document explains, in clear operational terms, how an external LLM / agent (not the MCP server) should interact with the CGM MCP server's tools and resources. It is written to be machine-readable and actionable by an LLM agent running outside of this repository.

Principles (apply these when deciding to call tools)

- Good Taste — First Principle: prefer elegant solutions that avoid special-case logic. If a choice can be made once (e.g., normalize repository paths) prefer a single canonical approach.
- Never Break Userspace: never make changes that could break existing user workflows or files without explicit confirmation.
- Pragmatism: call tools only when they add value. Avoid over-engineering.
- Simplicity Obsession: keep plans and code patches shallow (<= 3 levels of nested logic).
- Prioritize accuracy over deliverables: if the model lacks confidence or data, request clarification or repository context rather than guessing.

How tools are exposed

- Tools are exposed via the MCP `call_tool` mechanism.
- Each tool returns a list of TextContent objects. For these tools the primary content will typically be a single TextContent whose "text" field contains JSON (stringified) describing the result.
- Always parse the returned TextContent text as JSON when the tool description implies structured output.

Available core tools (short descriptions & schemas)

1) cgm_process_issue
- Purpose: Run the full CGM pipeline for an issue (rewriter → retriever → reranker → reader). Use for end-to-end issue resolution or when you need generated code patches.
- Input schema (JSON object):
  {
    "task_type": "issue_resolution" | "code_analysis" | "bug_fixing" | "feature_implementation",
    "repository_name": "string",              // must be repository identifier available to server
    "issue_description": "string",           // plain-text issue or task description
    "repository_context": { /* optional object: path, language, framework, etc. */ }
  }
- Best practices: provide repository_context.path when repository is not obvious. Keep issue_description focused (few sentences). Use this when you expect code changes.

2) cgm_get_task_status
- Purpose: Query the server for the status and results of a previously created task.
- Input schema:
  { "task_id": "string" }
- Returns: JSON representation of CGMResponse including status and possibly rewriter/retriever/reranker/reader outputs.
- Best practices: poll with exponential backoff and stop after a timeout period.

3) cgm_health_check
- Purpose: Lightweight server health check.
- Input: {} (empty object)
- Returns: JSON health summary.

Resources (readable via MCP resource APIs)

- cgm://health — server health JSON
- cgm://tasks  — active tasks JSON list

Agent behavior patterns and examples

- Decide whether you need a tool call
  * If you only need high-level guidance or to ask clarifying questions, do NOT call cgm_process_issue.
  * If you need concrete patches, file lists, or code edits, call cgm_process_issue.

- Two-step pattern (recommended) for changes:
  1) Call cgm_process_issue with a focused issue_description and repository_context (if available).
  2) Receive the CGMResponse from the tool (TextContent.text contains JSON). Parse it.
     - If status is "processing", record the returned task_id and poll using cgm_get_task_status until "completed" or "failed".
     - When "completed", inspect reader_result.patches (or equivalent) and present them to the user.

- Polling example (pseudocode JSON conversation intent):
  1) call_tool name=cgm_process_issue arguments={...}
  2) parse response -> {"task_id": "<uuid>", "status": "processing", ...}
  3) while status not in ["completed","failed"]:
       call_tool name=cgm_get_task_status arguments={"task_id": "<uuid>"}
       parse response
       wait backoff
  4) when completed: parse reader_result, extract patches and explanations

How to format `call_tool` arguments

- Always use JSON objects that match the tool's schema.
- Avoid sending excessively long issue_description; if necessary, summarize and include a focused excerpt.
- Example (cgm_process_issue):
  {
    "task_type": "issue_resolution",
    "repository_name": "my-project",
    "issue_description": "Authentication fails for users with non-ASCII characters in password; tests failing in auth/tests_auth.py",
    "repository_context": {"path": "/repos/my-project", "language": "python", "framework": "django"}
  }

Parsing responses

- Tools return a list of TextContent; take the first item and attempt to parse item.text as JSON.
- If parsing fails, treat item.text as plain-text explanation and ask a clarifying question.
- Typical successful `cgm_process_issue` response is a JSON-convertible CGMResponse object with fields: task_id, status, rewriter_result, retriever_result, reranker_result, reader_result, processing_time.

Error handling

- If the tool returns TextContent where the text begins with "Error:" treat it as a failure case and escalate or ask for clarification.
- For transient failures, retry the same call once after a small delay. For repeated failures, call cgm_health_check and include its output when asking for help.

Examples (concrete conversation snippets)

- Example 1 — Requesting analysis (no code change yet)
  User: "Why does authentication fail when a password contains emoji?"
  Agent:
    1) Ask clarifying questions if needed (e.g., which repo?).
    2) If repo provided, call cgm_process_issue with task_type="code_analysis" and an issue_description focused on the problem.
    3) Parse response when completed and summarize the most relevant files and suggested fixes.

- Example 2 — Requesting an actual patch
  User: "Fix password validation to accept unicode characters"
  Agent:
    1) Call cgm_process_issue with task_type="bug_fixing" and a precise repository_context.path
    2) When response completed, extract reader_result.patches (each patch contains file_path, original_code, modified_code, line_start, line_end, explanation)
    3) Present patches to the user and ask for confirmation before applying changes to the repo.

Conventions and constraints for LLM agents

- Do not modify repository files automatically without explicit user approval.
- Keep generated patches minimal and explain changes in 2–3 sentences.
- If multiple patches are produced, annotate each with a confidence score when available.
- If the model is uncertain, respond with the clarifying question rather than producing a speculative patch.

Tool-specific notes for the LLM model

- The server's Mock LLM provider is useful for quick local testing; however, production models may yield different outputs. Treat mock outputs as examples, not guarantees.
- Reader outputs are authoritative suggestions: still validate the patch and ask for user confirmation before applying.

Troubleshooting

- If cgm_process_issue fails at the rewriter stage: rephrase the issue_description to be more explicit and include repository path.
- If the server is unresponsive: call cgm_health_check and include its output when asking for support.

Appendix: Quick Reference

- call_tool name=cgm_process_issue arguments=<CGMRequest JSON>
- call_tool name=cgm_get_task_status arguments={"task_id": "<uuid>"}
- call_tool name=cgm_health_check arguments={}
- Resources: read_resource uri=cgm://health or cgm://tasks

End of LLM Tooling Guide
