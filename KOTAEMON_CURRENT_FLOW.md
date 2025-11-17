# Kotaemon Current Architecture & Flow

## Current Kotaemon Flow (Without LangGraph)

Based on the codebase structure, here's how it works:

```
USER ASKS QUESTION
        ↓
┌─────────────────────────────────────────────────────────┐
│ File Collection (ktem/index/file/)                      │
├─────────────────────────────────────────────────────────┤
│ 1. Upload Files (TXT, PDF, DOCX, etc.)                 │
│    ↓                                                     │
│ 2. Load Files → Extract Text                           │
│    ↓                                                     │
│ 3. BATCH CHUNK (NEW - what we just added!)             │
│    ├─ PHASE 1: Load all files (collect docs)           │
│    ├─ PHASE 2: Batch LLM chunking (parallel)           │
│    └─ PHASE 3: Group by file_id & index                │
│    ↓                                                     │
│ 4. Store in Document Store & Vector Store              │
│    ↓                                                     │
│ 5. Generate Embeddings                                  │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│ Reasoning Pipeline (ktem/reasoning/simple.py)           │
├─────────────────────────────────────────────────────────┤
│ Sequential Steps (NO CONDITIONAL ROUTING):              │
│                                                          │
│ 1. ADD QUERY CONTEXT                                    │
│    ├─ Takes user question                              │
│    ├─ Adds conversation history (last 5 interactions)  │
│    └─ Returns enriched query                            │
│         ↓                                                │
│ 2. DECOMPOSE QUESTION                                  │
│    ├─ Breaks down complex questions                    │
│    ├─ Creates sub-questions if needed                  │
│    └─ Returns decomposed questions                      │
│         ↓                                                │
│ 3. REWRITE QUESTION                                    │
│    ├─ Optimizes question for retrieval                 │
│    └─ Returns rephrased question                        │
│         ↓                                                │
│ 4. RETRIEVE DOCUMENTS                                  │
│    ├─ Vector search in Document Store                  │
│    ├─ Reranking (Cohere reranker)                      │
│    ├─ Top-K retrieval                                  │
│    └─ Returns relevant documents                        │
│         ↓                                                │
│ 5. GENERATE ANSWER                                     │
│    ├─ Takes question + retrieved documents             │
│    ├─ LLM generates answer with citations              │
│    ├─ Inline citation format                           │
│    └─ Returns answer text                               │
│         ↓                                                │
│ 6. CREATE CITATIONS                                    │
│    ├─ Extracts citations from answer                   │
│    ├─ Maps to source documents                         │
│    └─ Returns formatted citations                       │
│         ↓                                                │
│ 7. VISUALIZE (Mind Map)                                │
│    ├─ Creates knowledge graph visualization            │
│    ├─ Shows relationships between concepts             │
│    └─ Returns Plotly JSON visualization                │
│         ↓                                                │
│ RETURN FINAL RESPONSE                                   │
│ ├─ Answer text                                          │
│ ├─ Citations (documents + quotes)                       │
│ ├─ Mind map visualization                              │
│ └─ Conversation history updated                         │
└─────────────────────────────────────────────────────────┘
        ↓
DISPLAY TO USER
```

---

## Current Components & Their Roles

### **INDEXING PHASE** (File Collection)

```
File Upload
    ↓
Load & Extract Text
    ↓
Token Splitting (TokenSplitter) OR LLM Chunking (NEW!)
    ↓
Create Embeddings (e5-small)
    ↓
Store in:
├─ Document Store (LanceDB)
├─ Vector Store (Chroma)
└─ Metadata DB (SQLAlchemy)
```

**Files Involved:**
- `libs/ktem/ktem/index/file/pipelines.py` - Main indexing pipeline
- `libs/ktem/ktem/index/file/ui.py` - File upload UI
- `libs/kotaemon/kotaemon/indices/splitters/llm_chunker.py` - LLM-based chunking (NEW)
- `libs/kotaemon/kotaemon/storages/vectorstores/chroma.py` - Vector store
- `libs/kotaemon/kotaemon/storages/docstores/lancedb.py` - Document store

**Key Features:**
- Supports multiple file types: TXT, PDF, DOCX, XLSX, HTML
- Batch document processing with parallel LLM chunking
- Phase 1: Load all files (metadata + docs)
- Phase 2: Batch chunk with parallel ThreadPoolExecutor
- Phase 3: Group chunks by file_id and index
- Performance: ~50-70 seconds for 10 files (vs 400+ seconds sequential)

---

### **RETRIEVAL PHASE** (Reasoning)

```
User Question + History
    ↓
Add Context (from conversation history)
    ↓
Decompose (if complex)
    ↓
Rewrite (optimize for retrieval)
    ↓
Vector Search + Reranking
    ↓
Top-K documents retrieved
```

**Files Involved:**
- `libs/ktem/ktem/reasoning/simple.py` - Main reasoning pipeline
- `libs/kotaemon/kotaemon/indices/retriever/bm25.py` - BM25 retriever
- `libs/kotaemon/kotaemon/indices/rankings/cohere.py` - Cohere reranker
- `libs/kotaemon/kotaemon/llms/manager.py` - LLM management

**Key Components:**
1. **AddQueryContextPipeline** - Adds conversation history (last 5 interactions)
2. **DecomposeQuestionPipeline** - Breaks complex questions into sub-questions
3. **RewriteQuestionPipeline** - Optimizes questions for better retrieval
4. **DocumentRetrievalPipeline** - Hybrid search (BM25 + Vector)
5. **CohereReranking** - Reranks documents by relevance (top-K)

**Performance:** ~2-3 seconds for retrieval

---

### **GENERATION PHASE** (Reasoning)

```
Question + Retrieved Documents
    ↓
LLM (gpt-5-mini or configurable)
    ↓
Generate Answer with Citations
    ↓
Extract & Format Citations
    ↓
Create Mind Map
    ↓
Return Response
```

**Files Involved:**
- `libs/kotaemon/kotaemon/indices/qa/citation_qa.py` - Citation-aware QA
- `libs/kotaemon/kotaemon/indices/qa/citation_qa_inline.py` - Inline citations
- `libs/ktem/ktem/utils/visualize_cited.py` - Mind map creation
- `libs/ktem/ktem/pages/chat/__init__.py` - Chat interface

**Key Components:**
1. **AnswerWithContextPipeline** - LLM-based answer generation
2. **AnswerWithInlineCitation** - Extracts inline citations
3. **PrepareEvidencePipeline** - Formats evidence for display
4. **CreateCitationVizPipeline** - Generates mind map visualization

**Performance:** ~5-10 seconds (depends on LLM latency + response length)

---

## Current Limitations (Sequential Processing)

1. ❌ **No Conditional Routing** - All steps always execute, even if not needed
   - Simple questions still go through decomposition
   - Visualization always generated even if not requested

2. ❌ **No State Persistence** - Context lost between steps
   - Each step is independent
   - No shared state across pipeline

3. ❌ **No Error Recovery** - One failure = entire flow breaks
   - No fallbacks if retrieval fails
   - No retry logic

4. ❌ **No Loop Detection** - Can get stuck in infinite loops
   - No monitoring of step iterations

5. ❌ **No Human-in-the-Loop** - Fully automated, no approval points
   - Can't ask user for clarification
   - No way to review before generating

6. ❌ **Fixed Workflow** - Can't skip steps or take alternate paths
   - All documents always retrieved
   - All answers always generated

7. ❌ **No Monitoring** - Hard to see what's happening in each step
   - No visibility into execution state
   - Difficult to debug issues

---

## Example: Current Flow for "What are pump specifications?"

```
1. ADD CONTEXT: "What are pump specifications?" + history
   ↓ (Always executes)
2. DECOMPOSE: [Same question - no decomposition needed]
   ↓ (Wastes LLM call)
3. REWRITE: "pump specifications features types"
   ↓
4. RETRIEVE: Search for "pump specifications" → 10 documents
   ↓
5. GENERATE: Create answer from documents
   ↓
6. CITE: Extract citations (Document 1, page 2, etc.)
   ↓
7. VISUALIZE: Create mind map (Pump → Types → Specs → Features)
   ↓ (Always executes)
8. RETURN: Answer + Citations + Mind Map
```

**Total Time:** ~10-15 seconds
**Cost:** Multiple LLM calls (context + decompose + rewrite + generate)

---

## Current Stack Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **File Loading** | DirectoryReader | Load files from disk |
| **Chunking** | LLMBasedChunker (Azure OpenAI) | Semantic chunking with LLM |
| **Embeddings** | e5-small | Generate embeddings |
| **Document Store** | LanceDB | Store raw documents |
| **Vector Store** | Chroma | Store embeddings for search |
| **Retrieval** | BM25 + Vector Search | Hybrid search |
| **Reranking** | Cohere Reranker | Rank results by relevance |
| **LLM** | gpt-5-mini (Azure OpenAI) | Generate answers |
| **Visualization** | Plotly | Mind map generation |
| **Chat Interface** | Gradio | Web UI |

---

## Recent Improvements (This Session)

### ✅ LLM Chunking Implementation
- Added `llm_chunker.py` - Window-based semantic chunking
- Uses Azure OpenAI (gpt-5-mini) for intelligent chunking
- Parallel ThreadPoolExecutor for window extraction
- Temperature=1.0 support for consistent results

### ✅ Batch Document Processing
- PHASE 1: Load all files and collect documents
- PHASE 2: Batch chunk with parallel LLM (10x faster!)
- PHASE 3: Group chunks by file_id and index
- **Performance Improvement**: 950+ seconds → 50-70 seconds for 10 files

---

**Last Updated**: November 17, 2025
