# Full Stack Implementation Requirements (A2A + MCP + LangGraph)

## Overview
Complete breakdown of all changes required to transform Kotaemon from a monolithic, sequential system to a distributed, agent-based architecture with MCP tool integration and LangGraph orchestration.

---

## PHASE 1: ARCHITECTURE TRANSFORMATION

### 1. Monolithic → Distributed Agent Architecture
- **Current**: Single `FullQAPipeline` with sequential steps
- **New**: 5 independent agent services:
  - Intent Agent (detects question type, complexity, urgency)
  - Retriever Agent (multi-source document retrieval)
  - Generator Agent (LLM-based answer generation)
  - Citation Agent (citation extraction & formatting)
  - Visualization Agent (mind map/knowledge graph generation)

- **Change**: Each agent becomes a separate service/container with:
  - Independent LLM configuration
  - Own state management
  - Parallel execution capability
  - Health check endpoints

---

## PHASE 2: LANGGRAPH ORCHESTRATION

### 2. New LangGraph Files
```
libs/ktem/ktem/reasoning/langgraph/
├── orchestrator.py          (Main LangGraph graph definition)
├── state.py                 (Shared state schema across agents)
├── edges.py                 (Decision functions for routing)
├── nodes.py                 (Node handlers for each agent call)
├── agents/
│   ├── intent_agent.py      (Intent detection logic)
│   ├── retriever_agent.py   (Multi-source retrieval)
│   ├── generator_agent.py   (Answer generation)
│   ├── citation_agent.py    (Citation handling)
│   └── visualization_agent.py (Mind map creation)
└── utils/
    ├── constants.py         (Graph constants, confidence thresholds)
    └── validators.py        (State validation)
```

### 3. Graph Structure Changes
- Current: 7-8 sequential nodes → **20+ nodes** with:
  - Parallel agent execution paths
  - Conditional edges (complexity, confidence, strategy routing)
  - Loop detection and prevention
  - Error recovery with fallbacks
  - Human-in-the-loop approval points

---

## PHASE 3: MCP (MODEL CONTEXT PROTOCOL) INTEGRATION

### 4. MCP Server Infrastructure
```
libs/ktem/ktem/mcp/
├── server.py               (MCP server initialization)
├── tools/
│   ├── vector_db_tool.py   (Vector store queries)
│   ├── sql_database_tool.py (SQL queries)
│   ├── knowledge_graph_tool.py (Graph queries)
│   ├── web_search_tool.py  (Web search API)
│   ├── file_system_tool.py (File operations)
│   ├── api_tool.py         (External API calls)
│   └── code_execution_tool.py (Dynamic code execution)
├── permissions/
│   ├── tool_permissions.py (Permission boundaries)
│   └── access_control.py   (Authorization logic)
└── registry/
    └── tool_registry.py    (Tool discovery & registration)
```

### 5. Tool Ecosystem Setup
- Dynamic tool discovery (agents find available tools at startup)
- Permission boundaries (which agent can use which tool)
- Tool configuration (API keys, database connections, etc.)
- Tool versioning and A/B testing support

---

## PHASE 4: A2A (AGENT-TO-AGENT) PROTOCOL

### 6. A2A Communication Layer
```
libs/ktem/ktem/a2a/
├── protocol.py             (A2A message format & handling)
├── message_broker.py       (Async message routing)
├── registry.py             (Agent discovery & registration)
├── health_check.py         (Agent health monitoring)
└── load_balancer.py        (Distribute requests to agents)
```

### 7. Agent Communication Requirements
- Service-to-service communication protocol
- Agent registration in central registry
- Message queue for async communication
- Health check endpoints (active agents only)
- Load balancing across multiple agent instances

---

## PHASE 5: CONTAINERIZATION & DEPLOYMENT

### 8. Docker & Kubernetes Setup
```
docker/
├── Dockerfile.base         (Base image for all agents)
├── Dockerfile.intent       (Intent Agent container)
├── Dockerfile.retriever    (Retriever Agent container)
├── Dockerfile.generator    (Generator Agent container)
├── Dockerfile.citation     (Citation Agent container)
└── Dockerfile.visualization (Visualization Agent container)

kubernetes/
├── intent-deployment.yaml
├── retriever-deployment.yaml (can scale to 5+ replicas)
├── generator-deployment.yaml (can scale to 8+ replicas)
├── citation-deployment.yaml
├── visualization-deployment.yaml
├── service-mesh.yaml       (Istio or similar)
├── ingress.yaml            (API Gateway)
└── monitoring.yaml         (Prometheus/Grafana)
```

### 9. Service Mesh & Load Balancing
- Service discovery (agents find each other)
- Load balancing (distribute requests)
- Circuit breakers (handle failing agents)
- Retry logic with exponential backoff

---

## PHASE 6: STATE MANAGEMENT & PERSISTENCE

### 10. Agent State Storage
```
libs/ktem/ktem/state/
├── agent_state.py          (Agent-specific state)
├── conversation_state.py   (Conversation context)
├── execution_state.py      (Workflow execution tracking)
└── persistence/
    ├── redis_backend.py    (Fast session storage)
    └── postgres_backend.py (Durable agent data)
```

### 11. State Management Changes
- Shared state accessible by all agents
- Agent-specific metadata
- Conversation history tracking
- Workflow execution state
- Error recovery state

---

## PHASE 7: CONFIGURATION MANAGEMENT

### 12. Configuration Files
```
config/
├── agents.yaml             (Agent configuration)
├── tools.yaml              (Tool registration & settings)
├── permissions.yaml        (Tool access control)
├── llm_config.yaml         (LLM settings per agent)
├── infrastructure.yaml     (K8s, service mesh settings)
└── monitoring.yaml         (Logging & observability)
```

### 13. Environment Variables
- Agent URLs and ports
- MCP server configuration
- Database connections (Redis, Postgres, etc.)
- API keys (web search, external services)
- LLM configurations per agent
- Monitoring endpoints

---

## PHASE 8: API LAYER CHANGES

### 14. New API Endpoints
```
/api/agents/                     (Agent management)
├── GET /status                  (Health check all agents)
├── GET /registry                (List available agents)
├── POST /register               (Register new agent)

/api/tools/                      (Tool management)
├── GET /available               (List available tools)
├── GET /permissions             (Tool permission matrix)
├── POST /validate-access        (Check tool access)

/api/chat/                       (Chat interface)
├── POST /query                  (New chat query)
├── GET /query/{id}/status       (Query execution status)
├── GET /query/{id}/result       (Get results)

/api/monitoring/                 (Observability)
├── GET /metrics                 (Prometheus metrics)
├── GET /traces                  (Distributed traces)
└── GET /logs                    (Structured logs)
```

---

## PHASE 9: DATABASE SCHEMA CHANGES

### 15. New Database Tables
- `agents` (agent metadata, capabilities, health status)
- `tools` (tool registry, versions, permissions)
- `tool_permissions` (access control matrix)
- `agent_state` (agent execution state)
- `conversation_state` (conversation context)
- `tool_usage_audit` (audit logging)
- `agent_metrics` (performance tracking)
- `error_tracking` (error logs across agents)

---

## PHASE 10: MONITORING & OBSERVABILITY

### 16. Distributed Tracing & Monitoring
```
libs/ktem/ktem/monitoring/
├── tracing.py              (OpenTelemetry/Jaeger setup)
├── metrics.py              (Prometheus metrics)
├── logging.py              (Structured logging)
├── health_checks.py        (Agent health endpoints)
└── dashboards/
    ├── agent_performance.py (Agent latency/throughput)
    ├── tool_usage.py       (Tool call statistics)
    ├── error_tracking.py   (Error rates & types)
    └── system_health.py    (Overall system status)
```

### 17. Metrics to Track
- Agent latency (per agent, per query)
- Tool call frequency
- Error rates (by agent, by tool)
- Agent uptime/downtime
- Resource utilization (CPU, memory)
- Queue depths
- Cache hit rates

---

## PHASE 11: EXTERNAL INTEGRATIONS

### 18. Third-Party Service Integration
- **Web Search**: Bing/Google search APIs
- **Knowledge Graph**: Neo4j integration
- **SQL Database**: Connection pooling, query optimization
- **File Storage**: S3/GCS for document storage
- **External APIs**: Weather, Finance, etc.

---

## PHASE 12: CODE REFACTORING

### 19. Files to Significantly Refactor
- `libs/ktem/ktem/reasoning/simple.py` → Split into agent-specific modules
- `libs/ktem/ktem/index/file/pipelines.py` → Integrate with retriever agent
- `app.py` → Add agent discovery and A2A communication setup
- Chat interface → Support agent status display and tool usage

### 20. Classes to Replace/Rewrite
- `FullQAPipeline` → `LangGraphOrchestrator` (coordinates agents)
- `AddQueryContextPipeline` → `IntentAgent` node
- `DecomposeQuestionPipeline` → Part of `IntentAgent`
- `RewriteQuestionPipeline` → `RetrieverAgent` optimization
- `DocumentRetrievalPipeline` → `RetrieverAgent` with MCP tools
- `AnswerWithContextPipeline` → `GeneratorAgent`
- `AnswerWithInlineCitation` → `CitationAgent`
- `CreateCitationVizPipeline` → `VisualizationAgent`

---

## PHASE 13: TESTING REQUIREMENTS

### 21. New Testing Infrastructure
```
tests/
├── unit/
│   ├── test_orchestrator.py (LangGraph logic)
│   ├── test_agents/         (Each agent's logic)
│   ├── test_mcp_tools.py    (Tool behavior)
│   └── test_a2a_protocol.py (Communication)
├── integration/
│   ├── test_agent_communication.py
│   ├── test_tool_integration.py
│   └── test_end_to_end_flow.py
├── performance/
│   ├── test_agent_latency.py
│   ├── test_scalability.py
│   └── test_concurrent_queries.py
└── chaos/
    └── test_agent_failures.py (Test fault tolerance)
```

---

## PHASE 14: DOCUMENTATION

### 22. Documentation to Create
- Architecture overview (system design)
- Agent development guide (how to add new agents)
- MCP tool development guide (how to add new tools)
- Deployment guide (K8s setup)
- Configuration reference (all settings)
- API documentation (all endpoints)
- Troubleshooting guide (common issues)
- Performance tuning guide

---

## SUMMARY OF CHANGES

| Layer | Current | Full Stack |
|-------|---------|-----------|
| **Architecture** | Monolithic, Sequential | Distributed, Parallel |
| **Agents** | 1 (FullQAPipeline) | 5 independent agents |
| **LangGraph** | None | Complete orchestrator |
| **MCP Tools** | None | 6-7 MCP tools |
| **A2A Protocol** | None | Full communication layer |
| **Containerization** | None | Docker + Kubernetes |
| **State Management** | In-memory | Redis + Postgres |
| **Monitoring** | Basic logging | Distributed tracing + metrics |
| **Code Files** | ~500 LOC reasoning | ~8000-10000 LOC across all layers |
| **Deployment** | Single process | K8s cluster with service mesh |
| **Scalability** | Fixed single instance | Independent agent scaling |

---

## IMPLEMENTATION EFFORT

- **Time**: 12-16 weeks (3-4 months)
- **Lines of Code**: ~8000-10000
- **Complexity**: Extreme
- **Breaking Changes**: Complete platform redesign
- **Team Size**: 4-5 engineers
- **Infrastructure**: Complex K8s setup, service mesh, monitoring

---

## PERFORMANCE & SCALABILITY GAINS

### Performance Improvement
- Simple questions: 11s → 2s (80% faster - skip most steps)
- Complex questions: 15s → 6s (60% faster)
- Access to real-time information (web search)
- Access to structured data (SQL queries)
- Much richer answers (combine multiple sources)

### Scalability
- Retriever Agent: Can scale to 5+ replicas (handle 5x load)
- Generator Agent: Can scale to 8+ replicas (handle 8x load)
- Independent agent scaling based on bottleneck
- Handles 10,000+ queries per day

---

## BEST FOR

- Large enterprises with enterprise budgets
- Systems requiring real-time information
- Access to multiple data sources
- 10,000+ queries per day
- Multi-region global deployment
- 24/7 uptime SLA requirements

---

**Last Updated**: November 17, 2025
