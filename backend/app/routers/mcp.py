from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services.mcp_server import mcp_server

router = APIRouter(prefix="/v1/mcp", tags=["Model Context Protocol (MCP)"])

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

@router.get("/tools")
def list_mcp_tools():
    """Lists available MCP tools for Enterprise AI Agent invocation."""
    return {"tools": mcp_server.get_tool_definitions()}

@router.post("/execute")
def execute_mcp_tool(request: ToolCallRequest):
    """Executes an MCP tool call on behalf of an AI agent."""
    result = mcp_server.execute_tool(request.tool_name, request.arguments)
    return {"tool_name": request.tool_name, "result": result}
