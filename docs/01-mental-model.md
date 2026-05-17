# Mental model (90 minutes, then hands-on)

## 1. Chat vs agent vs MCP

```
User question
    → [Host: Cursor / your script]
        → [LLM] decides next action
            → [Tool call] via function API OR via MCP
                → [Your code / MCP server] runs deterministic logic
            → observation back to LLM
        → repeat until stop
    → final answer
```

- **Chat:** one model call, maybe no tools.
- **Agent:** loop with tools and a stop condition.
- **MCP:** standard wire format so *any* host can use *your* tools without custom glue per IDE.

## 2. DE analogies

| DE | Agents/MCP |
|----|------------|
| Airflow DAG | Agent loop with max steps |
| Operator | Tool function |
| JDBC connector | MCP server |
| Data contract | JSON schema on tool I/O |
| Lineage | JSONL trace of tool calls |
| Read replica | Read-only DB role for tools |

## 3. Non-negotiables in production

1. **Deterministic tools** — LLM proposes; your code executes.
2. **Allowlists** — tables, SQL verbs, row limits.
3. **Timeouts** on every external call.
4. **Traces** — log tool name, args, result hash, latency.
5. **Evals** — golden questions before you trust a prompt change.

## 4. Read (skim, 30 min total)

- https://modelcontextprotocol.io/docs/learn/architecture
- https://cursor.com/docs/context/mcp (how Cursor discovers tools)

Then close the tabs and build.
