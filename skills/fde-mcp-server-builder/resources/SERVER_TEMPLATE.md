# Basic MCP Server Template (Python)

```python
from mcp_server import McpServer

server = McpServer(name="my-custom-tool")

@server.tool()
def my_tool(input_val: str) -> str:
    """Tool description for the LLM."""
    return f"Processed: {input_val}"

if __name__ == "__main__":
    server.run()
```
