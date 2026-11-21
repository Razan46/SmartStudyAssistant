"""Small stdio MCP client for the existing Smart Study Assistant server."""

import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_PATH = BASE_DIR / "server.py"


class MCPClientError(RuntimeError):
    """Raised when the MCP server or protocol operation fails."""


class StudyMCPClient:
    """Run a real MCP stdio session against this project's server.py."""

    def _run(self, operation, *args):
        try:
            return anyio.run(self._request, operation, *args)
        except MCPClientError:
            raise
        except Exception as exc:
            raise MCPClientError(f"MCP communication failed: {exc}") from exc

    async def _request(self, operation, *args):
        server = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER_PATH)],
            cwd=str(BASE_DIR),
        )
        async with stdio_client(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await operation(session, *args)

    @staticmethod
    def _dump(value):
        return value.model_dump(mode="json", by_alias=True)

    async def _list_capabilities(self, session):
        tools = await session.list_tools()
        resources = await session.list_resources()
        prompts = await session.list_prompts()
        return {
            "tools": self._dump(tools).get("tools", []),
            "resources": self._dump(resources).get("resources", []),
            "prompts": self._dump(prompts).get("prompts", []),
        }

    def list_capabilities(self):
        return self._run(self._list_capabilities)

    async def _list_tools(self, session):
        return self._dump(await session.list_tools()).get("tools", [])

    async def _list_resources(self, session):
        return self._dump(await session.list_resources()).get("resources", [])

    async def _list_prompts(self, session):
        return self._dump(await session.list_prompts()).get("prompts", [])

    def list_tools(self):
        return self._run(self._list_tools)

    def list_resources(self):
        return self._run(self._list_resources)

    def list_prompts(self):
        return self._run(self._list_prompts)

    async def _read_resource(self, session, uri):
        result = await session.read_resource(uri)
        return [self._dump(item) for item in result.contents]

    def read_resource(self, uri):
        return self._run(self._read_resource, uri)

    async def _get_prompt(self, session, name, arguments):
        result = await session.get_prompt(name, arguments)
        return self._dump(result)

    def get_prompt(self, name, arguments=None):
        return self._run(self._get_prompt, name, arguments or {})

    async def _call_tool(self, session, name, arguments):
        result = await session.call_tool(name, arguments)
        if result.isError:
            message = " ".join(
                item.text for item in result.content if getattr(item, "type", None) == "text"
            )
            raise MCPClientError(message or f"MCP tool {name!r} returned an error.")
        if result.structuredContent is not None:
            return result.structuredContent
        return [self._dump(item) for item in result.content]

    def call_tool(self, name, arguments=None):
        return self._run(self._call_tool, name, arguments or {})


mcp_client = StudyMCPClient()
