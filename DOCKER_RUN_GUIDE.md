# Docker Build and Run Guide for Kotaemon RAG

This guide covers how to build and run Kotaemon with three different RAG configurations:
1. **Normal RAG** - Standard retrieval with Azure OpenAI (gpt-5-mini)
2. **Nano-GraphRAG** - Lightweight knowledge graph with OpenAI
3. **MS GraphRAG** - Comprehensive knowledge graph with OpenAI

---

## IMPORTANT: Always Use --env-file .env

⚠️ **CRITICAL:** You MUST include `--env-file .env` in every docker run command, otherwise:
- Mind maps won't generate
- Citations won't work
- LLM responses won't work
- Image captioning won't work
- Everything will fail silently

The `--env-file .env` flag loads your Azure OpenAI credentials and configuration.

---

## Setup: .env File Configuration

Before running any Docker configuration, create/update your `.env` file at `/home/sshan/kotaemon/.env`:

```bash
# ===== AZURE OPENAI (for Normal RAG) =====
AZURE_OPENAI_ENDPOINT=https://nwl-field-agent-swed.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-azure-key-here
OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-mini
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-3-large
TEMPERATURE=1.0

# ===== VISION/MULTIMODAL (for image captioning) =====
VLM_DEPLOYMENT=gpt-5-mini

# ===== OPENAI (for GraphRAG) =====
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_API_BASE=https://api.openai.com/v1

# ===== GRAPHRAG CONFIGURATION =====
GRAPHRAG_API_KEY=sk-your-openai-key-here
GRAPHRAG_LLM_MODEL=gpt-4o-mini
GRAPHRAG_EMBEDDING_MODEL=text-embedding-3-small

# ===== GRAPHRAG FEATURE FLAGS =====
USE_MS_GRAPHRAG=true
USE_NANO_GRAPHRAG=false
USE_LIGHTRAG=true
USE_CUSTOMIZED_GRAPHRAG_SETTING=false
```

---

## Configuration 1: Normal RAG (Azure OpenAI)

### Build the Docker Image

```bash
cd /home/sshan/kotaemon
docker build -f Dockerfile.normal-rag -t kotaemo-rag:normal .
```

### Run the Container

```bash
docker rm -f kotaemon 2>/dev/null || true
docker run -d \
  --name kotaemon \
  -p 7860:7860 \
  --env-file .env \
  -e NODE_TLS_REJECT_UNAUTHORIZED=0 \
  kotaemo-rag:normal
```

### Check Logs

```bash
docker logs -f kotaemon
```

### Access the Application

Open browser: `http://localhost:7860`

### Stop and Remove Container

```bash
docker stop kotaemon
docker rm kotaemon
```

---

## Configuration 2: Nano-GraphRAG with OpenAI

### Build the Docker Image

```bash
cd /home/sshan/kotaemon
docker build -f Dockerfile.nano-graphrag -t kotaemo-rag:nano .
```

### Run the Container

```bash
docker rm -f kotaemon 2>/dev/null || true
docker run -d \
  --name kotaemon \
  -p 7860:7860 \
  --env-file .env \
  -e NODE_TLS_REJECT_UNAUTHORIZED=0 \
  -e USE_NANO_GRAPHRAG=true \
  -e USE_MS_GRAPHRAG=false \
  -e GRAPHRAG_API_KEY=${GRAPHRAG_API_KEY} \
  kotaemo-rag:nano
```

### What Nano-GraphRAG Does

- Extracts entities and relationships from documents
- Builds a lightweight knowledge graph
- Supports both `local` and `global` search modes
- Faster than MS GraphRAG
- Good for quick knowledge base construction

### Access the Application

Open browser: `http://localhost:7860`

---

## Configuration 3: MS GraphRAG with OpenAI

### Build the Docker Image

```bash
cd /home/sshan/kotaemon
docker build -f Dockerfile.graphrag -t kotaemo-rag:graph .
```

### Run the Container

```bash
docker rm -f kotaemon 2>/dev/null || true
docker run -d \
  --name kotaemon \
  -p 7860:7860 \
  --env-file .env \
  -e NODE_TLS_REJECT_UNAUTHORIZED=0 \
  -e USE_MS_GRAPHRAG=true \
  -e USE_NANO_GRAPHRAG=false \
  -e GRAPHRAG_API_KEY=${GRAPHRAG_API_KEY} \
  kotaemo-rag:graph
```

### What MS GraphRAG Does

- Comprehensive entity extraction and relationship detection
- Community detection and report generation
- Full knowledge graph construction
- Supports `local` search (global requires additional configuration)
- More thorough but slower than Nano-GraphRAG

### Access the Application

Open browser: `http://localhost:7860`

---

## Comparison: Normal RAG vs Nano-GraphRAG vs MS GraphRAG

| Feature | Normal RAG | Nano-GraphRAG | MS GraphRAG |
|---------|-----------|---------------|------------|
| **Speed** | Fast | Medium | Slow |
| **Entity Extraction** | No | Yes | Yes (comprehensive) |
| **Relationship Mapping** | No | Yes | Yes (with communities) |
| **Knowledge Graph** | No | Lightweight | Full |
| **Community Detection** | No | No | Yes |
| **Image Captioning** | Yes (multimodal loaders) | Yes | Yes |
| **Best For** | Quick retrieval, QA | Fast knowledge graphs | Deep document analysis |
| **API Required** | Azure OpenAI | OpenAI | OpenAI |
| **Search Types** | Direct search | Local + Global | Local |

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs kotaemon

# Verify .env file exists and has correct values
cat .env

# Rebuild image without cache
docker build --no-cache -f Dockerfile.nano-graphrag -t kotaemo-rag:nano .
```

### Port already in use

```bash
# Kill existing container
docker rm -f kotaemon

# Or use different port
docker run -d --name kotaemon -p 8000:7860 ...
```

### NLTK data download issues

The NLTK data is pre-downloaded in the Dockerfile, but if you still get errors:

```bash
docker exec kotaemon python -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import nltk; nltk.download('punkt_tab'); nltk.download('punkt')"
```

### GraphRAG API key not set

```bash
# Verify GRAPHRAG_API_KEY is in .env
grep GRAPHRAG_API_KEY .env

# Or pass it explicitly when running
docker run -d \
  --name kotaemon \
  -p 7860:7860 \
  --env-file .env \
  -e NODE_TLS_REJECT_UNAUTHORIZED=0 \
  -e GRAPHRAG_API_KEY=sk-your-key-here \
  kotaemo-rag:nano
```

### Image captioning not working with gpt-5-mini

Ensure your `.env` has:

```bash
VLM_DEPLOYMENT=gpt-5-mini
AZURE_OPENAI_ENDPOINT=https://nwl-field-agent-swed.cognitiveservices.azure.com
OPENAI_API_VERSION=2024-12-01-preview
```

And that adobe_loader.py has been updated to use `config("VLM_DEPLOYMENT", default="gpt-5-mini")`

---

## Quick Commands Reference

### Build all images

```bash
cd /home/sshan/kotaemon
docker build -f Dockerfile.normal-rag -t kotaemo-rag:normal .
docker build -f Dockerfile.nano-graphrag -t kotaemo-rag:nano .
docker build -f Dockerfile.graphrag -t kotaemo-rag:graph .
```

### List available images

```bash
docker images | grep kotaemo-rag
```

### Switch between configurations

```bash
# Stop current container
docker stop kotaemon 2>/dev/null || true

# Remove current container
docker rm kotaemon 2>/dev/null || true

# Run different configuration (e.g., nano-graphrag)
docker run -d --name kotaemon -p 7860:7860 --env-file .env -e NODE_TLS_REJECT_UNAUTHORIZED=0 kotaemo-rag:nano
```

### View logs in real-time

```bash
docker logs -f kotaemon
```

### Execute commands inside container

```bash
# Interactive bash session
docker exec -it kotaemon bash

# Run single command
docker exec kotaemon python -c "print('Hello')"
```

### Clean up all Kotaemon containers and images

```bash
docker stop kotaemon 2>/dev/null || true
docker rm kotaemon 2>/dev/null || true
docker rmi kotaemo-rag:normal kotaemo-rag:nano kotaemo-rag:graph 2>/dev/null || true
```

---

## Switching Configurations (Recommended Workflow)

### To switch from Normal RAG to Nano-GraphRAG:

```bash
# 1. Ensure .env has GRAPHRAG_API_KEY set
echo "GRAPHRAG_API_KEY=sk-your-key-here" >> .env

# 2. Stop normal RAG container
docker stop kotaemon

# 3. Build nano-graphrag image (if not done)
docker build -f Dockerfile.nano-graphrag -t kotaemo-rag:nano .

# 4. Run nano-graphrag container
docker run -d \
  --name kotaemon \
  -p 7860:7860 \
  --env-file .env \
  -e NODE_TLS_REJECT_UNAUTHORIZED=0 \
  -e USE_NANO_GRAPHRAG=true \
  -e USE_MS_GRAPHRAG=false \
  kotaemo-rag:nano
```

### To switch from GraphRAG to Normal RAG:

```bash
# 1. Stop graphrag container
docker stop kotaemon

# 2. Remove old container
docker rm kotaemon

# 3. Run normal RAG container
docker run -d \
  --name kotaemon \
  -p 7860:7860 \
  --env-file .env \
  -e NODE_TLS_REJECT_UNAUTHORIZED=0 \
  kotaemo-rag:normal
```

---

## Environment Variables Explained

| Variable | Used By | Purpose |
|----------|---------|---------|
| `AZURE_OPENAI_ENDPOINT` | Normal RAG | Azure OpenAI service endpoint |
| `AZURE_OPENAI_API_KEY` | Normal RAG | Azure OpenAI authentication |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Normal RAG | Azure OpenAI chat model deployment name |
| `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT` | Normal RAG | Azure OpenAI embeddings model deployment name |
| `OPENAI_API_KEY` | GraphRAG | Standard OpenAI API key |
| `GRAPHRAG_API_KEY` | GraphRAG | OpenAI API key for GraphRAG (can be same as OPENAI_API_KEY) |
| `GRAPHRAG_LLM_MODEL` | GraphRAG | Model for entity extraction (e.g., gpt-4o-mini) |
| `GRAPHRAG_EMBEDDING_MODEL` | GraphRAG | Embedding model for GraphRAG (e.g., text-embedding-3-small) |
| `VLM_DEPLOYMENT` | Normal RAG | Vision model deployment name for image captioning |
| `TEMPERATURE` | Normal RAG | LLM temperature (gpt-5-mini only supports 1.0) |
| `USE_NANO_GRAPHRAG` | GraphRAG Config | Enable Nano-GraphRAG (true/false) |
| `USE_MS_GRAPHRAG` | GraphRAG Config | Enable MS GraphRAG (true/false) |
| `USE_CUSTOMIZED_GRAPHRAG_SETTING` | GraphRAG Config | Use custom settings.yaml (true/false) |

---

## Next Steps

1. **Choose your configuration** - Start with Normal RAG if unsure
2. **Update .env file** - Add necessary API keys
3. **Build the Docker image** - Use appropriate Dockerfile
4. **Run the container** - Follow configuration-specific instructions
5. **Test the application** - Access at http://localhost:7860
6. **Upload a PDF** - Start using RAG functionality

---

Last Updated: 2025-11-13
