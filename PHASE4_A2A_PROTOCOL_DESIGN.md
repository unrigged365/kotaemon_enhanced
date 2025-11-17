# Phase 4: A2A (Agent-to-Agent) Protocol Design

## Executive Summary

This document defines the A2A (Agent-to-Agent) communication protocol that enables distributed agents to communicate with each other in a scalable, resilient manner. Instead of monolithic in-process agents, we have:

- **Independent agent services** (IntentAgent, RetrieverAgent, GeneratorAgent, CitationAgent, VisualizationAgent)
- **Service discovery** (agents find each other dynamically)
- **Standardized messaging** (structured request/response protocol)
- **Async communication** (message queues for non-blocking calls)
- **Health monitoring** (agents report health status)
- **Load balancing** (distribute requests across agent replicas)
- **Service mesh integration** (Istio/Linkerd for advanced networking)

**Core Concept**: Transform from in-process agent coordination → distributed service-to-service communication via A2A protocol.

**Current State**:
- Agents are in-process functions called by LangGraph orchestrator
- No scalability (single instance, single process)
- Limited fault isolation

**After A2A Integration**:
- Each agent is a separate microservice
- Can scale independently (5+ RetrieverAgent instances)
- Fault isolation (one agent down ≠ entire system down)
- Containers for each agent service
- Load balanced across multiple instances

---

## Problem Statement

### Current Limitations (Monolithic Agents)

1. **Scalability Constraints**
   - All agents in single process
   - Can't scale RetrieverAgent independently
   - Resource contention (CPU, memory)
   - Single point of failure

2. **Deployment Rigidity**
   - Deploy entire system as unit
   - Can't update one agent without downtime
   - No rolling updates
   - Version management difficult

3. **Resource Inefficiency**
   - Heavy agents (GeneratorAgent) take up memory
   - Light agents (CitationAgent) unused most of the time
   - No fine-grained resource allocation
   - CPU cores not utilized efficiently

4. **Fault Isolation Issues**
   - One crashing agent crashes entire system
   - Error propagation across agents
   - No circuit breakers
   - No graceful degradation

5. **Operational Visibility**
   - No per-agent health checks
   - Hard to debug agent-specific issues
   - No per-agent metrics
   - Distributed tracing difficult

### Desired Behavior (With A2A Protocol)

✅ **Independent Scaling** - Run 5 RetrieverAgent + 8 GeneratorAgent + 1 CitationAgent
✅ **Service Discovery** - Agents find each other at runtime
✅ **Async Communication** - Non-blocking message passing
✅ **Health Monitoring** - Know which agents are healthy
✅ **Load Balancing** - Distribute requests fairly
✅ **Fault Tolerance** - Circuit breakers, retries, timeouts
✅ **Operational Visibility** - Per-agent metrics and logs
✅ **Zero-Downtime Updates** - Rolling deployment support

---

## Design Goals

1. **Service Independence**: Each agent is a standalone service
2. **Discovery**: Dynamic agent registration and discovery
3. **Scalability**: Easy horizontal scaling (add more instances)
4. **Resilience**: Handle failures gracefully with retries/fallbacks
5. **Observability**: Per-agent health, metrics, and traces
6. **Performance**: Low-latency communication (<100ms latency)
7. **Compatibility**: Seamless integration with LangGraph orchestrator
8. **Maintainability**: Clear message contracts and interfaces

---

## Architecture Diagram

### High-Level System Architecture

```
┌──────────────────────────────────────────────────────┐
│ LangGraph Orchestrator (in API Gateway container)    │
│ - Runs graph definition                              │
│ - Calls agents via A2A protocol                      │
│ - Manages state                                      │
└──────────────┬───────────────────────────────────────┘
               │ A2A Messages
               ↓
┌──────────────────────────────────────────────────────┐
│ A2A Message Broker (RabbitMQ/Redis)                  │
│ - Routes messages between services                   │
│ - Persists async messages                            │
│ - Ensures delivery                                   │
└──────────────┬───────────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┐
    │          │          │          │          │
    ↓          ↓          ↓          ↓          ↓
┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
│ Intent  ││Retriever││Generator││Citation ││Visualiz.│
│ Agent   ││Agent    ││Agent    ││Agent    ││Agent    │
│ (1x)    ││(5x)     ││(8x)     ││(1x)     ││(1x)     │
└────┬────┘└────┬────┘└────┬────┘└────┬────┘└────┬────┘
     │          │          │          │          │
     └──────────┼──────────┼──────────┼──────────┘
                │
                ↓
        ┌──────────────────┐
        │ Service Registry │
        │ (Consul/etcd)    │
        │                  │
        │ - Agent list     │
        │ - Addresses      │
        │ - Health status  │
        │ - Capabilities   │
        └──────────────────┘
                ↑
                │ Health checks
                │ every 10s
                │
    ┌───────────┼───────────┐
    │           │           │
    ↑           ↑           ↑
 Health       Health      Health
 Check        Check       Check
 (Intent)     (Retriever) (Generator)
```

### Agent Deployment

```
┌─────────────────────────────────────────────┐
│ Kubernetes Cluster                          │
├─────────────────────────────────────────────┤
│                                             │
│ ┌─────────────────────────────────────┐    │
│ │ Intent Agent Pod (1 replica)        │    │
│ │ ├─ Container: intent-agent:1.0      │    │
│ │ ├─ CPU: 500m, Memory: 512Mi         │    │
│ │ └─ Service: intent-agent:8001       │    │
│ └─────────────────────────────────────┘    │
│                                             │
│ ┌──────────────────────────────────────┐   │
│ │ Retriever Agent Deployment (5 replicas)  │
│ │ ┌─ Pod 1 (retriever-0)               │   │
│ │ │  └─ Container: retriever-agent:1.0 │   │
│ │ ┌─ Pod 2 (retriever-1)               │   │
│ │ │  └─ Container: retriever-agent:1.0 │   │
│ │ ├─ Pod 3 (retriever-2)               │   │
│ │ ├─ Pod 4 (retriever-3)               │   │
│ │ ├─ Pod 5 (retriever-4)               │   │
│ │ ├─ CPU: 1000m ea, Memory: 2Gi ea    │   │
│ │ └─ Service: retriever-agent:8002    │   │
│ └──────────────────────────────────────┘   │
│                                             │
│ ┌──────────────────────────────────────┐   │
│ │ Generator Agent Deployment (8 replicas)  │
│ │ ├─ Pod 1-8: generator-agent:1.0     │   │
│ │ ├─ CPU: 2000m ea, Memory: 4Gi ea    │   │
│ │ └─ Service: generator-agent:8003    │   │
│ └──────────────────────────────────────┘   │
│                                             │
│ ... (Citation, Visualization agents)        │
│                                             │
└─────────────────────────────────────────────┘
```

### Agent Communication Flow

```
LangGraph                 A2A Message Broker      Retriever Agents
(Orchestrator)                                    (Multiple Replicas)
    │
    │ "Call retriever_agent"
    │ (intent_result, question)
    ├────────────┐
    │            │
    │     (Create TargetAgent message)
    │     (Add to queue)
    │            │
    │            ├──────────────────────────────────>│
    │            │  Message: {"req_id": "123",      │
    │            │             "agent": "retriever",│
    │            │             "params": {...}}     │
    │            │                                   │
    │            │  Load Balancer picks idle agent
    │            │                                   │
    │            ├──────────────────────────────────>│ retriever-pod-2
    │            │  (Pod 2 picks up message)        │
    │            │                                   │
    │            │  Execute retriever logic         │
    │            │                                   │
    │            │<──────────────────────────────────┤
    │            │  Response: {"status": "success",  │
    │            │             "result": {...},      │
    │            │             "latency": 245ms}     │
    │            │                                   │
    │<───────────┤                                   │
    │  (Wait for response)                           │
    │
    │ Continue to next agent
    │
```

---

## Message Protocol

### Message Format (JSON-RPC 2.0 Style)

```python
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Literal
from datetime import datetime
from enum import Enum
import uuid

class MessageType(str, Enum):
    """Types of A2A messages."""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    NOTIFICATION = "notification"  # One-way, no response expected
    HEALTH_CHECK = "health_check"
    HEALTH_RESPONSE = "health_response"

class MessageStatus(str, Enum):
    """Status of message delivery."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class A2AMessage:
    """Standard A2A protocol message."""

    # Message identification
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.REQUEST
    timestamp: datetime = field(default_factory=datetime.now)

    # Request/Response pairing
    request_id: Optional[str] = None  # For responses, link back to request
    correlation_id: str = ""  # For distributed tracing

    # Sender/Receiver
    sender_agent: str  # "langgraph_orchestrator" or agent name
    sender_service: str  # Kubernetes service name
    sender_instance: Optional[str] = None  # Pod name if applicable

    target_agent: str  # Which agent this is for
    target_service: str  # Kubernetes service name
    target_instance: Optional[str] = None  # Specific pod (for routing)

    # Content
    method: str = "invoke"  # RPC method name
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    # Metadata
    priority: Literal["low", "normal", "high"] = "normal"
    timeout: int = 30  # seconds
    retry_count: int = 0
    max_retries: int = 3

    # Delivery tracking
    status: MessageStatus = MessageStatus.PENDING
    delivery_attempts: int = 0
    last_error: Optional[str] = None

    # Tracing & Observability
    trace_id: str = ""
    span_id: str = ""
    parent_span_id: Optional[str] = None


@dataclass
class A2ARequest:
    """Request message structure."""
    message_id: str
    sender_agent: str
    target_agent: str
    method: str  # "invoke", "get_status", "get_capabilities"
    parameters: Dict[str, Any]
    timeout: int = 30
    trace_id: str = ""


@dataclass
class A2AResponse:
    """Response message structure."""
    message_id: str
    request_id: str  # Link back to request
    sender_agent: str  # Now the target agent
    target_agent: str  # Now the original sender
    status: Literal["success", "error"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0  # milliseconds
    trace_id: str = ""


@dataclass
class A2AHealthCheck:
    """Health check message."""
    message_id: str
    sender_agent: str  # Registry/orchestrator
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class A2AHealthResponse:
    """Health check response."""
    message_id: str
    agent_name: str
    instance_id: str
    status: Literal["healthy", "degraded", "unhealthy"]
    uptime: float  # seconds
    memory_usage: Dict[str, float]  # {used: 512, total: 1024} in MB
    cpu_usage: float  # percentage 0-100
    requests_processed: int
    error_rate: float  # 0-1
    timestamp: datetime = field(default_factory=datetime.now)
```

### Example Messages

#### Request Message (JSON)

```json
{
  "message_id": "msg-550e8400-e29b-41d4-a716-446655440000",
  "message_type": "request",
  "timestamp": "2025-11-17T10:30:45.123Z",
  "sender_agent": "langgraph_orchestrator",
  "sender_service": "api-gateway",
  "target_agent": "retriever_agent",
  "target_service": "retriever-agent",
  "method": "invoke",
  "parameters": {
    "question": "What are pump specifications?",
    "optimized_question": "pump specifications features types",
    "sub_questions": []
  },
  "priority": "normal",
  "timeout": 30,
  "max_retries": 3,
  "trace_id": "trace-123",
  "correlation_id": "conv-456"
}
```

#### Response Message (JSON)

```json
{
  "message_id": "msg-550e8400-e29b-41d4-a716-446655440001",
  "request_id": "msg-550e8400-e29b-41d4-a716-446655440000",
  "sender_agent": "retriever_agent",
  "sender_service": "retriever-agent",
  "sender_instance": "retriever-pod-2",
  "target_agent": "langgraph_orchestrator",
  "target_service": "api-gateway",
  "status": "success",
  "result": {
    "documents": [
      {
        "doc_id": "doc-1",
        "content": "...",
        "score": 0.95,
        "source": "pump_manual.pdf"
      }
    ],
    "retrieval_confidence": 0.87,
    "retrieval_method": "hybrid_with_web_search"
  },
  "execution_time": 2345,
  "trace_id": "trace-123"
}
```

#### Error Message (JSON)

```json
{
  "message_id": "msg-550e8400-e29b-41d4-a716-446655440002",
  "request_id": "msg-550e8400-e29b-41d4-a716-446655440000",
  "sender_agent": "retriever_agent",
  "target_agent": "langgraph_orchestrator",
  "status": "error",
  "error": "Retrieval failed: No documents found matching query",
  "last_error": "Vector search returned 0 results",
  "trace_id": "trace-123"
}
```

#### Health Check Message (JSON)

```json
{
  "message_id": "msg-health-check-001",
  "message_type": "health_check",
  "sender_agent": "service_registry",
  "timestamp": "2025-11-17T10:30:45.123Z"
}
```

#### Health Response Message (JSON)

```json
{
  "message_id": "msg-health-response-001",
  "message_type": "health_response",
  "agent_name": "retriever_agent",
  "instance_id": "retriever-pod-2",
  "status": "healthy",
  "uptime": 86400,
  "memory_usage": {
    "used": 512,
    "total": 2048
  },
  "cpu_usage": 45.2,
  "requests_processed": 15234,
  "error_rate": 0.01,
  "timestamp": "2025-11-17T10:30:45.123Z"
}
```

---

## Agent Registry

### Service Registry Architecture

```
┌──────────────────────────────────┐
│ Service Registry (Consul/etcd)   │
├──────────────────────────────────┤
│                                  │
│ Agent Catalog:                   │
│ ├─ intent_agent                  │
│ │  ├─ Service: intent-agent      │
│ │  ├─ Port: 8001                 │
│ │  ├─ Instances:                 │
│ │  │  └─ intent-pod-1            │
│ │  │     ├─ Address: 10.0.1.10   │
│ │  │     ├─ Status: healthy      │
│ │  │     └─ Tags: [v1.0, prod]   │
│ │  └─ Capabilities:              │
│ │     └─ [detect_intent, ...]    │
│ │                                │
│ ├─ retriever_agent               │
│ │  ├─ Service: retriever-agent   │
│ │  ├─ Port: 8002                 │
│ │  ├─ Instances:                 │
│ │  │  ├─ retriever-pod-1         │
│ │  │  ├─ retriever-pod-2         │
│ │  │  ├─ retriever-pod-3         │
│ │  │  ├─ retriever-pod-4         │
│ │  │  └─ retriever-pod-5         │
│ │  └─ Capabilities:              │
│ │     └─ [hybrid_search, ...]    │
│ │                                │
│ ├─ generator_agent               │
│ │  ├─ Service: generator-agent   │
│ │  ├─ Instances: 8               │
│ │  └─ ...                         │
│ │                                │
│ └─ (citation, visualization)     │
│                                  │
└──────────────────────────────────┘
```

### Agent Registration

```python
@dataclass
class AgentRegistration:
    """Agent service registration."""
    agent_name: str  # "retriever_agent"
    service_name: str  # "retriever-agent" (K8s service)
    version: str  # "1.0.0"
    port: int  # 8002

    # Instance info
    instance_id: str  # Pod name: "retriever-pod-2"
    address: str  # IP or DNS: "10.0.1.11"

    # Health & status
    status: Literal["healthy", "degraded", "unhealthy"]
    last_heartbeat: datetime
    uptime: float

    # Capabilities
    capabilities: List[str]  # ["hybrid_search", "vector_search", "web_search"]

    # Metadata
    tags: List[str]  # ["v1.0", "prod", "retriever"]
    metadata: Dict[str, str]  # {"region": "us-east", "zone": "az1"}

class ServiceRegistry:
    """Manage agent service discovery."""

    def __init__(self, consul_url: str = "http://localhost:8500"):
        self.consul_url = consul_url
        self.agents: Dict[str, List[AgentRegistration]] = {}

    def register_agent(self, registration: AgentRegistration):
        """Register agent with registry."""
        if registration.agent_name not in self.agents:
            self.agents[registration.agent_name] = []

        self.agents[registration.agent_name].append(registration)
        logger.info(f"Registered {registration.instance_id} for {registration.agent_name}")

    def deregister_agent(self, agent_name: str, instance_id: str):
        """Deregister agent instance."""
        if agent_name in self.agents:
            self.agents[agent_name] = [
                a for a in self.agents[agent_name]
                if a.instance_id != instance_id
            ]

    def get_healthy_instances(self, agent_name: str) -> List[AgentRegistration]:
        """Get all healthy instances of an agent."""
        return [
            a for a in self.agents.get(agent_name, [])
            if a.status == "healthy"
        ]

    def get_agent_by_instance(self, instance_id: str) -> Optional[AgentRegistration]:
        """Get specific agent instance."""
        for agents in self.agents.values():
            for agent in agents:
                if agent.instance_id == instance_id:
                    return agent
        return None

    def list_agents(self) -> Dict[str, List[AgentRegistration]]:
        """List all registered agents."""
        return self.agents

    def update_agent_status(self, instance_id: str, status: str):
        """Update agent health status."""
        agent = self.get_agent_by_instance(instance_id)
        if agent:
            agent.status = status
            agent.last_heartbeat = datetime.now()
```

---

## Communication Patterns

### Pattern 1: Synchronous Request-Response

```
LangGraph                  Message Broker              Retriever Agent
    │                            │                            │
    ├─ A2ARequest ─────────────>│                            │
    │  (call retriever)          ├─ Route to healthy ───────>│
    │                            │  instance (load balance)   │
    │  [WAITING...]              │                            │
    │                            │ [Execute retriever logic]  │
    │                            │<─ A2AResponse ────────────┤
    │<─ A2AResponse ─────────────┤                            │
    │  (documents + metadata)    │                            │
    │                            │                            │
    ├─ Continue to next agent   │                            │
```

**When to use**: Agent calls are dependent (wait for result)
- LangGraph orchestrator → Intent Agent
- Intent Agent result → determines if decomposition needed
- Retriever Agent → Generator Agent

---

### Pattern 2: Asynchronous Fire-and-Forget (Notification)

```
LangGraph                  Message Broker              Visualization Agent
    │                            │                            │
    ├─ A2ANotification ────────>│                            │
    │  (visualize results)       ├─ Queue notification ────>│
    │  [NO WAITING]              │                            │
    │                            │ [Return immediately]      │
    │  Continue immediately      │                            │
    │                            │ [Async: execute later]    │
    │                            │                            │
    │                            │<─ Ack received ───────────┤
```

**When to use**: Fire-and-forget operations
- Visualization (mind map generation)
- Audit logging
- Metrics reporting

---

### Pattern 3: Publish-Subscribe (Event-based)

```
Generator Agent         Message Broker           [Subscribers]
    │                        │                      │
    ├─ Publish Event: ─────>│                      │
    │  "answer_generated"    ├─> Notify ──────────>│ Visualization
    │                        │                      │
    │                        ├─> Notify ──────────>│ Citation
    │                        │                      │
    │                        ├─> Notify ──────────>│ Audit Logger
    │                        │                      │
```

**When to use**: One-to-many notifications
- Answer generated → notify visualization, citation, logger
- Retrieval complete → notify downstream agents

---

### Pattern 4: Request with Retry (Circuit Breaker)

```
Orchestrator             Load Balancer              Agent Instances
    │                          │                      │
    ├─ Request ──────────────>│                      │
    │ (timeout: 10s)          ├─ Try pod-1 ────────>│ pod-1 [SLOW]
    │                         │ (timeout: 5s)        │
    │                         │<─ Timeout ──────────┤
    │                         │                      │
    │  [Retry with new pod]   ├─ Try pod-2 ────────>│ pod-2 [OK]
    │                         │                      │ [Respond]
    │                         │<─ Success ──────────┤
    │<─ Response ────────────┤                      │
```

**When to use**: Resilience against slow/failing agents
- Max retries: 3
- Exponential backoff: 100ms, 200ms, 400ms
- Circuit breaker: mark slow agents as degraded

---

## Load Balancing

### Load Balancing Strategy

```python
from typing import List
from enum import Enum

class LoadBalancingStrategy(str, Enum):
    """Load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    WEIGHTED = "weighted"  # Based on agent health/capacity
    LEAST_LATENCY = "least_latency"  # Based on response time

class LoadBalancer:
    """Distribute requests across agent instances."""

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS):
        self.strategy = strategy
        self.round_robin_index = 0
        self.instance_stats: Dict[str, Dict[str, Any]] = {}

    def select_instance(
        self,
        agent_name: str,
        healthy_instances: List[AgentRegistration]
    ) -> Optional[AgentRegistration]:
        """Select an instance based on strategy."""

        if not healthy_instances:
            logger.warning(f"No healthy instances for {agent_name}")
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(healthy_instances)

        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy_instances, agent_name)

        elif self.strategy == LoadBalancingStrategy.LEAST_LATENCY:
            return self._least_latency(healthy_instances, agent_name)

        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted_selection(healthy_instances)

        else:  # RANDOM
            import random
            return random.choice(healthy_instances)

    def _round_robin(self, instances: List[AgentRegistration]) -> AgentRegistration:
        """Simple round-robin rotation."""
        selected = instances[self.round_robin_index % len(instances)]
        self.round_robin_index += 1
        return selected

    def _least_connections(
        self,
        instances: List[AgentRegistration],
        agent_name: str
    ) -> AgentRegistration:
        """Select instance with fewest active connections."""
        min_connections = float('inf')
        selected = instances[0]

        for instance in instances:
            stats = self.instance_stats.get(instance.instance_id, {})
            connections = stats.get("active_connections", 0)

            if connections < min_connections:
                min_connections = connections
                selected = instance

        return selected

    def _least_latency(
        self,
        instances: List[AgentRegistration],
        agent_name: str
    ) -> AgentRegistration:
        """Select instance with lowest average latency."""
        min_latency = float('inf')
        selected = instances[0]

        for instance in instances:
            stats = self.instance_stats.get(instance.instance_id, {})
            avg_latency = stats.get("avg_latency", 1000)  # ms

            if avg_latency < min_latency:
                min_latency = avg_latency
                selected = instance

        return selected

    def _weighted_selection(
        self,
        instances: List[AgentRegistration]
    ) -> AgentRegistration:
        """Select based on health and capacity."""
        import random

        # Calculate weights
        weights = []
        for instance in instances:
            weight = 1.0

            # Adjust by health
            if instance.status == "healthy":
                weight *= 1.0
            elif instance.status == "degraded":
                weight *= 0.5
            else:
                weight *= 0.1

            weights.append(weight)

        # Weighted random selection
        return random.choices(instances, weights=weights, k=1)[0]

    def record_latency(self, instance_id: str, latency_ms: float):
        """Record response latency for load balancing."""
        if instance_id not in self.instance_stats:
            self.instance_stats[instance_id] = {
                "latencies": [],
                "avg_latency": 0
            }

        stats = self.instance_stats[instance_id]
        stats["latencies"].append(latency_ms)

        # Keep last 100 measurements
        if len(stats["latencies"]) > 100:
            stats["latencies"].pop(0)

        # Calculate average
        stats["avg_latency"] = sum(stats["latencies"]) / len(stats["latencies"])

    def record_connection(self, instance_id: str, active: bool):
        """Record active connection count."""
        if instance_id not in self.instance_stats:
            self.instance_stats[instance_id] = {"active_connections": 0}

        stats = self.instance_stats[instance_id]
        if active:
            stats["active_connections"] += 1
        else:
            stats["active_connections"] = max(0, stats["active_connections"] - 1)
```

---

## Health Monitoring

### Health Check System

```python
from enum import Enum
import asyncio

class HealthCheckType(str, Enum):
    """Types of health checks."""
    LIVENESS = "liveness"      # Is agent process alive?
    READINESS = "readiness"    # Can agent accept requests?
    STARTUP = "startup"        # Has agent finished initialization?

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    agent_name: str
    instance_id: str
    check_type: HealthCheckType
    status: Literal["healthy", "degraded", "unhealthy"]
    message: str
    timestamp: datetime

    # Metrics
    cpu_usage: float  # 0-100%
    memory_usage: float  # 0-100%
    request_latency: float  # ms
    error_rate: float  # 0-1
    uptime: float  # seconds

class HealthCheckManager:
    """Manage agent health monitoring."""

    def __init__(self, registry: ServiceRegistry, interval: int = 10):
        self.registry = registry
        self.interval = interval  # seconds between checks
        self.health_history: Dict[str, List[HealthCheckResult]] = {}

    async def run_health_checks(self):
        """Continuously run health checks on all agents."""
        while True:
            agents = self.registry.list_agents()

            for agent_name, instances in agents.items():
                for instance in instances:
                    # Run health check
                    result = await self._check_agent_health(instance)

                    # Store result
                    if instance.instance_id not in self.health_history:
                        self.health_history[instance.instance_id] = []

                    self.health_history[instance.instance_id].append(result)

                    # Keep last 100 checks
                    if len(self.health_history[instance.instance_id]) > 100:
                        self.health_history[instance.instance_id].pop(0)

                    # Update registry
                    self.registry.update_agent_status(
                        instance.instance_id,
                        result.status
                    )

            await asyncio.sleep(self.interval)

    async def _check_agent_health(self, instance: AgentRegistration) -> HealthCheckResult:
        """Check health of single agent instance."""
        try:
            # Send health check message
            message = A2AHealthCheck(
                message_id=str(uuid.uuid4()),
                sender_agent="health_checker"
            )

            response = await self._send_with_timeout(
                instance,
                message,
                timeout=5
            )

            # Evaluate health based on response
            status = "healthy"
            if response.get("cpu_usage", 0) > 80 or response.get("memory_usage", 0) > 85:
                status = "degraded"
            elif response.get("error_rate", 0) > 0.05:
                status = "degraded"

            return HealthCheckResult(
                agent_name=instance.agent_name,
                instance_id=instance.instance_id,
                check_type=HealthCheckType.LIVENESS,
                status=status,
                message="Health check passed",
                timestamp=datetime.now(),
                cpu_usage=response.get("cpu_usage", 0),
                memory_usage=response.get("memory_usage", 0),
                request_latency=response.get("latency", 0),
                error_rate=response.get("error_rate", 0),
                uptime=response.get("uptime", 0)
            )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                agent_name=instance.agent_name,
                instance_id=instance.instance_id,
                check_type=HealthCheckType.LIVENESS,
                status="unhealthy",
                message="Health check timeout",
                timestamp=datetime.now(),
                cpu_usage=0,
                memory_usage=0,
                request_latency=5000,
                error_rate=1.0,
                uptime=0
            )

        except Exception as e:
            logger.error(f"Health check failed for {instance.instance_id}: {e}")
            return HealthCheckResult(
                agent_name=instance.agent_name,
                instance_id=instance.instance_id,
                check_type=HealthCheckType.LIVENESS,
                status="unhealthy",
                message=str(e),
                timestamp=datetime.now(),
                cpu_usage=0,
                memory_usage=0,
                request_latency=0,
                error_rate=1.0,
                uptime=0
            )

    async def _send_with_timeout(self, instance, message, timeout):
        """Send message with timeout."""
        try:
            # Implementation: Send HTTP request to agent health endpoint
            return await asyncio.wait_for(
                self._send_to_agent(instance, message),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise
```

---

## Error Handling & Resilience

### Circuit Breaker Pattern

```python
from enum import Enum
from datetime import timedelta

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Working normally
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing if recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes before closing
    timeout: int = 60  # seconds before half-open
    monitor_window: int = 60  # seconds to monitor failures

class CircuitBreaker:
    """Implement circuit breaker for agent resilience."""

    def __init__(self, agent_name: str, config: CircuitBreakerConfig = None):
        self.agent_name = agent_name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None

    async def call(self, request: A2ARequest, executor_fn) -> A2AResponse:
        """Execute request with circuit breaker protection."""

        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if timeout passed
            if datetime.now() - self.opened_at > timedelta(seconds=self.config.timeout):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info(f"Circuit breaker {self.agent_name} HALF_OPEN (testing recovery)")
            else:
                # Circuit still open, reject
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.agent_name} is OPEN"
                )

        # Execute request
        try:
            response = await executor_fn(request)

            # Handle success
            self.failure_count = 0
            self.success_count += 1

            if self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    logger.info(f"Circuit breaker {self.agent_name} CLOSED (recovered)")

            return response

        except Exception as e:
            # Handle failure
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitState.HALF_OPEN:
                # Failure in half-open, reopen circuit
                self.state = CircuitState.OPEN
                self.opened_at = datetime.now()
                logger.warning(f"Circuit breaker {self.agent_name} OPEN (recovery failed)")
                raise

            elif self.failure_count >= self.config.failure_threshold:
                # Too many failures, open circuit
                self.state = CircuitState.OPEN
                self.opened_at = datetime.now()
                logger.warning(f"Circuit breaker {self.agent_name} OPEN (threshold exceeded)")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.agent_name} opened after {self.failure_count} failures"
                )

            raise

class CircuitBreakerOpenError(Exception):
    """Circuit breaker is open."""
    pass
```

### Retry with Exponential Backoff

```python
import asyncio

class RetryStrategy:
    """Implement retry with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.1,  # 100ms
        max_delay: float = 10.0,  # 10 seconds
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    async def execute_with_retry(self, fn, *args, **kwargs):
        """Execute function with retries."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await fn(*args, **kwargs)

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.initial_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )

                    # Add jitter (random 0-25% of delay)
                    import random
                    jitter = delay * random.uniform(0, 0.25)
                    total_delay = delay + jitter

                    logger.info(f"Retrying in {total_delay:.2f}s...")
                    await asyncio.sleep(total_delay)

        # All retries failed
        raise last_exception
```

### Timeout Handling

```python
class TimeoutError(Exception):
    """Request timeout."""
    pass

async def call_with_timeout(
    agent_name: str,
    request: A2ARequest,
    executor_fn,
    timeout: int = 30
):
    """Execute agent call with timeout."""
    try:
        return await asyncio.wait_for(
            executor_fn(request),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Timeout calling {agent_name} after {timeout}s")
        raise TimeoutError(f"Agent {agent_name} timeout after {timeout}s")
```

---

## Configuration

### A2A Configuration YAML

```yaml
# config/a2a_protocol.yaml

# A2A Protocol Settings
a2a:
  protocol_version: "1.0.0"
  message_format: "json"
  transport: "http"  # or "grpc"

# Message Broker (RabbitMQ/Redis)
message_broker:
  type: "rabbitmq"  # or "redis"
  url: "${RABBITMQ_URL:-amqp://guest:guest@localhost:5672/}"

  # Queue settings
  queues:
    prefetch_count: 10  # Messages to prefetch per worker
    durable: true       # Survive broker restart
    auto_delete: false  # Don't delete on disconnect

  # Acknowledgment
  ack_mode: "manual"  # Require explicit ACK

# Service Registry (Consul/etcd)
service_registry:
  type: "consul"  # or "etcd"
  url: "${CONSUL_URL:-http://localhost:8500}"

  # Health check settings
  health_check_interval: 10  # seconds
  health_check_timeout: 5     # seconds
  deregister_critical_after: 60  # seconds

# Load Balancing
load_balancer:
  strategy: "least_connections"  # round_robin, random, weighted, least_latency

  # Connection tracking
  track_connections: true
  track_latency: true

# Resilience
resilience:
  # Circuit Breaker
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    success_threshold: 2
    timeout: 60  # seconds

  # Retry Policy
  retry:
    max_retries: 3
    initial_delay: 0.1  # seconds
    max_delay: 10.0
    exponential_base: 2.0

  # Timeouts
  timeouts:
    request: 30  # seconds
    health_check: 5
    registry: 5

# Tracing (Jaeger/Zipkin)
tracing:
  enabled: true
  backend: "jaeger"
  jaeger_url: "http://localhost:6831"
  sample_rate: 1.0  # Sample 100% of requests

# Metrics (Prometheus)
metrics:
  enabled: true
  port: 9090
  interval: 10  # seconds

# Logging
logging:
  level: "INFO"
  format: "json"
  output:
    - "stdout"
    - "file"
  file_path: "/var/log/a2a.log"

# Agent Configuration
agents:
  intent_agent:
    instances: 1
    port: 8001
    timeout: 10
    max_retries: 2

  retriever_agent:
    instances: 5
    port: 8002
    timeout: 15
    max_retries: 3

  generator_agent:
    instances: 8
    port: 8003
    timeout: 30
    max_retries: 2

  citation_agent:
    instances: 1
    port: 8004
    timeout: 10
    max_retries: 2

  visualization_agent:
    instances: 1
    port: 8005
    timeout: 10
    max_retries: 2

# Security
security:
  mtls_enabled: false  # mTLS between services
  tls_cert_path: "/etc/tls/cert.pem"
  tls_key_path: "/etc/tls/key.pem"
  verify_hostname: true
```

---

## Testing Strategy

### Unit Tests

```python
# test_a2a_protocol.py

def test_message_serialization():
    """Test A2A message can be serialized/deserialized."""
    message = A2ARequest(
        message_id="msg-123",
        sender_agent="orchestrator",
        target_agent="retriever_agent",
        method="invoke",
        parameters={"query": "test"}
    )

    # Serialize to JSON
    import json
    json_str = json.dumps(message.__dict__, default=str)

    # Deserialize
    data = json.loads(json_str)
    assert data["message_id"] == "msg-123"
    assert data["target_agent"] == "retriever_agent"

def test_load_balancer_round_robin():
    """Test round-robin load balancing."""
    instances = [
        AgentRegistration(agent_name="retriever", instance_id="pod-1", ...),
        AgentRegistration(agent_name="retriever", instance_id="pod-2", ...),
        AgentRegistration(agent_name="retriever", instance_id="pod-3", ...),
    ]

    lb = LoadBalancer(strategy=LoadBalancingStrategy.ROUND_ROBIN)

    # Should rotate through instances
    assert lb.select_instance("retriever", instances).instance_id == "pod-1"
    assert lb.select_instance("retriever", instances).instance_id == "pod-2"
    assert lb.select_instance("retriever", instances).instance_id == "pod-3"
    assert lb.select_instance("retriever", instances).instance_id == "pod-1"

def test_circuit_breaker_opens_on_failures():
    """Test circuit breaker opens after threshold."""
    config = CircuitBreakerConfig(failure_threshold=3)
    cb = CircuitBreaker("retriever_agent", config)

    async def failing_fn(request):
        raise Exception("Agent error")

    # First 3 attempts should fail and track
    for _ in range(3):
        with pytest.raises(Exception):
            asyncio.run(cb.call(A2ARequest(...), failing_fn))

    # Should now be open
    assert cb.state == CircuitState.OPEN

def test_retry_with_backoff():
    """Test retry happens with exponential backoff."""
    retry = RetryStrategy(max_retries=2, initial_delay=0.01)

    call_times = []

    async def failing_fn():
        call_times.append(time.time())
        if len(call_times) < 3:
            raise Exception("Fail")
        return "success"

    result = asyncio.run(retry.execute_with_retry(failing_fn))
    assert result == "success"
    assert len(call_times) == 3

    # Verify backoff timing
    assert call_times[1] - call_times[0] >= 0.01
    assert call_times[2] - call_times[1] >= 0.02
```

### Integration Tests

```python
# test_a2a_integration.py

@pytest.mark.asyncio
async def test_agent_registration_and_discovery():
    """Test agents can register and be discovered."""
    registry = ServiceRegistry()

    # Register agent
    agent1 = AgentRegistration(
        agent_name="retriever_agent",
        service_name="retriever-agent",
        instance_id="retriever-pod-1",
        address="10.0.1.10",
        status="healthy",
        ...
    )

    registry.register_agent(agent1)

    # Discover agent
    healthy = registry.get_healthy_instances("retriever_agent")
    assert len(healthy) == 1
    assert healthy[0].instance_id == "retriever-pod-1"

@pytest.mark.asyncio
async def test_request_response_flow():
    """Test complete request-response cycle."""
    # Setup mock broker and registry
    broker = MockMessageBroker()
    registry = ServiceRegistry()

    # Register agent
    registry.register_agent(agent_registration)

    # Send request
    request = A2ARequest(...)
    lb = LoadBalancer()
    instance = lb.select_instance("retriever_agent", registry.get_healthy_instances("retriever_agent"))

    # Simulate response
    response = await broker.send_and_wait(request, timeout=5)

    assert response.status == "success"
    assert response.result is not None

@pytest.mark.asyncio
async def test_health_check_updates_status():
    """Test health checks update agent status."""
    registry = ServiceRegistry()
    health_mgr = HealthCheckManager(registry, interval=1)

    # Register unhealthy agent
    agent = AgentRegistration(
        agent_name="retriever_agent",
        instance_id="retriever-pod-1",
        status="healthy",
        ...
    )
    registry.register_agent(agent)

    # Simulate health check failing
    with patch.object(health_mgr, '_check_agent_health') as mock:
        mock.return_value = HealthCheckResult(
            agent_name="retriever_agent",
            instance_id="retriever-pod-1",
            status="unhealthy",
            ...
        )

        await health_mgr.run_health_checks()

    # Status should be updated
    updated_agent = registry.get_agent_by_instance("retriever-pod-1")
    assert updated_agent.status == "unhealthy"
```

### Performance Tests

```python
# test_a2a_performance.py

@pytest.mark.asyncio
async def test_request_latency():
    """Test message latency is acceptable."""
    # Measure end-to-end latency
    start = time.time()

    request = A2ARequest(...)
    response = await send_request(request)

    latency = (time.time() - start) * 1000  # ms

    # Should complete in <100ms for healthy instance
    assert latency < 100

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test system handles concurrent requests."""
    tasks = []

    for i in range(100):
        request = A2ARequest(...)
        tasks.append(send_request(request))

    start = time.time()
    responses = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    # 100 requests should complete in reasonable time
    assert elapsed < 10
    assert all(r.status == "success" for r in responses)

@pytest.mark.asyncio
async def test_load_distribution():
    """Test load is distributed fairly across instances."""
    instances = [f"pod-{i}" for i in range(5)]
    request_counts = {pod: 0 for pod in instances}

    # Send 1000 requests
    for _ in range(1000):
        instance = select_instance_with_tracking()
        request_counts[instance.instance_id] += 1

    # Each should get ~200 requests (+-20%)
    for pod, count in request_counts.items():
        expected = 1000 / 5
        assert abs(count - expected) < expected * 0.2  # Within 20%
```

---

## Implementation Checklist

- [ ] Define A2AMessage, A2ARequest, A2AResponse dataclasses
- [ ] Define A2AHealthCheck and A2AHealthResponse dataclasses
- [ ] Implement message serialization/deserialization
- [ ] Choose and setup message broker (RabbitMQ or Redis)
- [ ] Implement MessageBroker client for sending/receiving
- [ ] Choose and setup service registry (Consul or etcd)
- [ ] Implement ServiceRegistry with register/deregister/discover
- [ ] Implement LoadBalancer with multiple strategies
- [ ] Implement CircuitBreaker pattern
- [ ] Implement RetryStrategy with exponential backoff
- [ ] Implement HealthCheckManager
- [ ] Implement timeout handling
- [ ] Implement A2AClient for agents to call each other
- [ ] Implement A2AServer (HTTP/gRPC endpoints) for each agent
- [ ] Add distributed tracing (Jaeger/Zipkin integration)
- [ ] Add metrics collection (Prometheus)
- [ ] Create configuration YAML
- [ ] Write unit tests (serialization, LB, circuit breaker, retry)
- [ ] Write integration tests (registration, request-response, health checks)
- [ ] Write performance tests (latency, concurrency, load distribution)
- [ ] Write chaos tests (failures, timeouts, partial outages)

---

## Summary

This design document provides:

✅ **Message protocol** with request/response/health check formats
✅ **Service registry** for agent discovery and health tracking
✅ **Load balancing** with 5 different strategies
✅ **Communication patterns** (sync, async, pub-sub, retry)
✅ **Health monitoring** with continuous checks
✅ **Circuit breaker** for failure handling
✅ **Retry strategy** with exponential backoff
✅ **Complete configuration** YAML file
✅ **Testing strategy** with unit, integration, and performance tests

**Key Insights**:
- Each agent is a separate service that registers with registry
- Requests routed via load balancer to healthy instances
- Failures handled via circuit breaker + retry logic
- Health checks run continuously to maintain instance list
- All communication is async/event-driven

**Next Steps**:
1. Review this design
2. Implement A2A protocol layer
3. Deploy agents as Kubernetes microservices
4. Run end-to-end tests with full system
5. Optimize based on production metrics

---

**Last Updated**: November 17, 2025
**Status**: Ready for Implementation Review
