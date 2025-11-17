# Phase 2: LangGraph Orchestration Design

## Executive Summary

This document defines the LangGraph orchestration layer that coordinates 5 specialized agents (Intent, Retriever, Generator, Citation, Visualization) to process user questions in parallel and conditionally. Instead of sequential pipeline execution, the orchestrator enables:

- **Conditional routing** (skip decomposition if simple, use fallback if retrieval fails)
- **Parallel agent execution** (retriever and other agents can run in parallel)
- **State persistence** (all context available to any agent at any time)
- **Error recovery** (multiple fallback strategies)
- **Human-in-the-loop** (approval points for uncertain answers)

**Core Concept**: Transform from sequential FullQAPipeline → parallel LangGraph orchestrator with 5 agent nodes.

---

## Problem Statement

### Current Issues (Sequential Pipeline)
1. **No Conditional Logic** - All steps execute regardless of necessity
   - Simple questions still decomposed (wastes LLM call)
   - Visualization always generated even if not needed

2. **Sequential Bottleneck** - Steps must complete before next starts
   - Even when some steps could run in parallel
   - Total latency = sum of all steps

3. **No State Visibility** - Context lost between steps
   - Hard to debug where a failure occurred
   - Can't retry with previous state

4. **Fixed Workflow** - Can't take alternate paths
   - No fallback if retrieval fails
   - No way to skip decomposition for simple questions

5. **No Agent Isolation** - Everything in one monolithic pipeline
   - Can't scale individual components
   - Can't reuse agents for different tasks

### Desired Behavior (LangGraph)
- ✅ Parallel execution where possible
- ✅ Conditional routing based on question complexity/confidence
- ✅ Error recovery with fallback strategies
- ✅ Complete state visibility at every step
- ✅ Independent agent scaling

---

## Design Goals

1. **Orchestration**: Coordinate 5 independent agents with explicit state transitions
2. **Parallelization**: Enable concurrent execution of independent agents
3. **Robustness**: Multiple fallback strategies for failure scenarios
4. **Observability**: Track state at every step for debugging
5. **Flexibility**: Support conditional routing based on question type/confidence
6. **Maintainability**: Clear interfaces between agents
7. **Scalability**: Agents can be scaled independently (in Phase 4)

---

## Architecture Diagram

### High-Level Flow
```
START
  ↓
INTENT AGENT
├─ Detect: complexity (simple/complex), type (factual/opinion/procedural)
├─ Priority: high/normal/low
└─ Confidence: 0.0-1.0
  ↓ (Conditional Edge #1: Is it simple?)
  ├─ SIMPLE → SKIP to REWRITE
  └─ COMPLEX → DECOMPOSE
  ↓
DECOMPOSE (Optional)
├─ Break down complex questions
└─ Create sub-questions
  ↓
REWRITE (Parallel with DECOMPOSE)
├─ Optimize for retrieval
└─ Create search query
  ↓
RETRIEVER AGENT (Parallel path possible)
├─ BM25 search
├─ Vector search
├─ Score documents
└─ Add confidence scores
  ↓ (Conditional Edge #2: Good results?)
  ├─ HIGH CONFIDENCE (>0.7) → GENERATE
  ├─ MEDIUM CONFIDENCE (0.4-0.7) → HUMAN APPROVAL
  └─ LOW CONFIDENCE (<0.4) → FALLBACK RETRIEVE
  ↓
FALLBACK RETRIEVE (Optional)
├─ Simpler search strategy
├─ Broader scope
└─ Return all candidates
  ↓
HUMAN APPROVAL (Optional)
├─ Wait for user feedback
└─ Proceed with approval or requery
  ↓
GENERATOR AGENT
├─ Generate answer with citations
└─ Add confidence indicators
  ↓
CITATION AGENT
├─ Extract citations
├─ Map to documents
└─ Format references
  ↓
VISUALIZATION AGENT (Optional, Parallel)
├─ Create mind map
└─ Generate knowledge graph
  ↓
END
```

### Detailed Node Graph
```
┌─────────────────┐
│ START           │
└────────┬────────┘
         ↓
┌─────────────────────────────────┐
│ INTENT_AGENT                    │
│ ├─ Complexity classification   │
│ ├─ Question type               │
│ └─ Priority & confidence       │
└────────┬────────────────────────┘
         ↓
    ┌────────────┐
    │ Conditional: Simple or Complex?
    └──┬──────────┬──┘
       │          │
   SIMPLE     COMPLEX
       │          │
       │      ┌───▼──────────┐
       │      │DECOMPOSE     │
       │      │ - Break down │
       │      │ - Sub Qs     │
       │      └───┬──────────┘
       │          │
       └──────┬───┘
              ↓
    ┌──────────────────┐
    │ REWRITE          │
    │ - Optimize query │
    └────────┬─────────┘
             ↓
    ┌────────────────────────────┐
    │ RETRIEVER_AGENT            │
    │ ├─ BM25 search            │
    │ ├─ Vector search          │
    │ ├─ Hybrid results         │
    │ └─ Confidence scores      │
    └────────┬─────────────────┘
             ↓
        ┌────────────────┐
        │ Conditional: Confidence?
        └────┬───────────┬──────┘
        HIGH│      MED   │LOW
            │            │
    ┌───────▼──┐   ┌────▼──────────────┐
    │GENERATE  │   │HUMAN_APPROVAL     │
    └────┬─────┘   │- Wait for input   │
         │         └────┬──────────────┘
         │              ↓
         │         ┌─────────────────┐
         │         │ FALLBACK_RETRIEVE│
         │         │ - Simpler search │
         │         └────┬─────────────┘
         │              │
         └──────┬───────┘
                ↓
    ┌───────────────────────┐
    │ GENERATOR_AGENT       │
    │ ├─ Generate answer    │
    │ ├─ With citations     │
    │ └─ Confidence level   │
    └──────────┬────────────┘
               ↓
    ┌──────────────────────┐
    │ CITATION_AGENT       │
    │ ├─ Extract citations │
    │ ├─ Map to sources    │
    │ └─ Format output     │
    └──────────┬───────────┘
               ↓
    ┌──────────────────────────┐
    │ VISUALIZATION_AGENT      │
    │ (Parallel with CITATION) │
    │ ├─ Generate mind map     │
    │ └─ Knowledge graph       │
    └──────────┬───────────────┘
               ↓
         ┌─────────────┐
         │ END         │
         └─────────────┘
```

---

## State Schema

### Complete SharedState Definition

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from kotaemon.base import Document

@dataclass
class SharedState:
    """Shared state across all agents in the LangGraph orchestrator.

    This state persists through the entire graph execution and is accessible
    to all nodes/agents for reading and updating.
    """

    # ============================================================================
    # SECTION 1: INPUT & CONTEXT
    # ============================================================================

    # Original user input
    question: str  # Original user question
    conversation_id: str  # Conversation identifier
    conversation_history: List[tuple] = field(default_factory=list)  # [(user_msg, ai_msg), ...]

    # ============================================================================
    # SECTION 2: INTENT ANALYSIS (Output from IntentAgent)
    # ============================================================================

    question_complexity: Optional[str] = None  # "simple" or "complex"
    question_type: Optional[str] = None  # "factual", "opinion", "procedural", "greeting"
    question_priority: Optional[str] = None  # "high", "normal", "low"
    intent_confidence: float = 0.0  # 0.0 - 1.0

    enriched_query: Optional[str] = None  # Original question + context

    # ============================================================================
    # SECTION 3: DECOMPOSITION (Optional, Output from DecomposeNode)
    # ============================================================================

    sub_questions: List[str] = field(default_factory=list)  # Broken down sub-questions
    should_decompose: bool = False  # Whether decomposition was performed

    # ============================================================================
    # SECTION 4: QUESTION REWRITING (Output from RewriteNode)
    # ============================================================================

    optimized_question: Optional[str] = None  # Rewritten for better retrieval
    search_keywords: List[str] = field(default_factory=list)  # Extracted keywords

    # ============================================================================
    # SECTION 5: RETRIEVAL (Output from RetrieverAgent)
    # ============================================================================

    # Retrieved documents
    documents: List[Document] = field(default_factory=list)  # Top-K retrieved documents
    document_ids: List[str] = field(default_factory=list)  # IDs of retrieved documents

    # Retrieval metadata
    retrieval_confidence: float = 0.0  # Average confidence of retrieved docs (0.0-1.0)
    retrieval_scores: Dict[str, float] = field(default_factory=dict)  # Doc ID -> score
    retrieval_method: str = "initial"  # "initial", "fallback_semantic", "fallback_broad"
    retrieval_attempt_count: int = 0  # Track retry attempts

    # ============================================================================
    # SECTION 6: FALLBACK RETRIEVAL (Optional)
    # ============================================================================

    fallback_documents: List[Document] = field(default_factory=list)  # Fallback results
    fallback_attempted: bool = False  # Was fallback retrieval used?
    fallback_method: Optional[str] = None  # "semantic_only", "broader_scope", "clarify"

    # ============================================================================
    # SECTION 7: HUMAN APPROVAL (Optional)
    # ============================================================================

    needs_human_approval: bool = False  # Should ask human?
    human_approval_reason: Optional[str] = None  # Why approval needed
    human_feedback: Optional[str] = None  # User's response
    human_approved: Optional[bool] = None  # True/False/None

    # ============================================================================
    # SECTION 8: GENERATION (Output from GeneratorAgent)
    # ============================================================================

    generated_answer: Optional[str] = None  # LLM-generated answer
    answer_confidence: float = 0.0  # Model's confidence (0.0-1.0)

    # ============================================================================
    # SECTION 9: CITATIONS (Output from CitationAgent)
    # ============================================================================

    citations: List[Dict[str, Any]] = field(default_factory=list)  # [{source, quote, page}, ...]
    inline_citations: List[str] = field(default_factory=list)  # Citation strings to embed

    # ============================================================================
    # SECTION 10: VISUALIZATION (Output from VisualizationAgent)
    # ============================================================================

    mindmap_data: Optional[Dict[str, Any]] = None  # Mind map JSON structure
    knowledge_graph_data: Optional[Dict[str, Any]] = None  # Knowledge graph JSON
    visualization_generated: bool = False

    # ============================================================================
    # SECTION 11: ERROR TRACKING & RECOVERY
    # ============================================================================

    errors: List[Dict[str, Any]] = field(default_factory=list)  # List of errors encountered
    recovery_attempts: int = 0  # Number of recovery attempts
    loop_detected: bool = False  # Infinite loop detection

    # ============================================================================
    # SECTION 12: EXECUTION TRACKING
    # ============================================================================

    execution_path: List[str] = field(default_factory=list)  # Nodes executed: ["intent", "decompose", "rewrite", ...]
    node_latencies: Dict[str, float] = field(default_factory=dict)  # Node name -> time in seconds
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # ============================================================================
    # SECTION 13: METADATA & CONFIGURATION
    # ============================================================================

    user_id: Optional[str] = None  # For multi-user scenarios
    session_id: Optional[str] = None  # Session tracking
    request_id: str = ""  # Unique request identifier
    tags: Dict[str, str] = field(default_factory=dict)  # Custom tags

    # ============================================================================
    # SECTION 14: FINAL OUTPUT
    # ============================================================================

    final_answer: Optional[str] = None  # Complete answer with citations embedded
    response_ready: bool = False  # Is response ready to send to user?

    # ============================================================================
    # METHODS
    # ============================================================================

    def add_error(self, node: str, error_msg: str, error_type: str = "execution"):
        """Log an error during execution."""
        self.errors.append({
            "node": node,
            "message": error_msg,
            "type": error_type,
            "timestamp": datetime.now().isoformat()
        })

    def record_node_execution(self, node_name: str, latency: float):
        """Record that a node executed and how long it took."""
        self.execution_path.append(node_name)
        self.node_latencies[node_name] = latency

    def should_skip_decomposition(self) -> bool:
        """Decide if decomposition should be skipped."""
        return self.question_complexity == "simple"

    def should_fallback_retrieve(self) -> bool:
        """Decide if fallback retrieval should be attempted."""
        return self.retrieval_confidence < 0.4 and not self.fallback_attempted

    def should_ask_human(self) -> bool:
        """Decide if human approval is needed."""
        return 0.3 < self.retrieval_confidence < 0.7

    def total_latency(self) -> float:
        """Total execution time in seconds."""
        if self.completed_at is None:
            return (datetime.now() - self.started_at).total_seconds()
        return (self.completed_at - self.started_at).total_seconds()
```

### State Access Patterns

**Agents read these fields:**
```python
# IntentAgent reads
- state.question
- state.conversation_history

# RetrieverAgent reads
- state.question (or state.optimized_question)
- state.should_decompose (to know if decomposition happened)

# GeneratorAgent reads
- state.question
- state.documents
- state.citations (if already extracted)

# CitationAgent reads
- state.generated_answer
- state.documents

# VisualizationAgent reads
- state.generated_answer
- state.documents
```

**Agents write these fields:**
```python
# IntentAgent writes
- state.question_complexity
- state.question_type
- state.question_priority
- state.intent_confidence
- state.enriched_query

# RetrieverAgent writes
- state.documents
- state.retrieval_confidence
- state.retrieval_scores
- state.retrieval_method

# GeneratorAgent writes
- state.generated_answer
- state.answer_confidence

# CitationAgent writes
- state.citations
- state.inline_citations

# VisualizationAgent writes
- state.mindmap_data
- state.knowledge_graph_data
- state.visualization_generated
```

---

## Graph Topology

### Node Definitions

#### 1. INTENT_AGENT Node
**Purpose**: Detect question complexity, type, and priority
**Input**: question, conversation_history
**Output**: question_complexity, question_type, question_priority, intent_confidence, enriched_query

**Logic**:
```
Analyze question:
  - Simple indicators: "What is", "Define", "How do I"
  - Complex indicators: "Compare", "Analyze", "Explain why"
  - Type: Factual (has single correct answer) vs Opinion vs Procedural vs Greeting
  - Priority: User language/urgency signals

Return:
  complexity: "simple" | "complex"
  type: "factual" | "opinion" | "procedural" | "greeting"
  confidence: 0.0-1.0
```

---

#### 2. CLASSIFY_COMPLEXITY Node (Decision Point)
**Purpose**: Route to decomposition or skip based on complexity
**Input**: question_complexity
**Output**: routing decision ("decompose" or "skip_decompose")

**Logic**:
```
if question_complexity == "simple":
    return "skip_decompose"
else:
    return "decompose"
```

---

#### 3. DECOMPOSE Node (Optional, Conditional)
**Purpose**: Break down complex questions into sub-questions
**Input**: enriched_query
**Output**: sub_questions, should_decompose=True

**Logic**:
```
Use LLM to decompose:
  "How should I analyze X vs Y?"
  → Sub-questions:
    1. What is X?
    2. What is Y?
    3. How do X and Y differ?
    4. What are pros/cons of each?
```

---

#### 4. REWRITE Node
**Purpose**: Optimize question for better retrieval
**Input**: question (or sub_questions if decomposed)
**Output**: optimized_question, search_keywords

**Logic**:
```
Transform question for retrieval:
  "What is an electric pump?"
  → "electric pump definition specifications uses types"

Extract keywords for hybrid search
```

---

#### 5. RETRIEVER_AGENT Node
**Purpose**: Retrieve documents using multiple strategies
**Input**: optimized_question, sub_questions (if any)
**Output**: documents, retrieval_confidence, retrieval_scores, retrieval_method

**Logic**:
```
1. BM25 search (keyword-based)
2. Vector search (semantic)
3. Combine and rerank
4. Calculate average confidence score
5. Return top-K documents with confidence
```

---

#### 6. CHECK_RETRIEVAL_CONFIDENCE Node (Decision Point)
**Purpose**: Decide next step based on retrieval quality
**Input**: retrieval_confidence
**Output**: routing decision ("generate" | "human_approval" | "fallback")

**Logic**:
```
if retrieval_confidence >= 0.7:
    return "generate"
elif retrieval_confidence >= 0.4:
    return "human_approval"
else:
    return "fallback"
```

---

#### 7. FALLBACK_RETRIEVE Node (Optional, Conditional)
**Purpose**: Use simpler retrieval strategy when confidence is low
**Input**: optimized_question, previous retrieval_scores
**Output**: fallback_documents, fallback_method, retrieval_confidence updated

**Logic**:
```
Strategy 1: Semantic search only (no reranking)
  - Search with just vector embeddings
  - Increase top-K (get 20 instead of 10)

Strategy 2: Broader search scope
  - Increase similarity threshold
  - Cast wider net for documents

Strategy 3: Clarification
  - Ask user: "Did you mean...?"
```

---

#### 8. HUMAN_APPROVAL Node (Optional, Conditional)
**Purpose**: Get user feedback for uncertain results
**Input**: documents, retrieval_confidence
**Output**: human_approved (True/False), human_feedback

**Logic**:
```
Present to user:
  "I found these documents but with low confidence. Continue?"

Wait for user response:
  - If approved: Continue to generation
  - If rejected: Ask for clarification or offer fallback
```

---

#### 9. GENERATOR_AGENT Node
**Purpose**: Generate answer from retrieved documents
**Input**: question, documents
**Output**: generated_answer, answer_confidence

**Logic**:
```
Use LLM prompt:
  "Answer the question using ONLY the provided documents.
   If not answerable, say so.
   Format: Answer + inline citations [Doc1, Page 2]"

Return:
  - Generated answer text
  - Confidence score (0.0-1.0)
```

---

#### 10. CITATION_AGENT Node
**Purpose**: Extract and format citations
**Input**: generated_answer, documents
**Output**: citations, inline_citations

**Logic**:
```
1. Parse inline citations from answer [Doc1, Page 2]
2. Map to actual source documents
3. Extract relevant quotes
4. Format as structured citations

Output:
  [{
    "source": "document_name.pdf",
    "page": 2,
    "quote": "...",
    "doc_id": "uuid"
  }, ...]
```

---

#### 11. VISUALIZATION_AGENT Node (Parallel, Optional)
**Purpose**: Generate mind map and knowledge graph
**Input**: generated_answer, documents
**Output**: mindmap_data, knowledge_graph_data

**Logic**:
```
Create mind map structure:
  Central node: Main topic
  Branches: Sub-topics from answer
  Leaves: Details and relationships

Create knowledge graph:
  Nodes: Key concepts
  Edges: Relationships between concepts
```

---

#### 12. FINAL_ASSEMBLY Node
**Purpose**: Combine all outputs for response
**Input**: generated_answer, citations, mindmap_data
**Output**: final_answer, response_ready

**Logic**:
```
Assemble response:
  - Answer with inline citations
  - Structured citation list
  - Mind map data
  - Metadata (confidence, sources, latency)
```

---

## Conditional Edge Routing

### Edge 1: INTENT_AGENT → DECOMPOSE or SKIP_DECOMPOSE

```python
def route_by_complexity(state: SharedState) -> str:
    """Route based on question complexity."""
    if state.question_complexity == "simple":
        return "skip_decompose"  # Go to REWRITE
    else:
        return "decompose"  # Go to DECOMPOSE


# In graph definition:
graph.add_conditional_edges(
    "classify_complexity",
    route_by_complexity,
    {
        "decompose": "decompose",
        "skip_decompose": "rewrite"
    }
)
```

### Edge 2: RETRIEVER_AGENT → GENERATE, HUMAN_APPROVAL, or FALLBACK

```python
def route_by_retrieval_confidence(state: SharedState) -> str:
    """Route based on retrieval confidence."""
    confidence = state.retrieval_confidence

    if confidence >= 0.7:
        return "generate"  # High confidence
    elif confidence >= 0.4:
        return "human_approval"  # Medium confidence
    else:
        return "fallback"  # Low confidence


# In graph definition:
graph.add_conditional_edges(
    "retriever",
    route_by_retrieval_confidence,
    {
        "generate": "generator",
        "human_approval": "human_approval",
        "fallback": "fallback_retrieve"
    }
)
```

### Edge 3: HUMAN_APPROVAL → GENERATOR or FALLBACK

```python
def route_by_human_approval(state: SharedState) -> str:
    """Route based on human approval response."""
    if state.human_approved is True:
        return "generate"
    elif state.human_approved is False:
        return "fallback"  # Ask for clarification
    else:
        return "ask_human"  # Still waiting for response


# In graph definition:
graph.add_conditional_edges(
    "human_approval",
    route_by_human_approval,
    {
        "generate": "generator",
        "fallback": "fallback_retrieve",
        "ask_human": "human_approval"  # Loop until response
    }
)
```

### Edge 4: GENERATOR_AGENT → CITATION & VISUALIZATION (Parallel)

```python
def route_to_post_generation(state: SharedState) -> List[str]:
    """Route to citation and visualization agents in parallel."""
    return ["citation", "visualization"]


# In graph definition (no conditional needed, always both):
graph.add_edge("generator", "citation")
graph.add_edge("generator", "visualization")
```

---

## Interaction Patterns (Sequence Diagrams)

### Pattern 1: Simple Question (Optimized Path)

```
User: "What is a pump?"
    ↓
[INTENT] → complexity="simple"
    ↓
[SKIP DECOMPOSE] (saves ~2-3 seconds!)
    ↓
[REWRITE] → "pump definition specifications types"
    ↓
[RETRIEVE] → finds 10 documents, confidence=0.85
    ↓ (confidence >= 0.7, so generate)
[GENERATOR] → "A pump is a device that..."
    ↓ (parallel)
[CITATION] + [VISUALIZATION]
    ↓
[FINAL_ASSEMBLY]
    ↓
Return: Answer + Citations + Mind Map

Total time: ~8-9 seconds (vs 11 seconds before)
```

---

### Pattern 2: Complex Question (Full Path)

```
User: "Compare electric pumps vs mechanical pumps"
    ↓
[INTENT] → complexity="complex"
    ↓
[DECOMPOSE] → [
    "What is an electric pump?",
    "What is a mechanical pump?",
    "How do they differ?",
    "What are pros/cons of each?"
  ]
    ↓
[REWRITE] → "electric pump mechanical pump comparison differences"
    ↓
[RETRIEVE] → finds 15 documents, confidence=0.72
    ↓ (confidence >= 0.7, so generate)
[GENERATOR] → Comprehensive comparison answer
    ↓ (parallel)
[CITATION] + [VISUALIZATION]
    ↓
[FINAL_ASSEMBLY]
    ↓
Return: Answer + Citations + Mind Map

Total time: ~12-13 seconds
```

---

### Pattern 3: Low Confidence Recovery (Fallback Path)

```
User: "What are rare pump configurations?"
    ↓
[INTENT] → complexity="complex"
    ↓
[DECOMPOSE] → [sub-questions]
    ↓
[REWRITE] → "rare pump configurations unusual designs"
    ↓
[RETRIEVE] → finds 2 documents, confidence=0.35
    ↓ (confidence < 0.4, so fallback)
[FALLBACK_RETRIEVE] → "broader scope, semantic only"
    ↓ finds 8 documents, confidence=0.55
    ↓ (still < 0.7, but better, proceed)
[GENERATOR] → "Based on limited information found..."
    ↓
[CITATION] + [VISUALIZATION]
    ↓
[FINAL_ASSEMBLY] → includes confidence warning
    ↓
Return: Answer + Warning + Citations

Total time: ~14-15 seconds (but more reliable!)
```

---

### Pattern 4: Human-in-Loop (Approval Path)

```
User: "How do I fix my pump?"
    ↓
[INTENT] → complexity="simple"
    ↓
[SKIP DECOMPOSE]
    ↓
[REWRITE] → "pump repair fix troubleshooting"
    ↓
[RETRIEVE] → finds 5 documents, confidence=0.55
    ↓ (0.4 <= confidence < 0.7, ask human)
[HUMAN_APPROVAL] → Present results to user:
    "Found 5 documents but with medium confidence.
     Would you like me to continue or search differently?"
    ↓
User approves OR asks for fallback
    ↓
[GENERATOR]
    ↓
[CITATION] + [VISUALIZATION]
    ↓
[FINAL_ASSEMBLY]
    ↓
Return: Answer + Citations

Total time: Variable (depends on user response)
```

---

## Configuration

### Graph Configuration YAML

```yaml
# config/langgraph_orchestrator.yaml

# Graph-level settings
graph:
  name: "KotaemomQAPipeline"
  description: "LangGraph orchestrator for parallel agent execution"

  # Loop detection
  loop_detection:
    enabled: true
    max_iterations: 10  # Prevent infinite loops
    iteration_timeout: 300  # 5 minutes per iteration

  # Timeout settings (in seconds)
  timeouts:
    total_execution: 120
    node_execution: 30
    human_approval_wait: 300  # 5 minutes to wait for user

# Node-level configurations
nodes:
  intent_agent:
    enabled: true
    timeout: 10
    parallel: false

  decompose:
    enabled: true
    timeout: 10
    skip_if: "simple"  # Skip if complexity == "simple"

  rewrite:
    enabled: true
    timeout: 5

  retriever_agent:
    enabled: true
    timeout: 15
    strategies:
      - name: "bm25"
        weight: 0.3
      - name: "vector"
        weight: 0.7
    top_k: 10

  fallback_retrieve:
    enabled: true
    timeout: 10
    strategies:
      - name: "semantic_only"
        top_k: 20
      - name: "broader_scope"
        top_k: 15

  generator_agent:
    enabled: true
    timeout: 20

  citation_agent:
    enabled: true
    timeout: 10

  visualization_agent:
    enabled: true
    timeout: 10
    parallel_with: "citation"  # Run in parallel with citation

# Confidence thresholds for routing
thresholds:
  high_confidence: 0.7
  medium_confidence: 0.4
  low_confidence: 0.0

# Error handling
error_handling:
  max_retries: 2
  retry_backoff: 1.5  # Exponential backoff multiplier
  fallback_on_error: true

# Monitoring
monitoring:
  log_level: "INFO"
  trace_enabled: true
  metrics_enabled: true

# Feature flags
features:
  human_in_loop: true
  fallback_retrieval: true
  loop_detection: true
  parallel_execution: true
```

---

## Error Handling

### Error Scenarios & Recovery

#### 1. **Retrieval Returns No Documents**

```python
# In RETRIEVER_AGENT node
if len(documents) == 0:
    state.add_error(
        node="retriever",
        error_msg="No documents found for query",
        error_type="retrieval_failure"
    )
    state.retrieval_confidence = 0.0

    # Automatically route to fallback
    return state
```

**Recovery**: FALLBACK_RETRIEVE with broader scope

---

#### 2. **LLM Generation Fails**

```python
# In GENERATOR_AGENT node
try:
    answer = llm.generate(documents)
except Exception as e:
    state.add_error(
        node="generator",
        error_msg=str(e),
        error_type="generation_failure"
    )

    if state.recovery_attempts < 2:
        state.recovery_attempts += 1
        # Retry with simpler prompt
        return state
    else:
        # Give up, return error message
        state.generated_answer = "Unable to generate answer at this time."
        return state
```

**Recovery**: Retry with simpler prompt, or return error message

---

#### 3. **Loop Detected**

```python
# After each node execution
def check_loop_detection(state: SharedState) -> bool:
    """Detect infinite loops."""
    if len(state.execution_path) > 10:
        # Same nodes being executed repeatedly
        last_5 = state.execution_path[-5:]
        if len(set(last_5)) < 2:  # Only 1-2 unique nodes in last 5 executions
            state.loop_detected = True
            state.add_error(
                node="orchestrator",
                error_msg="Loop detected in graph execution",
                error_type="loop_detection"
            )
            return True
    return False
```

**Recovery**: Exit graph, return error message with collected context

---

#### 4. **Human Approval Timeout**

```python
# In HUMAN_APPROVAL node
start_time = state.started_at
elapsed = datetime.now() - start_time

if elapsed > timedelta(minutes=5):
    state.add_error(
        node="human_approval",
        error_msg="Approval timeout (5 minutes)",
        error_type="timeout"
    )

    # Use fallback instead of waiting
    return {"needs_human_approval": False, "route": "fallback"}
```

**Recovery**: Fallback to automated retrieval, skip human approval

---

#### 5. **Node Execution Timeout**

```python
# In node wrapper
async def execute_node_with_timeout(node_func, state, timeout=30):
    try:
        result = await asyncio.wait_for(
            node_func(state),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        state.add_error(
            node="<node_name>",
            error_msg=f"Execution timeout ({timeout}s)",
            error_type="timeout"
        )
        # Return partial state or skip to next node
        return state
```

**Recovery**: Skip node or use cached result

---

## Implementation Notes

### Architecture Decisions

1. **State as Dataclass**
   - ✅ Type-safe, serializable
   - ✅ Clear field documentation
   - ⚠️ Large state object (14 sections)
   - ℹ️ Consider breaking into sub-states if >100 fields

2. **Conditional Edges**
   - ✅ Explicit routing logic
   - ✅ Easy to test and modify
   - ⚠️ Multiple conditional edges can get complex
   - ℹ️ Document all edge conditions clearly

3. **Node Naming Convention**
   - `{AGENT}_agent` for agent nodes (e.g., `retriever_agent`)
   - `{ACTION}` for action nodes (e.g., `rewrite`)
   - `check_{CONDITION}` for decision nodes (e.g., `check_retrieval_confidence`)

4. **Parallel Execution**
   - CITATION_AGENT and VISUALIZATION_AGENT can run in parallel
   - Use LangGraph's parallel edge support
   - Ensure no state conflicts

5. **Error Propagation**
   - Errors stored in `state.errors` list
   - Not thrown immediately (graph continues)
   - Final assembly checks for critical errors
   - Return error context to user if needed

---

### Key Implementation Decisions

1. **When to Call Kotaemon Components?**
   - Each agent node imports and calls the corresponding Kotaemon component
   - Example: `RetrieverAgent` node calls `DocumentRetrievalPipeline` from `kotaemon.indices`
   - Wrap results in state updates

2. **State Updates**
   - Each node returns a dict that updates state
   - Use field names exactly as in dataclass definition
   - Only update fields the node is responsible for

3. **Error Logging**
   - Use `state.add_error()` method for consistency
   - Include: node name, error message, error type, timestamp
   - Never throw exceptions (orchestrator continues)

4. **Latency Tracking**
   - Use `state.record_node_execution()` after each node
   - Calculate node latency before returning
   - Use for monitoring and optimization

5. **Testing**
   - Test each node independently (mock dependencies)
   - Test edge routing logic separately
   - Test full graph with different state variations

---

## Testing Strategy

### Unit Tests (per-node testing)

```python
# test_langgraph_nodes.py

def test_intent_agent_simple_question():
    """Test intent agent correctly identifies simple questions."""
    state = SharedState(question="What is X?")
    result = intent_agent(state)
    assert result["question_complexity"] == "simple"
    assert result["intent_confidence"] > 0.7

def test_intent_agent_complex_question():
    """Test intent agent correctly identifies complex questions."""
    state = SharedState(question="Compare X vs Y")
    result = intent_agent(state)
    assert result["question_complexity"] == "complex"

def test_retriever_agent_confidence_calculation():
    """Test retriever confidence score calculation."""
    state = SharedState(question="What is pump?")
    result = retriever_agent(state)
    assert "retrieval_confidence" in result
    assert 0.0 <= result["retrieval_confidence"] <= 1.0
    assert len(result["documents"]) > 0

def test_generator_agent_with_documents():
    """Test generator creates answer from documents."""
    state = SharedState(
        question="What is pump?",
        documents=[mock_doc1, mock_doc2]
    )
    result = generator_agent(state)
    assert "generated_answer" in result
    assert len(result["generated_answer"]) > 0
```

---

### Integration Tests (graph routing)

```python
# test_langgraph_routing.py

def test_simple_question_skips_decomposition():
    """Test that simple questions skip decomposition."""
    graph = build_langgraph()
    state = SharedState(question="What is X?")

    # Run graph
    final_state = graph.invoke(state)

    # Check decomposition was skipped
    assert "decompose" not in final_state.execution_path
    assert "rewrite" in final_state.execution_path

def test_low_confidence_triggers_fallback():
    """Test that low confidence triggers fallback retrieval."""
    graph = build_langgraph()
    state = SharedState(question="Obscure technical question")

    # Mock retriever to return low confidence
    with patch('retriever_agent') as mock_retriever:
        mock_retriever.return_value = {
            "documents": [mock_doc],
            "retrieval_confidence": 0.3
        }

        final_state = graph.invoke(state)

        # Check fallback was triggered
        assert final_state.fallback_attempted == True
        assert "fallback_retrieve" in final_state.execution_path

def test_end_to_end_simple_flow():
    """Test complete flow for simple question."""
    graph = build_langgraph()
    state = SharedState(
        question="What is a pump?",
        conversation_id="test-123"
    )

    final_state = graph.invoke(state)

    # Verify all expected outputs
    assert final_state.generated_answer is not None
    assert len(final_state.citations) > 0
    assert final_state.response_ready == True
    assert final_state.total_latency() < 30  # Should complete in <30 seconds
```

---

### Performance Tests

```python
# test_langgraph_performance.py

def test_simple_question_latency():
    """Test that simple questions complete in <10 seconds."""
    graph = build_langgraph()
    state = SharedState(question="What is pump?")

    start = time.time()
    final_state = graph.invoke(state)
    elapsed = time.time() - start

    assert elapsed < 10, f"Expected <10s, got {elapsed}s"
    assert final_state.generated_answer is not None

def test_complex_question_latency():
    """Test that complex questions complete in <20 seconds."""
    graph = build_langgraph()
    state = SharedState(question="Compare X vs Y vs Z")

    start = time.time()
    final_state = graph.invoke(state)
    elapsed = time.time() - start

    assert elapsed < 20, f"Expected <20s, got {elapsed}s"
    assert final_state.decompose == True

def test_parallel_agent_speedup():
    """Test that parallel execution is faster than sequential."""
    # Run with parallel enabled
    graph_parallel = build_langgraph(parallel=True)

    # Run with parallel disabled
    graph_sequential = build_langgraph(parallel=False)

    state = SharedState(question="What is pump?")

    start = time.time()
    final_state_parallel = graph_parallel.invoke(state)
    parallel_time = time.time() - start

    start = time.time()
    final_state_sequential = graph_sequential.invoke(state)
    sequential_time = time.time() - start

    # Parallel should be faster
    assert parallel_time < sequential_time
```

---

### Chaos Tests (failure scenarios)

```python
# test_langgraph_chaos.py

def test_retriever_failure_triggers_fallback():
    """Test that retriever failure triggers fallback."""
    graph = build_langgraph()
    state = SharedState(question="What is pump?")

    with patch('retriever_agent') as mock:
        mock.side_effect = Exception("Retrieval failed")

        # Should not crash, should handle gracefully
        final_state = graph.invoke(state)

        assert len(final_state.errors) > 0
        assert final_state.fallback_attempted == True

def test_generator_failure_returns_error():
    """Test that generator failure returns error message."""
    graph = build_langgraph()
    state = SharedState(
        question="What is pump?",
        documents=[mock_doc]
    )

    with patch('generator_agent') as mock:
        mock.side_effect = Exception("LLM unavailable")

        final_state = graph.invoke(state)

        assert "Unable to generate" in final_state.generated_answer
        assert final_state.response_ready == False

def test_loop_detection_prevents_infinite_loop():
    """Test that infinite loops are detected and stopped."""
    # Create a state that would cause infinite loop
    state = SharedState(question="Test")

    # Somehow trigger a loop condition
    # (In real implementation, this would be hard to test)
    # For now, verify loop detection logic

    assert state.loop_detected == False
    # Simulate loop
    for i in range(15):
        state.execution_path.append("same_node")

    # Would need orchestrator to check this
```

---

## Implementation Checklist

- [ ] Define `SharedState` dataclass with all 14 sections
- [ ] Implement 12 node functions (intent, decompose, rewrite, retriever, generator, citation, visualization, etc.)
- [ ] Implement 4 conditional edge functions (routing logic)
- [ ] Build LangGraph with `StateGraph(SharedState)`
- [ ] Add all nodes with `graph.add_node()`
- [ ] Add all edges with `graph.add_edge()`
- [ ] Add conditional edges with `graph.add_conditional_edges()`
- [ ] Implement error handling in each node
- [ ] Implement latency tracking with `state.record_node_execution()`
- [ ] Create wrapper around Kotaemon components
- [ ] Write unit tests for each node
- [ ] Write integration tests for routing
- [ ] Write performance tests for latency
- [ ] Write chaos tests for error scenarios
- [ ] Create configuration YAML file
- [ ] Document all interfaces and data contracts

---

## Summary

This design document provides:

✅ **Clear architecture** with 12 nodes and 4 conditional edges
✅ **Complete state schema** with 14 sections
✅ **Decision logic** for routing (complexity, confidence, approval)
✅ **4 interaction patterns** (simple, complex, fallback, human-in-loop)
✅ **Error handling** for 5 failure scenarios
✅ **Testing strategy** with unit, integration, performance, and chaos tests

**Next Steps**:
1. Review this design
2. Proceed to implementation of node functions
3. Create the graph definition
4. Run tests to validate
5. Proceed to Phase 3 (MCP) and Phase 4 (A2A) design

---

**Last Updated**: November 17, 2025
**Status**: Ready for Implementation Review
