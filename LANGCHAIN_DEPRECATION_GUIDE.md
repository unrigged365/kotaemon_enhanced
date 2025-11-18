# LangChain Deprecation & Migration Guide

**Last Updated:** November 18, 2025  
**Repository:** kotaemon_enhanced  
**Current LangChain Version Support:** v0.1.16 - v0.2.16 (with deprecation warnings)  
**Recommended Target Version:** v1.0.7+

---

## Table of Contents

1. [Overview](#overview)
2. [All Unique LangChain Imports in Project](#all-unique-langchain-imports-in-project)
3. [Deprecated & Modified Imports](#deprecated--modified-imports)
4. [Detailed Migration Guide](#detailed-migration-guide)
5. [Breaking Changes in v1.0](#breaking-changes-in-v10)
6. [Migration Checklist](#migration-checklist)
7. [Quick Reference](#quick-reference)

---

## Overview

This project uses **LangChain extensively** across multiple components:
- **Chat Models** (OpenAI, Azure, Anthropic, Google, Cohere, Ollama)
- **Completion Models** (OpenAI, Azure, LlamaCpp)
- **Embeddings** (OpenAI, Azure, Cohere, HuggingFace, Google, Mistral)
- **Agents & Tools** (ReAct, ReWOO patterns)
- **Text Splitters** (for semantic chunking)
- **Output Parsers** (for structured outputs)
- **Message Schema** (AIMessage, HumanMessage, SystemMessage)

**Current Status:** Many imports are deprecated in v0.2+ but still functional. Upgrading to v1.0+ requires significant refactoring.

---

## All Unique LangChain Imports in Project

### Direct Imports (langchain)
```python
from langchain.agents import AgentType as LCAgentType
from langchain.agents import Tool as LCTool
from langchain.agents import initialize_agent
from langchain.agents.agent import AgentExecutor as LCAgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain.chat_models import AzureChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.embeddings import AzureOpenAIEmbeddings
from langchain.embeddings import CohereEmbeddings
from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain.llms import OpenAI
from langchain.llms import AzureOpenAI
from langchain.llms import LlamaCpp
from langchain.output_parsers.boolean import BooleanOutputParser
from langchain.schema import Document as LangchainDocument
from langchain.schema.messages import AIMessage as LCAIMessage
from langchain.schema.messages import HumanMessage as LCHumanMessage
from langchain.schema.messages import SystemMessage as LCSystemMessage
from langchain.text_splitter import CharacterTextSplitter
from langchain.utils import get_from_dict_or_env
```

### LangChain Core (langchain_core)
```python
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate as LCPromptTemplate
```

### LangChain OpenAI (langchain_openai)
```python
from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_openai import AzureOpenAIEmbeddings
from langchain_openai import OpenAI
from langchain_openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI
```

### LangChain Community (langchain_community)
```python
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.llms import LlamaCpp
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.utilities import SerpAPIWrapper
```

### LangChain Anthropic (langchain_anthropic)
```python
from langchain_anthropic import ChatAnthropic
```

### LangChain Google GenAI (langchain_google_genai)
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
```

### LangChain Cohere (langchain_cohere)
```python
from langchain_cohere import ChatCohere
from langchain_cohere import CohereEmbeddings
```

### LangChain Ollama (langchain_ollama)
```python
from langchain_ollama import ChatOllama
```

### LangChain Mistral AI (langchain_mistralai)
```python
from langchain_mistralai import MistralAIEmbeddings
```

---

## Deprecated & Modified Imports

### Status Legend
- ✅ **Modern** - Current best practice (v1.0+)
- ⚠️ **Deprecated** - Still works but discouraged (v0.2+)
- ❌ **Removed** - No longer available (v1.0+)
- 🔴 **Critical** - Breaking changes in v1.0

---

### 1. Message Schema (🔴 CRITICAL)

| Deprecated | Modern | Package | Version | Status |
|-----------|--------|---------|---------|--------|
| ❌ `from langchain.schema.messages import AIMessage` | ✅ `from langchain.messages import AIMessage` | langchain_core | v0.2+ | Re-exported via langchain.messages |
| ❌ `from langchain.schema.messages import HumanMessage` | ✅ `from langchain.messages import HumanMessage` | langchain_core | v0.2+ | Re-exported via langchain.messages |
| ❌ `from langchain.schema.messages import SystemMessage` | ✅ `from langchain.messages import SystemMessage` | langchain_core | v0.2+ | Re-exported via langchain.messages |
| ⚠️ `AIMessage(example=...)` parameter | ✅ `AIMessage(additional_kwargs=...)` | - | v1.0 | **REMOVED** - Parameter completely gone |
| ⚠️ `message.text()` method | ✅ `message.text` property | - | v1.0 | **Method changed to property** |

**Migration Example:**
```python
# ❌ OLD (v0.x)
from langchain.schema.messages import AIMessage, HumanMessage
msg = AIMessage(content="Hello", example=True)
text = msg.text()

# ✅ NEW (v1.0+)
from langchain.messages import AIMessage, HumanMessage
msg = AIMessage(content="Hello", additional_kwargs={"example": True})
text = msg.text  # Now a property, not a method
```

---

### 2. Chat Models (🔴 CRITICAL)

| Deprecated | Modern | Package | Version |
|-----------|--------|---------|---------|
| ❌ `from langchain.chat_models import ChatOpenAI` | ✅ `from langchain_openai import ChatOpenAI` | langchain-openai | v0.2+ |
| ❌ `from langchain.chat_models import AzureChatOpenAI` | ✅ `from langchain_openai import AzureChatOpenAI` | langchain-openai | v0.2+ |
| ❌ `from langchain.chat_models import ChatAnthropic` | ✅ `from langchain_anthropic import ChatAnthropic` | langchain-anthropic | v0.2+ |
| ❌ `from langchain.chat_models import ChatGoogle` | ✅ `from langchain_google_genai import ChatGoogleGenerativeAI` | langchain-google-genai | v0.2+ |
| ❌ `from langchain.chat_models import ChatCohere` | ✅ `from langchain_cohere import ChatCohere` | langchain-cohere | v0.2+ |

**New Unified Initialization (v1.0+):**
```python
# ✅ NEW: Universal model initialization
from langchain.chat_models import init_chat_model
model = init_chat_model("gpt-4o")
model = init_chat_model("claude-3-sonnet-20240229")
```

**Status in Project Files:**
- `libs/kotaemon/kotaemon/llms/chats/langchain_based.py` - ⚠️ Uses conditional imports (both old and new)

---

### 3. Completion LLMs (🔴 CRITICAL - LEGACY)

| Deprecated | Modern | Package | Notes |
|-----------|--------|---------|-------|
| ❌ `from langchain.llms import OpenAI` | ✅ `from langchain_openai import OpenAI` | langchain-openai | Completion-based (dated) |
| ❌ `from langchain.llms import AzureOpenAI` | ✅ `from langchain_openai import AzureOpenAI` | langchain-openai | Completion-based (dated) |
| ❌ `from langchain.llms import LlamaCpp` | ✅ `from langchain_community.llms import LlamaCpp` | langchain-community | Local models |

**⚠️ IMPORTANT:** Completion models are deprecated in favor of chat models. Migrate to ChatOpenAI if possible.

**Status in Project Files:**
- `libs/kotaemon/kotaemon/llms/completions/langchain_based.py` - ⚠️ Uses conditional imports

---

### 4. Embeddings (⚠️ DEPRECATED)

| Deprecated | Modern | Package | Version |
|-----------|--------|---------|---------|
| ❌ `from langchain.embeddings import OpenAIEmbeddings` | ✅ `from langchain_openai import OpenAIEmbeddings` | langchain-openai | v0.2+ |
| ❌ `from langchain.embeddings import AzureOpenAIEmbeddings` | ✅ `from langchain_openai import AzureOpenAIEmbeddings` | langchain-openai | v0.2+ |
| ❌ `from langchain.embeddings import CohereEmbeddings` | ✅ `from langchain_cohere import CohereEmbeddings` | langchain-cohere | v0.2+ |
| ❌ `from langchain.embeddings import HuggingFaceBgeEmbeddings` | ✅ `from langchain_community.embeddings import HuggingFaceBgeEmbeddings` | langchain-community | v0.2+ |
| ❌ `from langchain.embeddings import GoogleGenerativeAIEmbeddings` | ✅ `from langchain_google_genai import GoogleGenerativeAIEmbeddings` | langchain-google-genai | v0.2+ |
| ❌ `from langchain.embeddings import MistralAIEmbeddings` | ✅ `from langchain_mistralai import MistralAIEmbeddings` | langchain-mistralai | v0.2+ |

**New Unified Initialization (v1.0+):**
```python
# ✅ NEW: Universal embeddings initialization
from langchain.embeddings import init_embeddings
embeddings = init_embeddings("openai")
embeddings = init_embeddings("huggingface")
```

**Status in Project Files:**
- `libs/kotaemon/kotaemon/embeddings/langchain_based.py` - ⚠️ Uses conditional imports

---

### 5. Agents (🔴 CRITICAL - MAJOR CHANGES)

| Deprecated | Modern | Status | Version |
|-----------|--------|--------|---------|
| ❌ `from langchain.agents import initialize_agent` | ✅ `from langchain.agents import create_agent` | **REMOVED in v1.0** | v0.2-v1.0 |
| ❌ `from langchain.agents.agent import AgentExecutor` | ✅ Built into `create_agent()` | **REMOVED in v1.0** | v0.2-v1.0 |
| ❌ `from langchain.agents import AgentType` | ✅ Use config parameters | **REMOVED in v1.0** | v1.0 |
| ❌ `from langchain.agents import Tool` | ✅ `from langchain.tools import BaseTool` or `@tool` | Moved to tools module | v0.2+ |

**Breaking Changes in Agent Creation (v1.0):**

```python
# ❌ OLD (v0.x) - WILL NOT WORK IN v1.0
from langchain.agents import initialize_agent, AgentType
agent = initialize_agent(
    tools, 
    llm, 
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    prompt=prompt
)

# ✅ NEW (v1.0+)
from langchain.agents import create_agent
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="You are helpful"  # Changed: 'prompt' → 'system_prompt'
)
```

**Status in Project Files:**
- `libs/kotaemon/kotaemon/agents/langchain_based.py` - ⚠️ Uses deprecated `initialize_agent`, `AgentExecutor`, `AgentType`
- `libs/kotaemon/kotaemon/agents/react/` - Uses ReAct pattern (needs update)
- `libs/kotaemon/kotaemon/agents/rewoo/` - Uses ReWOO pattern (needs update)

---

### 6. Tools (⚠️ DEPRECATED - API CHANGED)

| Deprecated | Modern | Package | Version |
|-----------|--------|---------|---------|
| ❌ `from langchain.agents import Tool` | ✅ `from langchain.tools import BaseTool` | langchain_core | v0.2+ |
| ✅ `from langchain.tools import tool` | ✅ Decorator pattern (NEW) | langchain_core | v1.0+ |

**Migration Example:**
```python
# ❌ OLD (v0.x)
from langchain.agents import Tool
tool = Tool(name="search", func=search_func, description="Search")

# ✅ NEW (v1.0+)
from langchain.tools import tool, BaseTool

# Using decorator
@tool
def search(query: str) -> str:
    """Search the web"""
    return search_func(query)

# Or using class
class SearchTool(BaseTool):
    name: str = "search"
    description: str = "Search"
    
    def _run(self, query: str) -> str:
        return search_func(query)
```

**Status in Project Files:**
- `libs/kotaemon/kotaemon/agents/tools/base.py` - ⚠️ Uses conditional import for `Tool`, has conversion methods
- `libs/kotaemon/kotaemon/agents/tools/google.py` - Uses `SerpAPIWrapper` from langchain_community

---

### 7. Text Splitters (⚠️ DEPRECATED - PACKAGE MOVE)

| Deprecated | Modern | Package | Version |
|-----------|--------|---------|---------|
| ❌ `from langchain.text_splitter import CharacterTextSplitter` | ✅ `from langchain_text_splitters import CharacterTextSplitter` | langchain-text-splitters | v0.2+ |
| ❌ `from langchain.text_splitter import RecursiveCharacterTextSplitter` | ✅ `from langchain_text_splitters import RecursiveCharacterTextSplitter` | langchain-text-splitters | v0.2+ |

**Status in Project Files:**
- `libs/ktem/ktem/reasoning/react.py` - ⚠️ Uses deprecated import
- `libs/ktem/ktem/reasoning/rewoo.py` - ⚠️ Uses deprecated import
- `libs/kotaemon/kotaemon/indices/splitters/llm_chunker.py` - Uses `langchain_core` (good)

---

### 8. Output Parsers (⚠️ DEPRECATED - BASE CLASS CHANGED)

| Deprecated | Modern | Package | Version |
|-----------|--------|---------|---------|
| ❌ `from langchain.output_parsers import OutputParser` | ✅ `from langchain_core.output_parsers import BaseOutputParser` | langchain_core | v0.2+ |
| ⚠️ `from langchain.output_parsers.boolean import BooleanOutputParser` | ✅ `from langchain_core.output_parsers import BooleanOutputParser` | langchain_core | v0.2+ |

**Migration Example:**
```python
# ❌ OLD (v0.x)
from langchain.output_parsers import OutputParser

# ✅ NEW (v1.0+)
from langchain_core.output_parsers import BaseOutputParser, BooleanOutputParser
```

**Status in Project Files:**
- `libs/kotaemon/kotaemon/indices/rankings/llm.py` - ⚠️ Uses deprecated import path
- `libs/kotaemon/kotaemon/indices/rankings/llm_scoring.py` - ⚠️ Uses deprecated import path
- `libs/kotaemon/kotaemon/indices/splitters/llm_chunker.py` - ✅ Uses correct `langchain_core` imports

---

### 9. Schema & Documents (⚠️ PARTIALLY DEPRECATED)

| Deprecated | Modern | Package | Version |
|-----------|--------|---------|---------|
| ⚠️ `from langchain.schema import Document` | ✅ `from langchain_core.documents import Document` | langchain_core | v0.2+ |

**Status in Project Files:**
- `libs/kotaemon/tests/test_reader.py` - ⚠️ Uses deprecated import

---

### 10. Utilities (⚠️ SCATTERED)

| Deprecated | Modern | Package | Version |
|-----------|--------|---------|---------|
| ⚠️ `from langchain.utils import get_from_dict_or_env` | ✅ `from langchain_core.utils import get_from_dict_or_env` | langchain_core | v0.2+ |

**Status in Project Files:**
- `libs/kotaemon/kotaemon/loaders/mathpix_loader.py` - ⚠️ Uses deprecated import

---

## Detailed Migration Guide

### Step 1: Update Message Imports

**File:** `libs/kotaemon/kotaemon/base/schema.py`

```python
# ❌ CURRENT
from langchain.schema.messages import AIMessage as LCAIMessage
from langchain.schema.messages import HumanMessage as LCHumanMessage
from langchain.schema.messages import SystemMessage as LCSystemMessage

# ✅ NEW
from langchain.messages import AIMessage as LCAIMessage
from langchain.messages import HumanMessage as LCHumanMessage
from langchain.messages import SystemMessage as LCSystemMessage
```

---

### Step 2: Update LLM Base Class

**File:** `libs/kotaemon/kotaemon/llms/base.py`

```python
# ✅ ALREADY CORRECT
from langchain_core.language_models.base import BaseLanguageModel
```

---

### Step 3: Update Chat Model Imports (Conditional)

**File:** `libs/kotaemon/kotaemon/llms/chats/langchain_based.py`

The file already uses conditional imports, which is good for backward compatibility:

```python
def _get_lc_class(self):
    try:
        from langchain_openai import ChatOpenAI  # ✅ NEW
    except ImportError:
        from langchain.chat_models import ChatOpenAI  # ⚠️ FALLBACK
    return ChatOpenAI
```

**For v1.0+ cleanup, make langchain_openai the primary:**

```python
def _get_lc_class(self):
    from langchain_openai import ChatOpenAI  # ✅ PRIMARY
    return ChatOpenAI
```

---

### Step 4: Update Completion Model Imports (Conditional)

**File:** `libs/kotaemon/kotaemon/llms/completions/langchain_based.py`

Same pattern as chat models - already uses conditional imports. For v1.0+:

```python
def _get_lc_class(self):
    from langchain_openai import OpenAI  # ✅ PRIMARY
    return OpenAI
```

---

### Step 5: Update Embedding Imports (Conditional)

**File:** `libs/kotaemon/kotaemon/embeddings/langchain_based.py`

Already uses conditional imports. All good for now.

---

### Step 6: Update Agent Imports (CRITICAL)

**File:** `libs/kotaemon/kotaemon/agents/langchain_based.py`

This is the biggest change:

```python
# ❌ CURRENT (v0.x)
from langchain.agents import AgentType as LCAgentType
from langchain.agents import initialize_agent
from langchain.agents.agent import AgentExecutor as LCAgentExecutor

# ✅ NEW (v1.0+)
# Requires full refactoring to use create_agent() pattern
from langchain.agents import create_agent
```

**The entire `LangchainAgent` class needs refactoring** (see Breaking Changes section below).

---

### Step 7: Update Tool Imports

**File:** `libs/kotaemon/kotaemon/agents/tools/base.py`

```python
# ⚠️ CURRENT - Keep for backward compatibility
from langchain.agents import Tool as LCTool

# ✅ ADD ALIAS for modern code
from langchain.tools import BaseTool as LCTool
```

---

### Step 8: Update Text Splitter Imports

**Files:** 
- `libs/ktem/ktem/reasoning/react.py`
- `libs/ktem/ktem/reasoning/rewoo.py`

```python
# ❌ CURRENT
from langchain.text_splitter import CharacterTextSplitter

# ✅ NEW
from langchain_text_splitters import CharacterTextSplitter
```

**Requires adding `langchain-text-splitters` to dependencies.**

---

### Step 9: Update Output Parser Imports

**Files:**
- `libs/kotaemon/kotaemon/indices/rankings/llm.py`
- `libs/kotaemon/kotaemon/indices/rankings/llm_scoring.py`

```python
# ❌ CURRENT
from langchain.output_parsers.boolean import BooleanOutputParser

# ✅ NEW
from langchain_core.output_parsers import BooleanOutputParser
```

---

### Step 10: Update Other Imports

**Update these utility imports:**

- `libs/kotaemon/kotaemon/loaders/mathpix_loader.py`
  ```python
  # ❌ from langchain.utils import get_from_dict_or_env
  # ✅ from langchain_core.utils import get_from_dict_or_env
  ```

- `libs/kotaemon/tests/test_reader.py`
  ```python
  # ❌ from langchain.schema import Document as LangchainDocument
  # ✅ from langchain_core.documents import Document as LangchainDocument
  ```

---

## Breaking Changes in v1.0

### 1. Python Version Requirement
- ❌ Python 3.9 support dropped
- ✅ Requires Python 3.10+

### 2. Message Properties
```python
# ❌ v0.x
message.text()  # Method call

# ✅ v1.0+
message.text    # Property access
```

### 3. AIMessage Parameters
```python
# ❌ v0.x - REMOVED in v1.0
AIMessage(content="text", example=True)

# ✅ v1.0+
AIMessage(content="text", additional_kwargs={"example": True})
```

### 4. Agent Creation API (MAJOR)
```python
# ❌ v0.x
from langchain.agents import initialize_agent, AgentType
executor = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    prompt=custom_prompt,
    verbose=True
)

# ✅ v1.0+
from langchain.agents import create_agent
executor = create_agent(
    model=llm,
    tools=tools,
    system_prompt="Be helpful",  # Changed parameter name
    # Note: Must be TypedDict, not Pydantic
)
```

### 5. Agent State Schema
```python
# ❌ v0.x - Pydantic models supported
from pydantic import BaseModel
class AgentState(BaseModel):
    messages: list

# ✅ v1.0+ - TypedDict ONLY
from typing import TypedDict
class AgentState(TypedDict):
    messages: list
```

### 6. Streaming Node Names
```python
# ❌ v0.x
stream = executor.stream(inputs, stream_mode="values")
for node, output in stream:
    if node == "agent":  # Old name
        print(output)

# ✅ v1.0+
stream = executor.stream(inputs, stream_mode="values")
for node, output in stream:
    if node == "model":  # New name
        print(output)
```

### 7. Structured Output Strategy
```python
# ❌ v0.x - Simple schema passing
from langchain_openai import ChatOpenAI
model = ChatOpenAI(response_format=MySchema)

# ✅ v1.0+ - Requires strategy
from langchain_core.output_parsers import ToolStrategy
model = ChatOpenAI()
# Use with_structured_output() instead
structured_model = model.with_structured_output(MySchema, method="json_schema")
```

### 8. Tool Binding
```python
# ❌ v0.x
bound_model = llm.bind_tools(tools)

# ✅ v1.0+ - Different approach with create_agent
# Tools are passed to create_agent, not bound to model
```

---

## Migration Checklist

### Phase 1: Deprecation Warnings (0.2.x)
- [ ] Update message imports to `langchain.messages`
- [ ] Update chat model imports to provider packages
- [ ] Update embedding imports to provider packages
- [ ] Update output parser imports to `langchain_core`
- [ ] Update text splitter imports to `langchain_text_splitters`
- [ ] Update utility imports to `langchain_core.utils`

### Phase 2: Prepare for v1.0
- [ ] Review all conditional imports
- [ ] Identify all `initialize_agent` usage
- [ ] Review all agent state schemas
- [ ] Test with langchain>=1.0
- [ ] Update Python to 3.10+

### Phase 3: v1.0 Full Migration
- [ ] Replace `initialize_agent` with `create_agent`
- [ ] Refactor agent state to TypedDict
- [ ] Update parameter names (`prompt` → `system_prompt`)
- [ ] Remove all dependency on `AgentType` enum
- [ ] Update message property access (`.text()` → `.text`)
- [ ] Remove `AIMessage(example=...)` parameters
- [ ] Update streaming node references

### Phase 4: Testing & Validation
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Deprecation warnings resolved
- [ ] Performance benchmarks

---

## Quick Reference

### Current Project Status

| Component | File | Status | Priority |
|-----------|------|--------|----------|
| Message Schema | `base/schema.py` | ⚠️ Deprecated import | Medium |
| LLM Base | `llms/base.py` | ✅ Correct | - |
| Chat Models | `llms/chats/langchain_based.py` | ⚠️ Conditional imports | Medium |
| Completion LLMs | `llms/completions/langchain_based.py` | ⚠️ Conditional imports | Medium |
| Embeddings | `embeddings/langchain_based.py` | ⚠️ Conditional imports | Medium |
| Agents | `agents/langchain_based.py` | 🔴 **CRITICAL** | High |
| Agent Tools | `agents/tools/base.py` | ⚠️ Old API | Medium |
| Text Splitters | `reasoning/react.py, rewoo.py` | ⚠️ Deprecated | Medium |
| LLM Ranking | `indices/rankings/llm.py` | ⚠️ Deprecated import | Low |
| LLM Scoring | `indices/rankings/llm_scoring.py` | ⚠️ Deprecated import | Low |
| LLM Chunking | `indices/splitters/llm_chunker.py` | ✅ Correct | - |
| Loader Utils | `loaders/mathpix_loader.py` | ⚠️ Deprecated import | Low |
| Tests | `tests/test_reader.py` | ⚠️ Deprecated import | Low |

### Import Migration Table

| Old Import | New Import | Package | Reason |
|-----------|-----------|---------|--------|
| `langchain.schema.messages.*` | `langchain.messages.*` | langchain_core | Consolidation |
| `langchain.chat_models.*` | `langchain_<provider>.*` | provider-specific | Modularization |
| `langchain.llms.*` | `langchain_<provider>.*` | provider-specific | Modularization |
| `langchain.embeddings.*` | `langchain_<provider>.*` | provider-specific | Modularization |
| `langchain.agents.initialize_agent` | `langchain.agents.create_agent` | langchain | v1.0 refactor |
| `langchain.agents.AgentType` | Use config params | - | Removed |
| `langchain.agents.Tool` | `langchain.tools.BaseTool` | langchain_core | Moved |
| `langchain.text_splitter.*` | `langchain_text_splitters.*` | langchain-text-splitters | Extracted |
| `langchain.output_parsers.*` | `langchain_core.output_parsers.*` | langchain_core | Moved |
| `langchain.utils.*` | `langchain_core.utils.*` | langchain_core | Moved |
| `langchain.schema.Document` | `langchain_core.documents.Document` | langchain_core | Moved |

### Version Support

| LangChain Version | Status | Support |
|------------------|--------|---------|
| < 0.1 | Unsupported | ❌ |
| 0.1.x | Legacy | ⚠️ Current project |
| 0.2.x | Current | ⚠️ With deprecations |
| 1.0.x+ | Modern | ✅ Target |

**Project Current Version Range:** `langchain>=0.1.16,<0.2.16`  
**Recommended Target:** `langchain>=1.0.7`

---

## Additional Resources

- [LangChain Official Docs](https://docs.langchain.com/)
- [LangChain API Reference](https://api.python.langchain.com/)
- [LangChain GitHub Releases](https://github.com/langchain-ai/langchain/releases)
- [Migration Guide](https://docs.langchain.com/docs/migration_guide)
- [Release Policy](https://docs.langchain.com/oss/python/release-policy#migration-support)

---

## Summary

The project uses LangChain extensively with many deprecated import patterns. While most code will continue to work due to re-exports and conditional imports, **upgrading to v1.0+ requires significant refactoring**, especially in the agent system.

**Recommended Migration Timeline:**
1. **Phase 1:** Update simple imports (3-5 hours)
2. **Phase 2:** Test with v0.2.x (2-3 hours)
3. **Phase 3:** Plan v1.0 agent refactor (4-6 hours)
4. **Phase 4:** Execute v1.0 migration (8-12 hours)

**Total Estimated Effort:** 20-30 hours for complete migration

---

**Last Updated:** November 18, 2025  
**Document Version:** 1.0
