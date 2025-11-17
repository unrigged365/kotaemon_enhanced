# Kotaemon LangGraph Minimal Integration

## Overview
Add only 3 LangGraph features to improve the current reasoning pipeline:
1. **Conditional Routing** - Skip unnecessary steps (decomposition if simple question)
2. **Error Recovery** - Fallback to simpler retrieval if no results
3. **State Management** - Persist context across all steps

---

## Feature 1: Conditional Routing

### Current Behavior (Wasteful)
```
Simple Question: "What is X?"
    ↓
ADD CONTEXT
    ↓
DECOMPOSE (UNNECESSARY - wastes LLM call!)
    ↓
REWRITE
    ↓
RETRIEVE
    ↓
GENERATE
```

### With LangGraph (Optimized)
```
Question: "What is X?"
    ↓
CLASSIFY_COMPLEXITY
    ↓ (Conditional Edge)
    ├─ Simple → SKIP decompose, go directly to REWRITE
    └─ Complex → DECOMPOSE (then REWRITE)
    ↓
REWRITE
    ↓
RETRIEVE
    ↓
GENERATE
```

### Decision Function
```python
def should_decompose(state: ReasoningState) -> str:
    """Decides if question needs decomposition.

    Returns:
        "simple" - Skip decomposition
        "complex" - Perform decomposition
    """
    question = state["question"]
    complexity = state["complexity"]  # Set by previous node

    if complexity == "simple":
        logger.info("---SIMPLE QUESTION: SKIP DECOMPOSITION---")
        return "simple"
    else:
        logger.info("---COMPLEX QUESTION: DECOMPOSE---")
        return "complex"
```

**Savings**: Skips 1 LLM call for simple questions (~2-3 seconds per query)

---

## Feature 2: Error Recovery

### Current Behavior (Fragile)
```
RETRIEVE Documents
    ↓
No results found? → ERROR, FAIL
    (User sees "No information found")
```

### With LangGraph (Resilient)
```
RETRIEVE Documents (Hybrid Search)
    ↓ (Conditional Edge: Check Results)
    ├─ Results Found (confidence > threshold)
    │   ↓
    │   GENERATE Answer
    │
    └─ No Results / Low Confidence
        ↓
        FALLBACK_RETRIEVE (Simpler Search)
        ├─ Try semantic search only (no reranking)
        ├─ Broaden search scope
        ├─ Return all related documents
        ↓
        GENERATE Answer (with confidence warning)
```

### Decision Function
```python
def should_generate_or_fallback(state: ReasoningState) -> str:
    """Decides if we have enough docs or need to fallback.

    Returns:
        "generate" - Have good results, proceed to answer
        "fallback" - Low confidence, try simpler retrieval
        "no_answer" - Still nothing found, admit defeat
    """
    documents = state["sources"]
    confidence_scores = state["retrieval_confidence"]

    if not documents:
        logger.info("---NO DOCUMENTS: TRYING FALLBACK---")
        return "fallback"

    avg_confidence = sum(confidence_scores) / len(confidence_scores)

    if avg_confidence < 0.3:  # Low confidence threshold
        logger.info(f"---LOW CONFIDENCE ({avg_confidence:.2f}): FALLBACK---")
        return "fallback"

    logger.info(f"---GOOD RESULTS (confidence: {avg_confidence:.2f}): GENERATE---")
    return "generate"

def fallback_retrieve(state: ReasoningState) -> dict:
    """Fallback retrieval with simpler strategy.

    Strategy:
    1. Use only semantic search (no reranking)
    2. Increase top-K (get more documents)
    3. Lower similarity threshold
    """
    question = state["question"]

    # Use simple vector search without reranking
    docs = vector_store.search(question, k=20)  # Get 20 instead of 10

    return {
        "sources": docs,
        "retrieval_confidence": [0.5] * len(docs),  # Mark as fallback
        "retrieval_method": "fallback_simple_search"
    }
```

**Savings**: Better user experience, fewer "No answer" failures

---

## Feature 3: State Management

### Current Behavior (Stateless)
```
Step 1: Add Context
    ├─ Input: question
    └─ Output: enriched_query
    ✗ Context not saved

Step 2: Decompose
    ├─ Input: enriched_query
    └─ Output: sub_questions
    ✗ enriched_query lost

Step 3: Rewrite
    ├─ Input: sub_questions
    └─ Output: optimized_question
    ✗ Original question lost

... (context lost at each step)
```

### With LangGraph (Persistent State)
```
ReasoningState = {
    "original_question": "What is X?",
    "enriched_query": "What is X? [with history]",
    "sub_questions": ["Is X important?", "What are X's properties?"],
    "optimized_question": "X definition properties uses",
    "sources": [Document1, Document2, ...],
    "answer": "X is...",
    "citations": [...],
    "metadata": {
        "question_complexity": "simple",
        "retrieval_method": "hybrid_search",
        "retrieval_confidence": 0.85,
        "generation_latency": 3.2,
        "total_documents_retrieved": 10
    }
}
```

### Benefits
1. **Debugging** - See full context at any point
2. **Tracing** - Understand what happened in each step
3. **Optimization** - Track performance metrics
4. **Recovery** - Retry with previous state if error occurs
5. **Monitoring** - Log all state transitions

---

## Complete Flow with All 3 Features

```
START
    ↓
ADD_CONTEXT
├─ Input: question, history
├─ Output: enriched_query, conversation_context
└─ State: Store original_question, enriched_query
    ↓
CLASSIFY_COMPLEXITY (NEW!)
├─ Analyze if question is simple or complex
└─ State: Store question_complexity
    ↓ (CONDITIONAL EDGE #1)
    ├─ Simple → SKIP to REWRITE
    └─ Complex → DECOMPOSE
    ↓
DECOMPOSE (Optional)
├─ Input: enriched_query
├─ Output: sub_questions
└─ State: Store sub_questions
    ↓
REWRITE
├─ Input: question (or sub_questions)
├─ Output: optimized_question
└─ State: Store optimized_question
    ↓
RETRIEVE
├─ Input: optimized_question
├─ Output: documents with confidence scores
└─ State: Store sources, retrieval_confidence, retrieval_method
    ↓ (CONDITIONAL EDGE #2)
    ├─ Good Results → GENERATE
    ├─ Low Confidence → FALLBACK_RETRIEVE
    └─ No Results → NO_ANSWER
    ↓
FALLBACK_RETRIEVE (Optional, NEW!)
├─ Input: optimized_question
├─ Output: documents (simpler search)
└─ State: Update sources, mark retrieval_method="fallback"
    ↓
GENERATE
├─ Input: question, sources
├─ Output: answer with citations
└─ State: Store answer, citations, generation_metadata
    ↓
RETURN_RESPONSE
├─ State: Final state with all context
└─ Metadata: Track total latency, cost, effectiveness
    ↓
END
```

---

## Implementation Structure

### File: `libs/ktem/ktem/reasoning/langgraph_schema.py` (NEW)
```python
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from langgraph.graph.state import StateGraph

@dataclass
class ReasoningState:
    """Persistent state across reasoning steps."""

    # Input
    question: str
    history: List[Dict] = field(default_factory=list)

    # Context
    enriched_query: Optional[str] = None
    conversation_context: Optional[str] = None

    # Complexity Analysis
    question_complexity: Optional[str] = None  # "simple" or "complex"

    # Decomposition (optional)
    sub_questions: List[str] = field(default_factory=list)

    # Question Optimization
    optimized_question: Optional[str] = None

    # Retrieval
    sources: List[Document] = field(default_factory=list)
    retrieval_confidence: List[float] = field(default_factory=list)
    retrieval_method: str = "hybrid_search"  # or "fallback_simple_search"

    # Generation
    answer: Optional[str] = None
    citations: List[Dict] = field(default_factory=list)

    # Metadata for monitoring
    metadata: Dict = field(default_factory=dict)
```

### File: `libs/ktem/ktem/reasoning/langgraph_edges.py` (NEW)
```python
from langgraph.graph.state import StateGraph
from typing import Literal

def should_decompose(state: ReasoningState) -> Literal["simple", "complex"]:
    """Decide if decomposition is needed."""
    if state["question_complexity"] == "simple":
        return "simple"
    return "complex"

def should_generate_or_fallback(state: ReasoningState) -> Literal["generate", "fallback", "no_answer"]:
    """Decide if we have enough docs or need to fallback."""
    if not state["sources"]:
        return "fallback"

    avg_confidence = sum(state["retrieval_confidence"]) / len(state["retrieval_confidence"])

    if avg_confidence < 0.3:
        return "fallback"

    return "generate"
```

### File: `libs/ktem/ktem/reasoning/langgraph_graph.py` (NEW)
```python
from langgraph.graph import StateGraph, START, END
from ktem.reasoning.langgraph_schema import ReasoningState
from ktem.reasoning.langgraph_edges import should_decompose, should_generate_or_fallback
from ktem.reasoning.langgraph_nodes import (
    add_context,
    classify_complexity,
    decompose_question,
    rewrite_question,
    retrieve_documents,
    fallback_retrieve,
    generate_answer,
    no_answer,
)

def build_reasoning_graph():
    """Build the LangGraph reasoning graph."""

    graph = StateGraph(ReasoningState)

    # Add nodes
    graph.add_node("add_context", add_context)
    graph.add_node("classify_complexity", classify_complexity)
    graph.add_node("decompose", decompose_question)
    graph.add_node("rewrite", rewrite_question)
    graph.add_node("retrieve", retrieve_documents)
    graph.add_node("fallback_retrieve", fallback_retrieve)
    graph.add_node("generate", generate_answer)
    graph.add_node("no_answer", no_answer)

    # Add edges
    graph.add_edge(START, "add_context")
    graph.add_edge("add_context", "classify_complexity")

    # Conditional edge #1: Should decompose?
    graph.add_conditional_edges(
        "classify_complexity",
        should_decompose,
        {
            "simple": "rewrite",
            "complex": "decompose"
        }
    )
    graph.add_edge("decompose", "rewrite")
    graph.add_edge("rewrite", "retrieve")

    # Conditional edge #2: Should generate or fallback?
    graph.add_conditional_edges(
        "retrieve",
        should_generate_or_fallback,
        {
            "generate": "generate",
            "fallback": "fallback_retrieve",
            "no_answer": "no_answer"
        }
    )
    graph.add_edge("fallback_retrieve", "generate")

    # End edges
    graph.add_edge("generate", END)
    graph.add_edge("no_answer", END)

    return graph.compile()
```

---

## Integration with Existing Kotaemon

### Current Code (In simple.py)
```python
class FullQAPipeline(BaseReasoning):
    def stream(self, question, conversation_id, chat_history):
        # Current sequential code...
```

### After LangGraph Integration
```python
class FullQAPipeline(BaseReasoning):
    def __init__(self):
        self.graph = build_reasoning_graph()  # LangGraph
        # ... rest of init

    def stream(self, question, conversation_id, chat_history):
        # Create initial state
        state = ReasoningState(
            question=question,
            history=chat_history
        )

        # Run through LangGraph
        for event in self.graph.stream(state, stream_mode="updates"):
            for node, output in event.items():
                # Yield outputs to user as they stream
                yield self._format_output(node, output)

        # Final state has all context
        final_state = output
        return final_state
```

---

## Performance Impact

### Before (Current Sequential)
```
Simple Question:
├─ Add Context: 0.5s
├─ Decompose: 2.5s  ← WASTED (unnecessary)
├─ Rewrite: 1.0s
├─ Retrieve: 2.0s
├─ Generate: 5.0s
└─ Total: 11s
```

### After (With LangGraph)
```
Simple Question:
├─ Add Context: 0.5s
├─ Classify: 0.5s
├─ Rewrite: 1.0s  (decompose skipped!)
├─ Retrieve: 2.0s
├─ Generate: 5.0s
└─ Total: 9s  ← 2 seconds faster (18% improvement)

Complex Question (with fallback):
├─ Add Context: 0.5s
├─ Classify: 0.5s
├─ Decompose: 2.5s
├─ Rewrite: 1.0s
├─ Retrieve (0 results): 2.0s
├─ Fallback Retrieve: 1.5s
├─ Generate: 5.0s
└─ Total: 12.5s (but more reliable!)
```

---

## Benefits Summary

| Feature | Benefit | Implementation |
|---------|---------|-----------------|
| **Conditional Routing** | Skip decomposition for simple questions | `should_decompose()` edge function |
| **Error Recovery** | Fallback to simpler retrieval if nothing found | `should_generate_or_fallback()` edge function |
| **State Management** | Persist context across steps for debugging & recovery | `ReasoningState` dataclass |

---

## Next Steps

1. Create `langgraph_schema.py` - Define ReasoningState
2. Create `langgraph_edges.py` - Define decision functions
3. Create `langgraph_nodes.py` - Adapt existing nodes to work with state
4. Create `langgraph_graph.py` - Build the graph
5. Update `simple.py` - Integrate LangGraph into FullQAPipeline
6. Test with sample questions (simple and complex)

---

**Minimal, focused, practical. Ready to code?**
