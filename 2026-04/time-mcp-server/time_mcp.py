#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
from zoneinfo import ZoneInfo
from tzlocal import get_localzone_name
import sys

import json


def get_current_time(timezone_name) -> dict:
    """
    Get current time in specified timezone
    {"jsonrpc": "2.0","id": 1,"method": "tools/call","params":{"name": "get_current_time","arguments": {"timezone": "Europe/Warsaw"}}}
    """
    if not timezone_name:
        timezone_name = get_localzone_name()
    timezone = ZoneInfo(timezone_name)
    current_time = datetime.now(timezone)

    return {
        "timezone": timezone_name,
        "datetime": current_time.isoformat(timespec="seconds"),
        "day_of_week": current_time.strftime("%A"),
        "is_dst": bool(current_time.dst()),
    }

def get_current_time_tool_desc() -> dict:
    local_tz = get_localzone_name()
    return {
        "name": "get_current_time",
        "title": "Get current time",
        "description": "Get current time in a specific timezones by default uses current time timezone. Reads time from clock.\n\nIMPORTANT: Do call it whenever you need current time",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": f"IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use '{local_tz}' as local timezone if no timezone provided by the user.",
                }
            },
            "required": [],
        },
        "annotations": {
            "readOnlyHint": True
        },
        "execution": {
            "taskSupport": "forbidden"
        }
    }

def list_tools(cmd) -> dict:
    """
    {"jsonrpc": "2.0","id": 1,"method": "tools/list","params": {}}
    """
    tools = [get_current_time_tool_desc()]
    return {
        "result": {
            "tools": tools
        },
        "jsonrpc": "2.0",
        "id": cmd['id']
    }


def call_tools(cmd):
    params = cmd["params"]
    if params["name"] == "get_current_time":
        dt = get_current_time(params['arguments'].get('timezone'))
        return {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(dt)
                    }
                ]
            },
            "jsonrpc": "2.0",
            "id": cmd['id']
        }
    return {}

def initialize(cmd):
    return {
        "result":
            {
                "protocolVersion": "2025-11-25",
                "capabilities":
                    {
                        "tools":
                            {
                                "listChanged": True
                            }
                    },
                "serverInfo":
                    {
                        "name": "Time server",
                        "version": "0.0.1",
                        "websiteUrl": "https://example.com",
                        "description": "Test time mcp server.",
                        "icons":
                            [
                                {
                                    "src": "",
                                    "mimeType": "image/png"
                                }
                            ]
                    },
                "instructions": "Use this server to everything that is related to time whenever user asks about current time. Use even when you think you know the answer -- your training data may not reflect recent changes."
            },
        "jsonrpc": "2.0",
        "id": cmd['id']
    }


def execute(cmd: dict) -> dict:
    if "method" not in cmd:
        return {}
    if cmd["method"] == "initialize":
        return initialize(cmd)
    elif cmd["method"] == "tools/list":
        return list_tools(cmd)
    elif cmd["method"] == "tools/call":
        return call_tools(cmd)
    return {}

def start_stdin():
    for line in sys.stdin:
        try:
            cmd = json.loads(line)
            out = execute(cmd)
            if out:
                sys.stdout.write(f"{json.dumps(out)}\n")
        except Exception as e:
            pass

def start_server():
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    @app.post('/mcp')
    async def mcp(req: Request):
        cmd = await req.json()
        return execute(cmd)

    uvicorn.run(app, port=3001)

if __name__ == '__main__':
    if sys.argv[-1] == 'stdin':
        start_stdin()
    else:
        start_server()
