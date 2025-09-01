#!/usr/bin/env python3
"""
Calculator MCP Service - Example implementation for l8e-harbor

This is a Model Context Protocol (MCP) service that provides basic calculator
functionality. It demonstrates how l8e-harbor can proxy MCP services with
full observability and logging.

Usage:
    python calculator_mcp.py

Or with uvicorn:
    uvicorn calculator_mcp:app --host 0.0.0.0 --port 3000
"""

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional
import json
import logging
import asyncio

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("calculator-mcp")

app = FastAPI(
    title="Calculator MCP Service",
    description="A Model Context Protocol service providing calculator tools",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# JSON-RPC request schema
class JSONRPCRequest(BaseModel):
    jsonrpc: str
    id: int
    method: str
    params: Optional[Dict[str, Any]] = {}

    class Config:
        extra = "forbid"

# JSON-RPC response helpers
def jsonrpc_response(id: int, result: Any = None, error: Dict = None) -> Dict:
    """Create a JSON-RPC 2.0 response"""
    resp = {"jsonrpc": "2.0", "id": id}
    if result is not None:
        resp["result"] = result
    if error is not None:
        resp["error"] = error
    return resp

def jsonrpc_error(id: int, code: int, message: str, data: Any = None) -> Dict:
    """Create a JSON-RPC 2.0 error response"""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return jsonrpc_response(id, error=error)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Calculator MCP",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "mcp": "POST /",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health_check():
    """Dedicated health check for load balancers"""
    return {"status": "healthy", "service": "calculator-mcp"}

@app.post("/")
async def mcp_handler(request: Request):
    """Main MCP JSON-RPC handler"""
    try:
        # Parse the JSON-RPC request
        payload = await request.json()
        logger.info(f"Received request: {json.dumps(payload, indent=2)}")
        
        # Validate JSON-RPC structure
        try:
            req = JSONRPCRequest(**payload)
        except ValidationError as e:
            logger.error(f"Invalid JSON-RPC request: {e}")
            return jsonrpc_error(-1, -32600, "Invalid Request", str(e))
        
        # Handle different MCP methods
        if req.method == "initialize":
            return handle_initialize(req)
        elif req.method == "tools/list":
            return handle_tools_list(req)
        elif req.method == "tools/call":
            return handle_tools_call(req)
        else:
            logger.warning(f"Unknown method: {req.method}")
            return jsonrpc_error(req.id, -32601, "Method not found")
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return jsonrpc_error(-1, -32700, "Parse error")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonrpc_error(-1, -32603, "Internal error")

def handle_initialize(req: JSONRPCRequest) -> Dict:
    """Handle MCP initialize request"""
    logger.info("MCP client initializing")
    return jsonrpc_response(req.id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "calculator-mcp",
            "version": "1.0.0"
        }
    })

def handle_tools_list(req: JSONRPCRequest) -> Dict:
    """Return list of available tools"""
    logger.info("Client requesting tool list")
    
    tools = [
        {
            "name": "calculator",
            "description": "Evaluate basic mathematical expressions safely",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4')"
                    }
                },
                "required": ["expression"]
            }
        },
        {
            "name": "convert_units",
            "description": "Convert between common units",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "Value to convert"
                    },
                    "from_unit": {
                        "type": "string",
                        "description": "Source unit (e.g., 'celsius', 'fahrenheit', 'meters', 'feet')"
                    },
                    "to_unit": {
                        "type": "string", 
                        "description": "Target unit"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        }
    ]
    
    return jsonrpc_response(req.id, {"tools": tools})

def handle_tools_call(req: JSONRPCRequest) -> Dict:
    """Execute a tool call"""
    params = req.params or {}
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    logger.info(f"Calling tool '{tool_name}' with args: {arguments}")
    
    if tool_name == "calculator":
        return handle_calculator(req.id, arguments)
    elif tool_name == "convert_units":
        return handle_unit_conversion(req.id, arguments)
    else:
        return jsonrpc_error(req.id, -32602, f"Unknown tool: {tool_name}")

def handle_calculator(request_id: int, args: Dict) -> Dict:
    """Handle calculator tool calls"""
    expression = args.get("expression", "")
    
    if not expression:
        return jsonrpc_error(request_id, -32602, "Missing expression parameter")
    
    try:
        # Safe evaluation - only allow basic math operations
        allowed_names = {
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            'pow': pow,
            'sum': sum,
        }
        
        # Evaluate the expression safely
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        result_str = str(result)
        
        logger.info(f"Calculator: '{expression}' = {result_str}")
        
        return jsonrpc_response(request_id, {
            "content": [
                {
                    "type": "text",
                    "text": f"Result: {result_str}"
                }
            ]
        })
        
    except Exception as e:
        error_msg = f"Error evaluating '{expression}': {str(e)}"
        logger.error(error_msg)
        return jsonrpc_error(request_id, -32000, "Calculation error", error_msg)

def handle_unit_conversion(request_id: int, args: Dict) -> Dict:
    """Handle unit conversion tool calls"""
    try:
        value = args.get("value")
        from_unit = args.get("from_unit", "").lower()
        to_unit = args.get("to_unit", "").lower()
        
        if value is None or not from_unit or not to_unit:
            return jsonrpc_error(request_id, -32602, "Missing required parameters")
        
        # Temperature conversions
        if from_unit == "celsius" and to_unit == "fahrenheit":
            result = (value * 9/5) + 32
        elif from_unit == "fahrenheit" and to_unit == "celsius":
            result = (value - 32) * 5/9
        elif from_unit == "celsius" and to_unit == "kelvin":
            result = value + 273.15
        elif from_unit == "kelvin" and to_unit == "celsius":
            result = value - 273.15
        
        # Length conversions
        elif from_unit == "meters" and to_unit == "feet":
            result = value * 3.28084
        elif from_unit == "feet" and to_unit == "meters":
            result = value / 3.28084
        elif from_unit == "kilometers" and to_unit == "miles":
            result = value * 0.621371
        elif from_unit == "miles" and to_unit == "kilometers":
            result = value / 0.621371
            
        else:
            return jsonrpc_error(request_id, -32602, f"Unsupported conversion: {from_unit} to {to_unit}")
        
        result_text = f"{value} {from_unit} = {result:.4f} {to_unit}"
        logger.info(f"Unit conversion: {result_text}")
        
        return jsonrpc_response(request_id, {
            "content": [
                {
                    "type": "text",
                    "text": result_text
                }
            ]
        })
        
    except Exception as e:
        error_msg = f"Unit conversion error: {str(e)}"
        logger.error(error_msg)
        return jsonrpc_error(request_id, -32000, "Conversion error", error_msg)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Calculator MCP Service...")
    uvicorn.run(
        "calculator_mcp:app",
        host="0.0.0.0", 
        port=3001,
        reload=False,
        log_level="info"
    )