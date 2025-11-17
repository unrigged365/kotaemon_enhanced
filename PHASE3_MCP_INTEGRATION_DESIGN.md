# Phase 3: MCP (Model Context Protocol) Integration Design

## Executive Summary

This document defines the MCP (Model Context Protocol) integration layer that enables agents to dynamically access external tools and data sources. MCP provides a standardized interface for agents to:

- **Discover available tools** at runtime
- **Request tool execution** with parameters
- **Access diverse data sources**: Vector DB, SQL, Knowledge Graph, Web Search, File System, APIs, Code Execution
- **Enforce permission boundaries** (which agent can use which tool)
- **Handle tool failures gracefully** with fallbacks

**Core Concept**: Instead of agents directly calling Kotaemon components, they can also request external tools via MCP protocol.

**Current State**:
- Agents only have access to Kotaemo components (BM25, Vector Search, LLM, etc.)
- No access to external data (real-time web, structured databases, APIs)

**After MCP Integration**:
- Agents can call 7 different tool categories
- Each tool has standardized interface
- Permission system controls access
- Async execution with result caching

---

## Problem Statement

### Current Limitations (Without MCP)

1. **Limited Data Sources**
   - Only access to indexed documents (vector + document store)
   - No real-time information (web search)
   - No structured data (SQL queries)
   - No semantic knowledge graphs

2. **No External Tool Access**
   - Can't call external APIs (weather, finance, etc.)
   - Can't execute code dynamically
   - Can't interact with file systems

3. **Monolithic Tool Integration**
   - Each new tool requires code change
   - No runtime tool discovery
   - Hard to scale/version tools

4. **No Granular Control**
   - All agents can access all data sources
   - No permission model
   - Audit trail missing

### Desired Behavior (With MCP)

✅ **Dynamic Tool Discovery** - Agents see all available tools at startup
✅ **Multiple Data Sources** - Vector, SQL, Web, File System, APIs
✅ **Permission Boundaries** - Intent Agent can't call SQL, Citation Agent can't use Web Search
✅ **Tool Versioning** - Multiple versions of same tool (v1, v2)
✅ **Error Recovery** - Tool fails? Try alternative approach
✅ **Audit & Monitoring** - Track which agent called which tool
✅ **Async Execution** - Long-running tools don't block
✅ **Result Caching** - Reuse results for same query

---

## Design Goals

1. **Standardization**: Define unified interface for all tools
2. **Extensibility**: Easy to add new tools without breaking existing
3. **Security**: Permission boundaries enforce who can use what
4. **Observability**: Track all tool calls and results
5. **Performance**: Caching, parallelization, result reuse
6. **Resilience**: Handle tool failures gracefully
7. **Maintainability**: Clear separation between tools

---

## Architecture Diagram

### High-Level MCP Integration

```
┌─────────────────────────────────┐
│ Agent (IntentAgent, Retriever,  │
│  Generator, etc.)               │
└────────────┬────────────────────┘
             │ "Call tool: web_search"
             ↓
┌──────────────────────────────────┐
│ MCP Client                       │
│ (inside each agent)              │
├──────────────────────────────────┤
│ - Format request                 │
│ - Check permissions              │
│ - Send to MCP Server             │
│ - Parse response                 │
└────────────┬─────────────────────┘
             │ HTTP/gRPC Request
             ↓
┌──────────────────────────────────┐
│ MCP Server                       │
│ (orchestrates tools)             │
├──────────────────────────────────┤
│ - Receive request                │
│ - Verify permissions             │
│ - Route to tool                  │
│ - Execute tool                   │
│ - Cache result                   │
│ - Return response                │
└─────┬──────────┬──────────┬──────┘
      │          │          │
      ↓          ↓          ↓
┌──────────┐ ┌────────┐ ┌────────┐
│ Vector   │ │ SQL    │ │ Web    │
│ DB Tool  │ │ Tool   │ │ Search │
└──────────┘ └────────┘ └────────┘
      │          │          │
      ↓          ↓          ↓
┌──────────┐ ┌────────┐ ┌────────┐
│ Chroma   │ │Postgres│ │Bing API│
│ Vector   │ │Database│ │Search  │
└──────────┘ └────────┘ └────────┘
```

### Detailed Tool Call Sequence

```
Agent                MCP Server           Tool                External Service
  │                      │                  │                       │
  ├─ Tool Request ──────>│                  │                       │
  │  (name, params)      │                  │                       │
  │                      ├─ Check Perms ─>  │                       │
  │                      │  (allowed?)       │                       │
  │                      │                  │                       │
  │                      ├─ Check Cache ──> │                       │
  │                      │  (cached result?)  │                       │
  │                      │                  │                       │
  │                      ├─ Execute Tool ──>│                       │
  │                      │                  ├─ API Call ──────────>│
  │                      │                  │                       │
  │                      │                  │<─ API Response ───────┤
  │                      │                  │                       │
  │                      │<─ Cache Result ── │                       │
  │                      │                  │                       │
  │<─ Tool Response ─────┤                  │                       │
  │  (result, metadata)  │                  │                       │
  │                      │                  │                       │
```

---

## Tool Interface Definition

### Standard Tool Format

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal
from enum import Enum
from datetime import datetime

class ToolStatus(str, Enum):
    """Tool execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"
    TIMEOUT = "timeout"
    UNAUTHORIZED = "unauthorized"

@dataclass
class ToolParameter:
    """Definition of a single tool parameter."""
    name: str
    type: str  # "string", "integer", "float", "boolean", "list", "dict"
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[str]] = None  # Valid values if constrained
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None

@dataclass
class ToolDefinition:
    """Complete definition of a tool."""
    name: str
    version: str  # e.g., "1.0.0"
    description: str
    category: str  # "search", "database", "api", "file_system", "computation"

    # Tool interface
    parameters: List[ToolParameter]
    returns: Dict[str, str]  # {field_name: type_description}

    # Tool metadata
    provider: str  # "bing", "openai", "anthropic", "internal", etc.
    requires_auth: bool
    rate_limit: Optional[Dict[str, int]]  # {calls_per_minute: 60}
    timeout: int  # seconds

    # Status
    enabled: bool = True
    deprecated: bool = False
    replacement: Optional[str] = None

@dataclass
class ToolRequest:
    """Request to execute a tool."""
    tool_name: str
    tool_version: str = "latest"
    parameters: Dict[str, Any]

    # Metadata
    request_id: str
    agent_name: str  # Which agent is requesting
    timestamp: datetime = field(default_factory=datetime.now)
    timeout: int = 30  # seconds

@dataclass
class ToolResult:
    """Result of tool execution."""
    status: ToolStatus
    tool_name: str
    result: Optional[Dict[str, Any]]
    error: Optional[str] = None

    # Execution metadata
    execution_time: float = 0.0  # seconds
    cached: bool = False
    cache_hit: Optional[str] = None  # Cache key if hit

    # For debugging
    request_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
```

### Tool Registration Format

```python
# tools/vector_db_tool.py
from mcp.tool_interface import ToolDefinition, ToolParameter

VECTOR_DB_TOOL = ToolDefinition(
    name="vector_db",
    version="1.0.0",
    description="Search documents using semantic vector similarity",
    category="search",

    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Search query text",
            required=True,
            min_length=1,
            max_length=1000
        ),
        ToolParameter(
            name="top_k",
            type="integer",
            description="Number of results to return",
            required=False,
            default=10,
            min_value=1,
            max_value=100
        ),
        ToolParameter(
            name="threshold",
            type="float",
            description="Minimum similarity threshold (0.0-1.0)",
            required=False,
            default=0.5,
            min_value=0.0,
            max_value=1.0
        ),
        ToolParameter(
            name="filter_metadata",
            type="dict",
            description="Optional metadata filters",
            required=False,
            default=None
        )
    ],

    returns={
        "results": "List of documents with scores",
        "total_count": "Total matches found",
        "query_time": "Query execution time in seconds"
    },

    provider="internal",
    requires_auth=False,
    rate_limit={"calls_per_minute": 1000},
    timeout=30,
    enabled=True
)
```

---

## Tool Catalog (7 Tools)

### Tool 1: VECTOR_DB_TOOL

**Purpose**: Semantic search using vector embeddings
**Provider**: Internal (Chroma/Weaviate)
**Used By**: RetrieverAgent, GeneratorAgent

```yaml
Tool: vector_db
Version: 1.0.0
Description: Semantic search on indexed documents
Provider: Internal

Parameters:
  - query (string, required): Search query
  - top_k (integer, default=10): Results to return
  - threshold (float, default=0.5): Min similarity
  - filter_metadata (dict, optional): Filters

Returns:
  - results: List[{doc_id, content, score, metadata}]
  - total_count: int
  - query_time: float

Rate Limit: 1000 calls/minute
Timeout: 30 seconds
Cache: YES (key = query + top_k + threshold)
```

**Example Request**:
```json
{
  "tool_name": "vector_db",
  "parameters": {
    "query": "electric pump specifications",
    "top_k": 10,
    "threshold": 0.5
  }
}
```

---

### Tool 2: SQL_DATABASE_TOOL

**Purpose**: Query structured data from SQL databases
**Provider**: Internal (PostgreSQL)
**Used By**: RetrieverAgent, GeneratorAgent

```yaml
Tool: sql_database
Version: 1.0.0
Description: Execute SQL queries on structured data
Provider: Internal

Parameters:
  - query (string, required): SQL SELECT query
  - limit (integer, default=100): Max rows
  - timeout (integer, default=30): Query timeout

Returns:
  - rows: List[Dict]
  - column_names: List[str]
  - row_count: int
  - execution_time: float

Rate Limit: 100 calls/minute
Timeout: 30 seconds
Cache: NO (data changes frequently)

Restrictions:
  - Only SELECT queries allowed
  - No INSERT/UPDATE/DELETE
  - Tables accessible: products, specifications, documentation
```

**Example Request**:
```json
{
  "tool_name": "sql_database",
  "parameters": {
    "query": "SELECT * FROM products WHERE type='pump' LIMIT 10",
    "limit": 100
  }
}
```

---

### Tool 3: KNOWLEDGE_GRAPH_TOOL

**Purpose**: Query semantic relationships using knowledge graphs
**Provider**: Neo4j
**Used By**: RetrieverAgent, VisualizationAgent

```yaml
Tool: knowledge_graph
Version: 1.0.0
Description: Query relationships in knowledge graph
Provider: Neo4j

Parameters:
  - query (string, required): Cypher query
  - return_format (string, default="json"): Format

Returns:
  - nodes: List[Dict]
  - relationships: List[Dict]
  - query_result: Dict
  - execution_time: float

Rate Limit: 500 calls/minute
Timeout: 30 seconds
Cache: YES (key = query)

Example Queries:
  - MATCH (n:Pump)-[:HAS_SPEC]->(s:Specification) RETURN n, s
  - MATCH p=(n1)-[:RELATES_TO*1..3]-(n2) WHERE n1.name='Pump' RETURN p
```

**Example Request**:
```json
{
  "tool_name": "knowledge_graph",
  "parameters": {
    "query": "MATCH (n:Pump)-[:HAS_TYPE]->(t:Type) RETURN n.name, t.name LIMIT 10",
    "return_format": "json"
  }
}
```

---

### Tool 4: WEB_SEARCH_TOOL

**Purpose**: Search the internet for real-time information
**Provider**: Bing Search API
**Used By**: RetrieverAgent, GeneratorAgent

```yaml
Tool: web_search
Version: 1.0.0
Description: Search the web for real-time information
Provider: Bing API

Parameters:
  - query (string, required): Search query
  - top_k (integer, default=10): Results to return
  - language (string, default="en"): Language
  - search_type (string, default="web"): Type

Returns:
  - results: List[{title, url, snippet, date}]
  - total_results: int
  - search_time: float

Rate Limit: 50 calls/minute
Timeout: 15 seconds
Cache: YES (key = query + language, TTL=24h)

Requires Auth: YES (API key)
```

**Example Request**:
```json
{
  "tool_name": "web_search",
  "parameters": {
    "query": "latest pump technology 2025",
    "top_k": 10,
    "language": "en"
  }
}
```

---

### Tool 5: FILE_SYSTEM_TOOL

**Purpose**: Read/write files in permitted directories
**Provider**: Internal
**Used By**: RetrieverAgent, VisualizationAgent

```yaml
Tool: file_system
Version: 1.0.0
Description: File system operations
Provider: Internal

Parameters:
  - operation (string, required): read, write, list, delete
  - path (string, required): File path
  - content (string, optional): Content to write (for write operation)

Returns:
  - success: bool
  - content (read): string
  - files (list): List[str] (for list operation)
  - message: string

Rate Limit: 200 calls/minute
Timeout: 10 seconds
Cache: YES for read (TTL=1h)

Permissions:
  - Readable: /documents, /exports, /cache
  - Writable: /cache, /exports
  - NOT writable: /system, /config
```

**Example Request**:
```json
{
  "tool_name": "file_system",
  "parameters": {
    "operation": "read",
    "path": "/documents/pump_manual.pdf"
  }
}
```

---

### Tool 6: API_CALL_TOOL

**Purpose**: Call external APIs (weather, finance, etc.)
**Provider**: Various (Anthropic OpenWeather, Yahoo Finance, etc.)
**Used By**: RetrieverAgent, GeneratorAgent

```yaml
Tool: api_call
Version: 1.0.0
Description: Call external APIs
Provider: Multiple

Parameters:
  - api_name (string, required): API identifier
  - endpoint (string, required): API endpoint
  - method (string, default="GET"): HTTP method
  - parameters (dict, optional): Query/body parameters
  - headers (dict, optional): Custom headers

Returns:
  - status_code: int
  - response: Dict
  - response_time: float

Rate Limit: 100 calls/minute
Timeout: 15 seconds
Cache: Depends on API (GET cached, POST not)

Supported APIs:
  - openweather: Weather data
  - yahoo_finance: Stock data
  - newsapi: News articles
  - (more can be registered)
```

**Example Request**:
```json
{
  "tool_name": "api_call",
  "parameters": {
    "api_name": "openweather",
    "endpoint": "/current",
    "parameters": {
      "city": "New York",
      "units": "metric"
    }
  }
}
```

---

### Tool 7: CODE_EXECUTION_TOOL

**Purpose**: Execute code for dynamic analysis
**Provider**: Sandboxed environment (Docker)
**Used By**: GeneratorAgent (for dynamic calculations)

```yaml
Tool: code_execution
Version: 1.0.0
Description: Execute Python code in sandbox
Provider: Docker sandbox

Parameters:
  - code (string, required): Python code to execute
  - timeout (integer, default=10): Max execution time
  - libraries (list, optional): Required libraries

Returns:
  - output: string
  - error: Optional[string]
  - execution_time: float
  - memory_used: float

Rate Limit: 50 calls/minute
Timeout: 10 seconds
Cache: NO

Sandboxing:
  - No access to file system (except /tmp)
  - No network access
  - No shell commands
  - Memory limit: 512MB
  - CPU limit: 1 core
  - Allowed libraries: numpy, pandas, scipy, etc.
```

**Example Request**:
```json
{
  "tool_name": "code_execution",
  "parameters": {
    "code": "import math; print(math.sqrt(100))",
    "timeout": 5,
    "libraries": ["math"]
  }
}
```

---

## Permission System

### Permission Matrix

```python
from typing import Dict, List, Set
from enum import Enum

class PermissionLevel(str, Enum):
    """Permission levels for tool access."""
    ADMIN = "admin"          # Full access
    WRITE = "write"          # Read + write
    READ = "read"            # Read-only
    NONE = "none"            # No access
    AUDIT = "audit"          # Read-only, logged

PERMISSION_MATRIX = {
    # Agent -> Tool -> Permission
    "intent_agent": {
        "vector_db": "read",
        "sql_database": "read",
        "knowledge_graph": "read",
        "web_search": "none",      # Intent doesn't need web
        "file_system": "none",
        "api_call": "none",
        "code_execution": "none"
    },

    "retriever_agent": {
        "vector_db": "read",
        "sql_database": "read",
        "knowledge_graph": "read",
        "web_search": "read",       # Can search web for latest info
        "file_system": "read",
        "api_call": "read",
        "code_execution": "none"
    },

    "generator_agent": {
        "vector_db": "read",
        "sql_database": "read",
        "knowledge_graph": "read",
        "web_search": "read",
        "file_system": "read",
        "api_call": "read",
        "code_execution": "read"    # Can execute code for calculations
    },

    "citation_agent": {
        "vector_db": "none",
        "sql_database": "none",
        "knowledge_graph": "none",
        "web_search": "none",
        "file_system": "read",      # Can read exported files
        "api_call": "none",
        "code_execution": "none"
    },

    "visualization_agent": {
        "vector_db": "read",
        "sql_database": "none",
        "knowledge_graph": "read",  # For graph visualization
        "web_search": "none",
        "file_system": "write",     # Can export visualizations
        "api_call": "none",
        "code_execution": "none"
    }
}
```

### Permission Check Flow

```python
@dataclass
class PermissionCheck:
    """Result of permission validation."""
    allowed: bool
    reason: str
    agent_name: str
    tool_name: str
    permission_level: Optional[str]
    timestamp: datetime

def check_tool_permission(
    agent_name: str,
    tool_name: str,
    operation: str = "read"
) -> PermissionCheck:
    """
    Check if agent can use tool.

    Args:
        agent_name: Name of requesting agent
        tool_name: Name of tool being requested
        operation: "read" or "write"

    Returns:
        PermissionCheck with allowed/denied and reason
    """
    # Get permission level from matrix
    permission = PERMISSION_MATRIX.get(agent_name, {}).get(tool_name, "none")

    # Check if operation is allowed
    if operation == "read" and permission in ["read", "write", "admin"]:
        return PermissionCheck(
            allowed=True,
            reason=f"Agent '{agent_name}' has '{permission}' access to '{tool_name}'",
            agent_name=agent_name,
            tool_name=tool_name,
            permission_level=permission,
            timestamp=datetime.now()
        )

    elif operation == "write" and permission in ["write", "admin"]:
        return PermissionCheck(
            allowed=True,
            reason=f"Agent '{agent_name}' has '{permission}' access to '{tool_name}'",
            agent_name=agent_name,
            tool_name=tool_name,
            permission_level=permission,
            timestamp=datetime.now()
        )

    else:
        return PermissionCheck(
            allowed=False,
            reason=f"Agent '{agent_name}' does not have '{operation}' permission for '{tool_name}'",
            agent_name=agent_name,
            tool_name=tool_name,
            permission_level=permission,
            timestamp=datetime.now()
        )
```

### Audit Logging

```python
@dataclass
class ToolAuditLog:
    """Record of tool usage for audit trail."""
    request_id: str
    agent_name: str
    tool_name: str
    operation: str  # "read", "write", "execute"
    parameters: Dict[str, Any]  # Sanitized (no secrets)
    status: ToolStatus
    permission_check: PermissionCheck
    execution_time: float
    result_summary: str  # Brief summary, not full result
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None

# Log to database/file for audit trail
def log_tool_usage(audit_log: ToolAuditLog):
    """Log tool usage for security/compliance."""
    # Store in audit_logs table
    # Can be queried for: "Which agents called web_search?", "Which tools failed?"
    pass
```

---

## Tool Call Flow

### Step-by-Step Execution

```
1. AGENT REQUESTS TOOL
   ├─ Agent calls: mcp_client.call_tool("vector_db", {"query": "...", "top_k": 10})
   └─ Request object created with metadata

2. MCP CLIENT PREPARATION
   ├─ Validate parameters against ToolDefinition
   ├─ Generate unique request_id
   ├─ Add agent_name, timestamp
   └─ Create ToolRequest object

3. PERMISSION CHECK
   ├─ Check PERMISSION_MATRIX[agent_name][tool_name]
   ├─ If denied: Return error immediately
   ├─ If allowed: Continue to next step
   └─ Log permission check (audit trail)

4. CACHE LOOKUP
   ├─ Generate cache key: hash(tool_name + parameters)
   ├─ If cache HIT and valid (not expired):
   │  └─ Return cached result (mark as cached=True)
   └─ If cache MISS:
      └─ Continue to execution

5. ROUTE TO TOOL
   ├─ Send ToolRequest to MCP Server
   ├─ Server receives request
   └─ Server routes to appropriate tool handler

6. EXECUTE TOOL
   ├─ Tool handler receives request
   ├─ Execute tool logic (API call, DB query, etc.)
   ├─ Measure execution time
   └─ Get result

7. CACHE RESULT
   ├─ If tool cacheable (vector_db, knowledge_graph, web_search)
   ├─ Store result with TTL (time-to-live)
   └─ Cache key = tool_name + parameters_hash

8. RETURN TO AGENT
   ├─ Format ToolResult object
   ├─ Include: status, result, execution_time, cached flag
   └─ Return to agent

9. AGENT PROCESSES RESULT
   ├─ If status == SUCCESS: Use result in state
   ├─ If status == FAILED: Handle error/fallback
   └─ Update shared state with result

10. AUDIT LOGGING
    ├─ Create ToolAuditLog entry
    ├─ Store in database
    └─ Make available for monitoring
```

### Code Example: Tool Call from Agent

```python
# Inside RetrieverAgent node
async def retriever_agent(state: SharedState) -> dict:
    """Retriever agent with MCP tool access."""

    mcp_client = MCPClient()  # MCP client

    # Strategy 1: Vector search (Kotaemo component)
    vector_results = await mcp_client.call_tool(
        tool_name="vector_db",
        parameters={
            "query": state.optimized_question,
            "top_k": 10,
            "threshold": 0.5
        },
        agent_name="retriever_agent"
    )

    if vector_results.status != ToolStatus.SUCCESS:
        # Tool failed, log and continue
        state.add_error("retriever", f"Vector search failed: {vector_results.error}")
    else:
        state.documents.extend(vector_results.result["results"])

    # Strategy 2: Web search (MCP tool)
    if state.question_type == "factual":
        web_results = await mcp_client.call_tool(
            tool_name="web_search",
            parameters={
                "query": state.optimized_question,
                "top_k": 5
            },
            agent_name="retriever_agent"
        )

        if web_results.status == ToolStatus.SUCCESS:
            # Convert web results to Document format
            web_docs = format_web_results(web_results.result)
            state.documents.extend(web_docs)

    # Strategy 3: SQL database (MCP tool)
    if state.question_type == "procedural":
        sql_results = await mcp_client.call_tool(
            tool_name="sql_database",
            parameters={
                "query": "SELECT * FROM procedures WHERE topic LIKE ?",
                "limit": 10
            },
            agent_name="retriever_agent"
        )

        if sql_results.status == ToolStatus.SUCCESS:
            sql_docs = format_sql_results(sql_results.result)
            state.documents.extend(sql_docs)

    # Calculate average confidence
    state.retrieval_confidence = calculate_confidence(state.documents)
    state.retrieval_method = "hybrid_with_mcp_tools"

    return {
        "documents": state.documents,
        "retrieval_confidence": state.retrieval_confidence,
        "retrieval_method": state.retrieval_method
    }
```

---

## MCP Server Architecture

### Server Components

```
┌─────────────────────────────────────────┐
│ MCP Server                              │
├─────────────────────────────────────────┤
│                                         │
│ ┌──────────────────────────────────┐   │
│ │ HTTP/gRPC Listener               │   │
│ │ (receives requests on port 8000) │   │
│ └────────────┬─────────────────────┘   │
│              │                         │
│ ┌────────────▼─────────────────────┐   │
│ │ Request Handler                  │   │
│ │ ├─ Parse request                 │   │
│ │ ├─ Validate schema               │   │
│ │ └─ Check authentication          │   │
│ └────────────┬─────────────────────┘   │
│              │                         │
│ ┌────────────▼─────────────────────┐   │
│ │ Permission Manager               │   │
│ │ ├─ Check PERMISSION_MATRIX       │   │
│ │ ├─ Log permission checks         │   │
│ │ └─ Deny if unauthorized          │   │
│ └────────────┬─────────────────────┘   │
│              │                         │
│ ┌────────────▼─────────────────────┐   │
│ │ Cache Manager                    │   │
│ │ ├─ Generate cache key            │   │
│ │ ├─ Check Redis cache             │   │
│ │ └─ Return if hit                 │   │
│ └────────────┬─────────────────────┘   │
│              │                         │
│ ┌────────────▼─────────────────────┐   │
│ │ Tool Router                      │   │
│ │ ├─ Find tool handler             │   │
│ │ ├─ Call tool async               │   │
│ │ └─ Measure execution time        │   │
│ └────────────┬─────────────────────┘   │
│              │                         │
│ ┌────────────▼─────────────────────┐   │
│ │ Tool Handlers                    │   │
│ │ ├─ VectorDBHandler               │   │
│ │ ├─ SQLDatabaseHandler            │   │
│ │ ├─ KnowledgeGraphHandler         │   │
│ │ ├─ WebSearchHandler              │   │
│ │ ├─ FileSystemHandler             │   │
│ │ ├─ APICallHandler                │   │
│ │ └─ CodeExecutionHandler          │   │
│ └────────────┬─────────────────────┘   │
│              │                         │
│ ┌────────────▼─────────────────────┐   │
│ │ Response Formatter               │   │
│ │ ├─ Format result                 │   │
│ │ ├─ Add metadata                  │   │
│ │ └─ Cache if needed               │   │
│ └────────────┬─────────────────────┘   │
│              │                         │
│ ┌────────────▼─────────────────────┐   │
│ │ Audit Logger                     │   │
│ │ ├─ Create audit log              │   │
│ │ ├─ Store in database             │   │
│ │ └─ Send to monitoring            │   │
│ └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

### Server Startup Sequence

```python
class MCPServer:
    """MCP Server - orchestrates tool execution."""

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.handlers: Dict[str, ToolHandler] = {}
        self.cache = RedisCache()
        self.db = Database()
        self.logger = Logger()

    async def startup(self):
        """Initialize MCP server."""
        # 1. Register all tools
        self.register_tool(VectorDBTool)
        self.register_tool(SQLDatabaseTool)
        self.register_tool(KnowledgeGraphTool)
        self.register_tool(WebSearchTool)
        self.register_tool(FileSystemTool)
        self.register_tool(APICallTool)
        self.register_tool(CodeExecutionTool)

        # 2. Initialize handlers
        self.handlers["vector_db"] = VectorDBHandler()
        self.handlers["sql_database"] = SQLDatabaseHandler()
        self.handlers["knowledge_graph"] = KnowledgeGraphHandler()
        self.handlers["web_search"] = WebSearchHandler()
        self.handlers["file_system"] = FileSystemHandler()
        self.handlers["api_call"] = APICallHandler()
        self.handlers["code_execution"] = CodeExecutionHandler()

        # 3. Start HTTP server on port 8000
        self.app = FastAPI()
        self.app.post("/tools/call")(self.handle_tool_call)
        self.app.get("/tools/list")(self.list_tools)
        self.app.get("/tools/{tool_name}")(self.get_tool_definition)

        # 4. Start async server
        await self.start_http_server()

    def register_tool(self, tool_class):
        """Register a tool."""
        tool = tool_class()
        self.tools[tool.definition.name] = tool.definition
        self.handlers[tool.definition.name] = tool.handler

    async def handle_tool_call(self, request: ToolRequest) -> ToolResult:
        """Handle incoming tool call request."""
        try:
            # 1. Validate request
            if request.tool_name not in self.tools:
                return ToolResult(
                    status=ToolStatus.FAILED,
                    tool_name=request.tool_name,
                    result=None,
                    error=f"Tool '{request.tool_name}' not found"
                )

            # 2. Check permissions
            perm_check = check_tool_permission(
                request.agent_name,
                request.tool_name
            )

            if not perm_check.allowed:
                return ToolResult(
                    status=ToolStatus.UNAUTHORIZED,
                    tool_name=request.tool_name,
                    result=None,
                    error=perm_check.reason
                )

            # 3. Check cache
            cache_key = self._generate_cache_key(request)
            cached_result = await self.cache.get(cache_key)

            if cached_result:
                return ToolResult(
                    status=ToolStatus.CACHED,
                    tool_name=request.tool_name,
                    result=cached_result,
                    cached=True,
                    cache_hit=cache_key
                )

            # 4. Execute tool
            handler = self.handlers[request.tool_name]
            start_time = time.time()

            result = await handler.execute(request.parameters)

            execution_time = time.time() - start_time

            # 5. Cache result if applicable
            if self.tools[request.tool_name].category in ["search", "database"]:
                ttl = 3600  # 1 hour cache
                await self.cache.set(cache_key, result, ttl=ttl)

            # 6. Create response
            tool_result = ToolResult(
                status=ToolStatus.SUCCESS,
                tool_name=request.tool_name,
                result=result,
                execution_time=execution_time,
                request_id=request.request_id
            )

            # 7. Log audit trail
            await self._log_audit(request, tool_result, perm_check)

            return tool_result

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=request.tool_name,
                result=None,
                error=str(e)
            )

    def _generate_cache_key(self, request: ToolRequest) -> str:
        """Generate cache key for tool request."""
        import hashlib
        import json

        key_data = {
            "tool": request.tool_name,
            "params": request.parameters
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"tool:{request.tool_name}:{key_hash}"

    async def _log_audit(
        self,
        request: ToolRequest,
        result: ToolResult,
        perm_check: PermissionCheck
    ):
        """Log tool usage for audit trail."""
        audit_log = ToolAuditLog(
            request_id=request.request_id,
            agent_name=request.agent_name,
            tool_name=request.tool_name,
            operation="execute",
            parameters={k: v for k, v in request.parameters.items()
                       if k != "api_key"},  # Exclude secrets
            status=result.status,
            permission_check=perm_check,
            execution_time=result.execution_time,
            result_summary=self._summarize_result(result),
            timestamp=datetime.now()
        )

        await self.db.store_audit_log(audit_log)
```

---

## Configuration

### MCP Server Configuration YAML

```yaml
# config/mcp_server.yaml

# Server settings
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  debug: false

# Tool configurations
tools:
  vector_db:
    enabled: true
    version: "1.0.0"
    timeout: 30
    cache:
      enabled: true
      ttl: 3600  # 1 hour
    rate_limit:
      calls_per_minute: 1000

  sql_database:
    enabled: true
    version: "1.0.0"
    timeout: 30
    cache:
      enabled: false  # Data changes frequently
    rate_limit:
      calls_per_minute: 100
    connection_pool:
      min_size: 5
      max_size: 20

  knowledge_graph:
    enabled: true
    version: "1.0.0"
    timeout: 30
    cache:
      enabled: true
      ttl: 7200  # 2 hours
    rate_limit:
      calls_per_minute: 500

  web_search:
    enabled: true
    version: "1.0.0"
    timeout: 15
    cache:
      enabled: true
      ttl: 86400  # 24 hours
    rate_limit:
      calls_per_minute: 50
    provider: "bing"
    requires_auth: true
    auth_key_env: "BING_SEARCH_API_KEY"

  file_system:
    enabled: true
    version: "1.0.0"
    timeout: 10
    cache:
      enabled: true
      ttl: 3600
    rate_limit:
      calls_per_minute: 200
    permissions:
      readable_dirs:
        - /documents
        - /exports
        - /cache
      writable_dirs:
        - /cache
        - /exports
      forbidden_dirs:
        - /system
        - /config

  api_call:
    enabled: true
    version: "1.0.0"
    timeout: 15
    cache:
      enabled: true
      ttl: 3600
    rate_limit:
      calls_per_minute: 100
    supported_apis:
      - name: "openweather"
        base_url: "https://api.openweathermap.org"
        auth_key_env: "OPENWEATHER_API_KEY"
      - name: "yahoo_finance"
        base_url: "https://query1.finance.yahoo.com"
        auth_key_env: "YAHOO_FINANCE_API_KEY"

  code_execution:
    enabled: true
    version: "1.0.0"
    timeout: 10
    cache:
      enabled: false  # Code execution results are ephemeral
    rate_limit:
      calls_per_minute: 50
    sandbox:
      docker_image: "python:3.11-slim"
      memory_limit: "512M"
      cpu_limit: "1"
      allowed_libraries:
        - numpy
        - pandas
        - scipy
        - matplotlib
        - json
        - math
        - datetime

# Cache settings
cache:
  backend: "redis"
  redis_url: "${REDIS_URL:-redis://localhost:6379}"
  default_ttl: 3600
  max_size: "1GB"

# Database settings
database:
  url: "${DATABASE_URL}"
  pool_size: 10
  max_overflow: 20
  echo: false  # Set to true for SQL debugging

# Logging
logging:
  level: "INFO"
  format: "json"
  output:
    - "stdout"
    - "file"
  file_path: "/var/log/mcp_server.log"

# Monitoring
monitoring:
  metrics_enabled: true
  metrics_port: 9090
  tracing_enabled: true
  jaeger_url: "http://localhost:6831"

# Security
security:
  enable_cors: true
  cors_origins:
    - "http://localhost:3000"
    - "http://localhost:8080"
  require_api_key: false  # Agents authenticate via A2A
  rate_limit_global: 10000  # Global calls per minute
```

---

## Error Handling

### Tool Execution Errors

#### 1. **Tool Not Found**

```python
# Error scenario
request.tool_name = "nonexistent_tool"

# Server response
ToolResult(
    status=ToolStatus.FAILED,
    tool_name="nonexistent_tool",
    result=None,
    error="Tool 'nonexistent_tool' not found"
)

# Agent handling
if result.status == ToolStatus.FAILED:
    state.add_error(
        node="retriever",
        error_msg=result.error,
        error_type="tool_not_found"
    )
    # Try alternative tool or Kotaemo component
```

---

#### 2. **Permission Denied**

```python
# Error scenario
agent_name = "citation_agent"
tool_name = "web_search"  # Not in citation_agent's permissions

# Server response
ToolResult(
    status=ToolStatus.UNAUTHORIZED,
    tool_name="web_search",
    result=None,
    error="Agent 'citation_agent' does not have 'read' permission for 'web_search'"
)

# Agent handling
# This should never happen if permission matrix is correct
# If it does, log as security issue
state.add_error(
    node="citation",
    error_msg="Permission denied for tool",
    error_type="authorization_failure"
)
```

---

#### 3. **Timeout**

```python
# Error scenario
tool_name = "web_search"
timeout = 15  # seconds
# ... search takes 20 seconds ...

# Server response
ToolResult(
    status=ToolStatus.TIMEOUT,
    tool_name="web_search",
    result=None,
    error="Tool execution timeout (15s exceeded)"
)

# Agent handling
state.add_error(
    node="retriever",
    error_msg="Web search timed out",
    error_type="timeout"
)

# Fallback to cached results or alternative method
if not state.fallback_attempted:
    # Try simpler retrieval strategy
    state.retrieval_method = "fallback_vector_only"
```

---

#### 4. **Rate Limit Exceeded**

```python
# Error scenario
tool_name = "web_search"
rate_limit = 50  # calls per minute
# ... agent makes 51st call ...

# Server response
ToolResult(
    status=ToolStatus.FAILED,
    tool_name="web_search",
    result=None,
    error="Rate limit exceeded for 'web_search' (50 calls/minute)"
)

# Agent handling
state.add_error(
    node="retriever",
    error_msg="Tool rate limit exceeded",
    error_type="rate_limit"
)

# Retry with exponential backoff
await asyncio.sleep(2 ** retry_count)  # 2s, 4s, 8s, ...
```

---

#### 5. **Invalid Parameters**

```python
# Error scenario
parameters = {
    "query": "pump",
    "top_k": 500  # Max is 100
}

# Validation fails in tool handler

# Server response
ToolResult(
    status=ToolStatus.FAILED,
    tool_name="vector_db",
    result=None,
    error="Invalid parameter: top_k must be <= 100, got 500"
)

# Agent handling
state.add_error(
    node="retriever",
    error_msg="Invalid tool parameters",
    error_type="invalid_parameters"
)

# Retry with corrected parameters
parameters["top_k"] = 100
result = await mcp_client.call_tool(tool_name, parameters)
```

---

## Implementation Notes

### Design Decisions

1. **MCP Server as Central Hub**
   - ✅ Single point for permission checking
   - ✅ Centralized caching
   - ✅ Audit logging in one place
   - ⚠️ Single point of failure (mitigate with clustering/redundancy)

2. **Async Tool Execution**
   - ✅ Non-blocking calls
   - ✅ Can parallelize multiple tool calls
   - ⚠️ More complex error handling
   - ℹ️ Use asyncio for Python

3. **Permission Matrix vs Dynamic Roles**
   - ✅ Matrix: Simple, explicit, easy to audit
   - ❌ Roles: More flexible but harder to debug
   - Decision: Use matrix, add role support in Phase 4

4. **Tool Caching Strategy**
   - ✅ Cache search results (vector_db, web_search, knowledge_graph)
   - ❌ Don't cache SQL queries (data changes)
   - ❌ Don't cache code execution (ephemeral)
   - ℹ️ Configurable per-tool TTL

5. **Tool Versioning**
   - ✅ Support multiple versions: vector_db@1.0, vector_db@2.0
   - ✅ Agents can specify version: "latest" or "1.0"
   - ⚠️ Need migration strategy for breaking changes

6. **Sandboxing Code Execution**
   - ✅ Docker container for isolation
   - ✅ No file system access (except /tmp)
   - ✅ No network access
   - ✅ Memory/CPU limits
   - ℹ️ Use Docker or similar containerization

---

### Key Implementation Decisions

1. **When to Call MCP Tools vs Kotaemo Components?**
   - Vector search: Use both (MCP tool + Kotaemo backup)
   - Web search: MCP only (external data)
   - SQL queries: MCP only (structured data)
   - LLM calls: Kotaemo (no MCP needed)

2. **Tool Response Format**
   - Always return ToolResult dataclass
   - Include metadata (execution_time, cached flag, etc.)
   - Agent can inspect these fields for debugging

3. **Error Propagation**
   - Tool errors don't throw (status=FAILED)
   - Agent checks status and decides next action
   - Errors logged to state.errors for tracking

4. **Caching Strategy**
   - Cache key = hash(tool_name + parameters)
   - TTL configurable per tool
   - Invalidation: Manual + time-based expiry

5. **Audit Trail**
   - All tool calls logged (agent, tool, params, result)
   - Exclude secrets (api_keys, passwords)
   - Queryable for compliance/debugging

---

## Testing Strategy

### Unit Tests (per-tool testing)

```python
# test_mcp_tools.py

def test_vector_db_tool_success():
    """Test successful vector search."""
    tool = VectorDBTool()
    result = tool.execute({
        "query": "pump specifications",
        "top_k": 10
    })

    assert result["results"] is not None
    assert len(result["results"]) <= 10

def test_vector_db_tool_invalid_topk():
    """Test parameter validation."""
    tool = VectorDBTool()

    with pytest.raises(ValueError):
        tool.execute({"query": "pump", "top_k": 500})

def test_web_search_tool_timeout():
    """Test timeout handling."""
    tool = WebSearchTool(timeout=1)

    with patch('requests.get') as mock:
        mock.side_effect = Timeout()

        with pytest.raises(Timeout):
            tool.execute({"query": "pump"})

def test_code_execution_tool_security():
    """Test sandbox prevents dangerous operations."""
    tool = CodeExecutionTool()

    # Try to read system file
    with pytest.raises(PermissionError):
        tool.execute({"code": "open('/etc/passwd')"})
```

---

### Integration Tests (MCP server)

```python
# test_mcp_server.py

@pytest.mark.asyncio
async def test_permission_check_allowed():
    """Test permission check allows authorized access."""
    server = MCPServer()

    request = ToolRequest(
        tool_name="vector_db",
        parameters={"query": "test"},
        agent_name="retriever_agent",
        request_id="req-1"
    )

    result = await server.handle_tool_call(request)
    assert result.status == ToolStatus.SUCCESS

@pytest.mark.asyncio
async def test_permission_check_denied():
    """Test permission check denies unauthorized access."""
    server = MCPServer()

    request = ToolRequest(
        tool_name="web_search",
        parameters={"query": "test"},
        agent_name="citation_agent",  # Not allowed
        request_id="req-2"
    )

    result = await server.handle_tool_call(request)
    assert result.status == ToolStatus.UNAUTHORIZED

@pytest.mark.asyncio
async def test_cache_hit():
    """Test caching returns cached result."""
    server = MCPServer()

    request1 = ToolRequest(
        tool_name="vector_db",
        parameters={"query": "test", "top_k": 10},
        agent_name="retriever_agent",
        request_id="req-1"
    )

    # First call
    result1 = await server.handle_tool_call(request1)
    assert result1.status == ToolStatus.SUCCESS
    assert result1.cached == False

    # Second call with same parameters
    request2 = ToolRequest(
        tool_name="vector_db",
        parameters={"query": "test", "top_k": 10},
        agent_name="retriever_agent",
        request_id="req-2"
    )

    result2 = await server.handle_tool_call(request2)
    assert result2.status == ToolStatus.CACHED
    assert result2.result == result1.result

@pytest.mark.asyncio
async def test_tool_not_found():
    """Test error when tool doesn't exist."""
    server = MCPServer()

    request = ToolRequest(
        tool_name="nonexistent_tool",
        parameters={},
        agent_name="retriever_agent",
        request_id="req-1"
    )

    result = await server.handle_tool_call(request)
    assert result.status == ToolStatus.FAILED
    assert "not found" in result.error
```

---

### Performance Tests

```python
# test_mcp_performance.py

def test_tool_execution_latency():
    """Test that tools complete within SLA."""
    tool = VectorDBTool()

    start = time.time()
    result = tool.execute({"query": "pump", "top_k": 10})
    elapsed = time.time() - start

    # Vector DB should complete in <500ms
    assert elapsed < 0.5, f"Expected <500ms, got {elapsed*1000}ms"

def test_cache_hit_latency():
    """Test that cache hits are fast."""
    tool = VectorDBTool()

    # Warm up cache
    tool.execute({"query": "pump", "top_k": 10})

    # Measure cached hit
    start = time.time()
    result = tool.execute({"query": "pump", "top_k": 10})
    elapsed = time.time() - start

    # Cached hit should be <10ms
    assert elapsed < 0.01, f"Expected <10ms, got {elapsed*1000}ms"

def test_concurrent_tool_calls():
    """Test parallel tool execution."""
    server = MCPServer()

    async def call_tool():
        request = ToolRequest(
            tool_name="vector_db",
            parameters={"query": f"pump {i}"},
            agent_name="retriever_agent",
            request_id=f"req-{i}"
        )
        return await server.handle_tool_call(request)

    # Make 100 concurrent calls
    loop = asyncio.get_event_loop()
    tasks = [call_tool() for _ in range(100)]

    start = time.time()
    results = loop.run_until_complete(asyncio.gather(*tasks))
    elapsed = time.time() - start

    # Should complete in reasonable time (not 100x single call)
    assert all(r.status == ToolStatus.SUCCESS for r in results)
    assert elapsed < 10  # Should complete in <10 seconds
```

---

### Chaos Tests (failure scenarios)

```python
# test_mcp_chaos.py

@pytest.mark.asyncio
async def test_tool_timeout_recovery():
    """Test that timeout is handled gracefully."""
    server = MCPServer()

    with patch.object(WebSearchTool, 'execute', side_effect=asyncio.TimeoutError):
        request = ToolRequest(
            tool_name="web_search",
            parameters={"query": "test"},
            agent_name="retriever_agent",
            request_id="req-1"
        )

        result = await server.handle_tool_call(request)
        assert result.status == ToolStatus.TIMEOUT

@pytest.mark.asyncio
async def test_tool_error_recovery():
    """Test that tool errors don't crash server."""
    server = MCPServer()

    with patch.object(VectorDBTool, 'execute', side_effect=Exception("DB Error")):
        request = ToolRequest(
            tool_name="vector_db",
            parameters={"query": "test"},
            agent_name="retriever_agent",
            request_id="req-1"
        )

        result = await server.handle_tool_call(request)
        assert result.status == ToolStatus.FAILED
        assert "DB Error" in result.error

@pytest.mark.asyncio
async def test_rate_limit_enforcement():
    """Test that rate limits are enforced."""
    server = MCPServer()
    tool_def = server.tools["web_search"]
    tool_def.rate_limit = {"calls_per_minute": 10}

    # Make 11 calls rapidly
    results = []
    for i in range(11):
        request = ToolRequest(
            tool_name="web_search",
            parameters={"query": f"test{i}"},
            agent_name="retriever_agent",
            request_id=f"req-{i}"
        )
        result = await server.handle_tool_call(request)
        results.append(result)

    # Last request should fail due to rate limit
    assert results[-1].status == ToolStatus.FAILED
    assert "rate limit" in results[-1].error
```

---

## Implementation Checklist

- [ ] Define ToolDefinition, ToolParameter, ToolRequest, ToolResult dataclasses
- [ ] Create PERMISSION_MATRIX with all agent-tool mappings
- [ ] Implement permission checking logic
- [ ] Create VectorDBTool handler (wrapper around Chroma)
- [ ] Create SQLDatabaseTool handler (PostgreSQL wrapper)
- [ ] Create KnowledgeGraphTool handler (Neo4j wrapper)
- [ ] Create WebSearchTool handler (Bing API integration)
- [ ] Create FileSystemTool handler (file I/O with path restrictions)
- [ ] Create APICallTool handler (generic HTTP client)
- [ ] Create CodeExecutionTool handler (Docker sandbox)
- [ ] Implement MCPServer with request handling
- [ ] Implement permission checking in server
- [ ] Implement cache layer (Redis)
- [ ] Implement audit logging (database storage)
- [ ] Create MCPClient for agents to call tools
- [ ] Write unit tests for each tool
- [ ] Write integration tests for MCP server
- [ ] Write performance tests for latency/throughput
- [ ] Write chaos tests for failure scenarios
- [ ] Create configuration YAML file
- [ ] Document tool APIs and usage examples

---

## Summary

This design document provides:

✅ **Clear tool catalog** with 7 tools and full specifications
✅ **Permission system** with matrix and enforcement logic
✅ **MCP server architecture** with request/response flow
✅ **Tool call flow** showing 10-step execution process
✅ **Error handling** for 5 failure scenarios
✅ **Caching strategy** with TTL and invalidation
✅ **Audit logging** for compliance and debugging
✅ **Testing strategy** with unit, integration, performance, and chaos tests

**Key Insights**:
- Tools are discovered at runtime (not hard-coded)
- Permissions prevent agents from accessing unauthorized tools
- Caching improves performance for idempotent operations
- Errors don't crash the system (graceful degradation)
- All tool calls are audited for security/compliance

**Next Steps**:
1. Review this design
2. Implement MCP server and tools
3. Create Phase 4 (A2A Protocol) design
4. Implement A2A protocol for agent communication
5. Test full integration of LangGraph + MCP + A2A

---

**Last Updated**: November 17, 2025
**Status**: Ready for Implementation Review
