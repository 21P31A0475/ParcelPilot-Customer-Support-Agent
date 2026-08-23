# Architecture Note

```text
User
 ↓
Agent node
 ↓
tools_condition
 ↓
ToolNode
 ↓
MCP tools
 ├─ account lookup
 ├─ order lookup
 ├─ ticket lookup
 ├─ document search
 ├─ proactive issue detection
 └─ prepare action tools
 ↓
Check action
 ↓
Human Review (interrupt)
 ↓
Execute action
 ↓
Agent
```

The core graph intentionally mirrors the trainer's LangGraph + MCP example: MCP tools are loaded with `MultiServerMCPClient`, bound with `llm.bind_tools(tools)`, executed by `ToolNode`, and routed with `tools_condition`.
