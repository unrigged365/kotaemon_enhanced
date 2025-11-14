# Kotaemon Docker Commands Reference

**Last Updated:** 2025-11-11

This document contains all Docker commands used throughout the Kotaemon setup process, organized by configuration and use case.

> **⚠️ IMPORTANT:** Replace all placeholder values with your actual credentials:
> - `<YOUR_AZURE_OPENAI_ENDPOINT>` → Your Azure OpenAI service endpoint
> - `<YOUR_AZURE_OPENAI_API_KEY>` → Your Azure OpenAI API key
> - `<YOUR_OPENAI_API_VERSION>` → Your API version (e.g., 2024-12-01-preview)
> - `<YOUR_AZURE_CHAT_DEPLOYMENT>` → Your chat model deployment (e.g., gpt-5-mini)
> - `<YOUR_EMBEDDINGS_DEPLOYMENT>` → Your embeddings deployment (e.g., text-embedding-3-large)

---

## Table of Contents

1. [Initial Docker Attempts (Failed/Outdated)](#initial-docker-attempts)
2. [Docker with Normal RAG + gpt-5-mini (CURRENT)](#docker-with-normal-rag--gpt-5-mini-current)
3. [Docker with Normal RAG + gpt-5-nano](#docker-with-normal-rag--gpt-5-nano)
4. [Docker with Nano-GraphRAG + gpt-5-mini (DEPRECATED)](#docker-with-nano-graphrag--gpt-5-mini-deprecated)
5. [Docker with Nano-GraphRAG + gpt-5-nano (DEPRECATED)](#docker-with-nano-graphrag--gpt-5-nano-deprecated)
6. [Docker Maintenance Commands](#docker-maintenance-commands)
7. [Azure OpenAI Configuration Variables](#azure-openai-configuration-variables)

---

## Initial Docker Attempts

### Interactive Mode (Failed - No TTY)
```bash
docker run -e GRADIO_SERVER_NAME=0.0.0.0 -e GRADIO_SERVER_PORT=7860 -e AZURE_OPENAI_ENDPOINT=<YOUR_AZURE_OPENAI_ENDPOINT> -e AZURE_OPENAI_API_KEY=<YOUR_AZURE_OPENAI_API_KEY> -e OPENAI_API_VERSION=<YOUR_OPENAI_API_VERSION> -e AZURE_OPENAI_CHAT_DEPLOYMENT=<YOUR_AZURE_CHAT_DEPLOYMENT> -e AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=<YOUR_EMBEDDINGS_DEPLOYMENT> -v ./ktem_app_data:/app/ktem_app_data -p 7860:7860 -it --rm ghcr.io/cinnamon/kotaemon:main-lite
```

**Status:** ❌ Failed
**Error:** `the input device is not a TTY`
**Issue:** Can't use `-it` flags in non-interactive environments

---

### Official Image (main-lite)
```bash
docker run -d --name kotaemo -e GRADIO_SERVER_NAME=0.0.0.0 -e GRADIO_SERVER_PORT=7860 -e AZURE_OPENAI_ENDPOINT=<YOUR_AZURE_OPENAI_ENDPOINT> -e AZURE_OPENAI_API_KEY=<YOUR_AZURE_OPENAI_API_KEY> -e OPENAI_API_VERSION=<YOUR_OPENAI_API_VERSION> -e AZURE_OPENAI_CHAT_DEPLOYMENT=<YOUR_AZURE_CHAT_DEPLOYMENT> -e AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=<YOUR_EMBEDDINGS_DEPLOYMENT> -v ./ktem_app_data:/app/ktem_app_data -p 7860:7860 ghcr.io/cinnamon/kotaemon:main-lite
```

**Status:** ✅ Ran
**Issue:** Missing nano-graphrag (showed warnings)

---

## Docker with Normal RAG + gpt-5-mini (CURRENT ✅)

### Build Custom Image (No GraphRAG)
```bash
docker build -f Dockerfile.normal-rag -t kotaemo-rag:normal .
```

**Dockerfile.normal-rag content:**
```dockerfile
FROM ghcr.io/cinnamon/kotaemon:main-full

# Pre-download NLTK data with SSL verification disabled
RUN python -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import nltk; nltk.download('punkt_tab'); nltk.download('punkt')" || true

# Normal RAG with Azure OpenAI (gpt-5-mini) and multimodal document processing
# Uses: AdobeReader, AzureAIDocumentIntelligenceLoader, DoclingReader for image captioning

# Gradio server configuration
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# LLM parameters
ENV TEMPERATURE=1.0

# SSL/TLS configuration
ENV NODE_TLS_REJECT_UNAUTHORIZED=0
```

### Run Container - Normal RAG with gpt-5-mini
```bash
docker run -d --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 kotaemo-rag:normal
```

**Important:** Create `.env` file with:
```bash
# ⚠️ REPLACE WITH YOUR ACTUAL CREDENTIALS:
AZURE_OPENAI_ENDPOINT=<YOUR_AZURE_OPENAI_ENDPOINT>
AZURE_OPENAI_API_KEY=<YOUR_AZURE_OPENAI_API_KEY>
OPENAI_API_VERSION=<YOUR_OPENAI_API_VERSION>
AZURE_OPENAI_CHAT_DEPLOYMENT=<YOUR_AZURE_CHAT_DEPLOYMENT>
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=<YOUR_EMBEDDINGS_DEPLOYMENT>
TEMPERATURE=1.0
VLM_DEPLOYMENT=gpt-5-mini
NODE_TLS_REJECT_UNAUTHORIZED=0
```

**Status:** ✅ Production Ready
**Features:**
- ✅ Normal RAG (vector + full-text search)
- ✅ gpt-5-mini for Q&A
- ✅ text-embedding-3-large for embeddings
- ✅ Temperature set to 1.0
- ✅ No GraphRAG

### Run in Foreground (For Logs)
```bash
docker run --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 --rm kotaemo-rag:normal
```

**Status:** ✅ Good for debugging
**Note:** Runs in foreground, Ctrl+C to stop

---

## Docker with Normal RAG + gpt-5-nano

### Build Custom Image
```bash
docker build -f Dockerfile.normal-rag -t kotaemo-rag:nano .
```

### Run Container - Normal RAG with gpt-5-nano
```bash
docker run -d --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 -e AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-nano kotaemo-rag:nano
```

**Status:** ✅ Alternative Option
**Features:**
- ✅ Normal RAG (vector + full-text search)
- ✅ gpt-5-nano for Q&A (faster than gpt-5-mini)
- ✅ text-embedding-3-large for embeddings
- ✅ Temperature set to 1.0
- ✅ No GraphRAG

**When to use:** When you need faster response times

---

## Docker with Nano-GraphRAG + gpt-5-mini (DEPRECATED ❌)

### Build Custom Image with Nano-GraphRAG
```bash
docker build -f Dockerfile.nano-graphrag -t kotaemo-rag:nano-graph .
```

**Dockerfile.nano-graphrag content:**
```dockerfile
FROM ghcr.io/cinnamon/kotaemon:main-full

# Install nano-graphrag and fix hnswlib compatibility issue
RUN pip install --no-cache-dir nano-graphrag && \
    pip uninstall hnswlib chroma-hnswlib -y && \
    pip install --no-cache-dir chroma-hnswlib

# Pre-download NLTK data with SSL verification disabled
RUN python -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import nltk; nltk.download('punkt_tab'); nltk.download('punkt')" || true

# Nano-GraphRAG - lightweight knowledge graph approach for document understanding
# Uses: OpenAI API key (separate from Azure) for entity extraction and relationships
# Faster than MS GraphRAG, good for quick graph construction

# Gradio server configuration
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# LLM parameters
ENV TEMPERATURE=1.0

# SSL/TLS configuration
ENV NODE_TLS_REJECT_UNAUTHORIZED=0
```

### Run Container - Nano-GraphRAG with gpt-5-mini
```bash
docker run -d --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 -e USE_NANO_GRAPHRAG=true -e USE_MS_GRAPHRAG=false kotaemo-rag:nano-graph
```

**Status:** ⚠️ Deprecated
**Issues:**
- API timeouts during entity extraction
- gpt-5-mini too slow for GraphRAG workloads
- Use gpt-5-nano variant instead

---

## Docker with Nano-GraphRAG + gpt-5-nano (DEPRECATED ❌)

### Build Custom Image (Same as above)
```bash
docker build -f Dockerfile.nano-graphrag -t kotaemo-rag:nano-graph .
```

### Run Container - Nano-GraphRAG with gpt-5-nano
```bash
docker run -d --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 -e USE_NANO_GRAPHRAG=true -e USE_MS_GRAPHRAG=false -e AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-nano kotaemo-rag:nano-graph
```

**Status:** ⚠️ Deprecated
**Issues:**
- Faster than gpt-5-mini but still occasional timeouts
- GraphRAG entity extraction unstable
- Switched to normal RAG for stability

---

## Docker Maintenance Commands

### Stop Container
```bash
docker stop kotaemon
```

### Remove Container
```bash
docker rm kotaemon
```

### Stop and Remove (Force)
```bash
docker rm -f kotaemon
```

### View Logs (Live)
```bash
docker logs -f kotaemon
```

### View Last 50 Lines of Logs
```bash
docker logs --tail 50 kotaemon
```

### Execute Command in Running Container
```bash
docker exec kotaemon python -c "command here"
```

### Download NLTK Data in Running Container
```bash
docker exec kotaemon python -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import nltk; nltk.download('punkt_tab'); nltk.download('punkt')"
```

### Check Running Containers
```bash
docker ps
```

### Check All Containers (Including Stopped)
```bash
docker ps -a
```

### View Container Details
```bash
docker inspect kotaemon
```

### Rebuild Image (After Dockerfile changes)
```bash
docker build -f Dockerfile.normal-rag -t kotaemo-rag:normal . --no-cache
```

---

## Azure OpenAI Configuration Variables

### Required Environment Variables (in .env file)
```bash
# ⚠️ REPLACE ALL PLACEHOLDERS WITH YOUR ACTUAL VALUES:

GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SERVER_PORT=7860
AZURE_OPENAI_ENDPOINT=<YOUR_AZURE_OPENAI_ENDPOINT>
AZURE_OPENAI_API_KEY=<YOUR_AZURE_OPENAI_API_KEY>
OPENAI_API_VERSION=<YOUR_OPENAI_API_VERSION>
TEMPERATURE=1.0
```

### Model Deployment Options
```bash
# For gpt-5-mini (Standard)
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-mini

# For gpt-5-nano (Faster)
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-nano
```

### Embedding Model
```bash
# ⚠️ REPLACE WITH YOUR ACTUAL DEPLOYMENT NAME:
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=<YOUR_EMBEDDINGS_DEPLOYMENT>
```

### Optional: GraphRAG Variables (if using GraphRAG image)
```bash
# ⚠️ REPLACE WITH YOUR ACTUAL API KEY:
GRAPHRAG_API_KEY=<YOUR_OPENAI_API_KEY>
GRAPHRAG_LLM_MODEL=gpt-4o-mini
GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small
USE_NANO_GRAPHRAG=false
USE_MS_GRAPHRAG=true
```

---

## Volume & Port Mapping

### Volume Mount
```bash
-v ./ktem_app_data:/app/ktem_app_data
```

**Purpose:** Persist application data between container restarts

### Port Mapping
```bash
-p 7860:7860
```

**Access:** `http://localhost:7860`

---

## Quick Command Reference

### Start Current Setup (Normal RAG + gpt-5-mini)
```bash
docker run -d --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 kotaemo-rag:normal
```

### Start with gpt-5-nano (Faster)
```bash
docker run -d --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 -e AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-nano kotaemo-rag:normal
```

### Restart (Stop + Remove + Start)
```bash
docker stop kotaemon && docker rm kotaemon && docker run -d --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 kotaemo-rag:normal
```

### Check Status
```bash
docker ps && docker logs kotaemon | tail -20
```

---

## Troubleshooting

### Port Already in Use
```bash
docker rm -f kotaemon
# Then run again
```

### Container Exiting Immediately
```bash
docker logs kotaemon
# Check the error messages
```

### SSL Certificate Errors (NLTK)
```bash
docker exec kotaemon python -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import nltk; nltk.download('punkt_tab'); nltk.download('punkt')"
```

### Rebuild Image (After Dockerfile changes)
```bash
docker build -f Dockerfile.normal-rag -t kotaemo-rag:normal . --no-cache
```

---

## Summary

| Setup | Image | Status | Notes |
|-------|-------|--------|-------|
| Normal RAG + gpt-5-mini | `kotaemo-rag:normal` | ✅ Recommended | Stable, reliable |
| Normal RAG + gpt-5-nano | `kotaemo-rag:normal` | ✅ Alternative | Faster responses |
| Nano-GraphRAG + gpt-5-mini | `kotaemo-rag:nano-graph` | ❌ Deprecated | Timeout issues |
| Nano-GraphRAG + gpt-5-nano | `kotaemo-rag:nano-graph` | ❌ Deprecated | Occasional timeouts |

**Current Recommendation:** Normal RAG + gpt-5-mini for production use

---

**Last Updated:** 2025-11-14
**Status:** Production Ready
**Note:** Replace all `<PLACEHOLDER>` values with your actual Azure OpenAI credentials before using.
