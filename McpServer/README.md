# McpServer

MCP (Model Context Protocol) server that acts as a bridge between AI agents and the RemitApp API. Built with FastMCP, it exposes remittance operations as MCP tools that can be called by LLM agents. It also consumes RabbitMQ messages for transaction event monitoring.

## Features

- Exposes RemitApp API operations as MCP tools (login, register, KYC, transactions, etc.)
- Session management with JWT token persistence
- RabbitMQ consumer for transaction event monitoring
- Admin and user-level tool access

## Prerequisites

- Python 3.10+
- ApiServer running on localhost:8000
- RabbitMQ running on localhost:5672

## Installation

```bash
cd McpServer
pip install -r requirements.txt
```

## Run

```bash
python server.py
```

## Browser Access

- MCP endpoint: http://localhost:8001/mcp
