# Kotaemon: When Does It Use Which PDF Library?

**Date:** 2025-11-11
**Purpose:** Decision tree showing which library is used when

---

## Quick Decision Tree

```
User uploads PDF
    ↓
[Check Settings → Retrieval Settings → File Loader]
    ↓
What file loader is selected?
    │
    ├─ "normal" (PDFThumbnailReader)
    │   └─ PyMuPDF (fitz) - ONLY for thumbnails
    │   └─ pypdf/llama-index - for text extraction
    │   └─ OUTPUT: Text + Page thumbnails
    │
    ├─ "ocr" (OCRReader)
    │   └─ FullOCR Pipeline (HTTP API) - MAIN processing
    │   └─ Unstructured.io - fallback text reading
    │   └─ OUTPUT: Tables + Text (OCR-focused)
    │
    ├─ "azure_di" (AzureAIDocumentIntelligenceLoader)
    │   ├─ Azure Document Intelligence API - MAIN
    │   ├─ PyMuPDF (fitz) - for cropping figures
    │   ├─ GPT-4-Vision (Azure OpenAI) - figure captions
    │   └─ OUTPUT: Text + Tables (Markdown) + Figures (captioned)
    │
    ├─ "adobe" (AdobeReader)
    │   ├─ Adobe PDF Services API - MAIN
    │   ├─ GPT-4-Vision (Azure OpenAI) - figure captions
    │   └─ OUTPUT: Text + Tables + Figures (high quality)
    │
    ├─ "docling" (DoclingReader)
    │   ├─ Docling DocumentConverter - MAIN
    │   ├─ PyMuPDF (fitz) - for cropping figures
    │   ├─ GPT-4-Vision (Azure OpenAI) - figure captions
    │   └─ OUTPUT: Text + Tables + Figures (structured)
    │
    ├─ "unstructured" (UnstructuredReader)
    │   └─ Unstructured.io API or Local - MAIN
    │   └─ OUTPUT: Text + basic elements (universal)
    │
    ├─ "mathpix" (MathpixPDFReader)
    │   └─ Mathpix API - MAIN
    │   └─ OUTPUT: Text with preserved formulas
    │
    └─ "auto" (AutoReader / DirectoryReader)
        └─ Detect format automatically
        └─ Route to appropriate loader
        └─ OUTPUT: Varies by detected type
```

---

## Detailed Scenario-Based Usage

### Scenario 1: User Selects "normal" (Default)
**Kotaemon UI → Settings → Retrieval Settings → File Loader: "normal"**

**Libraries Used:**
1. **pypdf** (via llama-index PDFReader)
   - Extracts text from PDF pages
   - Basic structure preservation
   - USAGE: `PDFThumbnailReader.load_data(file)`

2. **PyMuPDF (fitz)**
   - Renders each page to image
   - Creates DPI-configurable thumbnails
   - USAGE: `get_page_thumbnails(file_path, pages, dpi=40)`

**Code Flow:**
```python
# settings.py selects default loader
default_loader = "normal"

# Load with PDFThumbnailReader
reader = PDFThumbnailReader()
documents = reader.load_data(file)

# Inside PDFThumbnailReader.load_data():
# Step 1: Call parent PDFReader.load_data()
documents = super().load_data(file)  # Uses pypdf via llama-index

# Step 2: Generate thumbnails
page_thumbnails = get_page_thumbnails(
    file,
    pages=[0,1,2,...],  # All pages
    dpi=40              # DPI from PDF_LOADER_DPI config
)

# Step 3: Inside get_page_thumbnails()
import fitz  # PyMuPDF
doc = fitz.open(file_path)
for page_number in pages:
    page = doc.load_page(page_number)
    pm = page.get_pixmap(dpi=dpi)  # Render to image
    img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
    # Convert to Base64
    img_base64 = convert_image_to_base64(img)
```

**Output:**
```
Documents:
  ├─ Text chunks (from pypdf)
  │   metadata: {"page_label": 0, "file_name": "..."}
  ├─ Text chunks (from pypdf)
  │   metadata: {"page_label": 1, ...}
  ├─ Thumbnail (from PyMuPDF)
  │   metadata: {"type": "thumbnail", "image_origin": "data:image/png;base64,..."}
  └─ ... (more pages)
```

**When to Use:**
- ✅ Simple PDFs (text only)
- ✅ Fast processing needed
- ✅ No tables or complex layouts
- ✅ Cost-conscious (no API calls)

---

### Scenario 2: User Selects "ocr"
**Kotaemon UI → Settings → Retrieval Settings → File Loader: "ocr"**

**Libraries Used:**
1. **FullOCR Pipeline** (Internal HTTP API)
   - Sends PDF to local endpoint
   - Returns detected tables and text regions
   - USAGE: `tenacious_api_post(url=ocr_endpoint, file_path=file, ...)`

2. **Unstructured.io** (fallback)
   - Reads PDF normally for comparison
   - USAGE: `read_pdf_unstructured(file_path)`

**Code Flow:**
```python
# User selects "ocr" loader
loader = OCRReader(endpoint="http://127.0.0.1:8000/v2/ai/infer/")

# Load data
documents = loader.load_data(file_path)

# Inside OCRReader.load_data():
# Step 1: Call FullOCR endpoint
resp = tenacious_api_post(
    url="http://127.0.0.1:8000/v2/ai/infer/",
    file_path=file_path,
    table_only=False  # Or True if use_ocr=False
)
ocr_results = resp.json()["result"]

# Step 2: Read PDF normally for comparison
pdf_page_items = read_pdf_unstructured(file_path)  # Unstructured.io

# Step 3: Merge results
tables, texts = parse_ocr_output(
    ocr_results,
    pdf_page_items,
    debug_path=None,
    artifact_path=None
)

# Step 4: Create documents
for page_id, table_text in tables:
    Document(
        text=table_text,
        metadata={"type": "table", "page_label": page_id + 1}
    )
```

**Output:**
```
Documents:
  ├─ Table (from OCR)
  │   metadata: {"type": "table", "table_origin": "..."}
  ├─ Text (from PDF)
  │   metadata: {"page_label": 1}
  ├─ Table (from OCR)
  │   metadata: {"type": "table", ...}
  └─ ...
```

**When to Use:**
- ✅ PDF with many tables
- ✅ Scanned documents
- ✅ Table structure is important
- ✅ FullOCR service is running locally
- ❌ No figure extraction
- ❌ No text OCR (only table OCR)

---

### Scenario 3: User Selects "azure_di"
**Kotaemon UI → Settings → Retrieval Settings → File Loader: "azure_di"**

**Libraries Used:**
1. **Azure Document Intelligence API**
   - Main processing engine
   - Layout analysis, OCR, table detection, figure detection
   - USAGE: `client.begin_analyze_document(model, body=file, ...)`

2. **PyMuPDF (fitz)**
   - Crops figures from original PDF at detected bounding boxes
   - USAGE: `crop_image(file_path, bbox, page_number)`

3. **GPT-4-Vision (Azure OpenAI)**
   - Generates descriptive captions for each figure
   - USAGE: `generate_single_figure_caption(figure=img_base64, vlm_endpoint=...)`

**Code Flow:**
```python
# User configures Azure DI settings
loader = AzureAIDocumentIntelligenceLoader(
    endpoint="https://your-instance.cognitiveservices.azure.com",
    credential="api-key",
    model="prebuilt-layout",
    vlm_endpoint="https://your-gpt4v-endpoint"  # Optional, for captions
)

# Load data
documents = loader.load_data(file_path)

# Inside AzureAIDocumentIntelligenceLoader.load_data():
# Step 1: Call Azure Document Intelligence
with open(file_path, "rb") as fi:
    poller = self.client_.begin_analyze_document(
        model="prebuilt-layout",
        body=fi,
        output_content_format="markdown"  # Text output format
    )
    result = poller.result()

# Step 2: Extract text content
text_content = result.content

# Step 3: Extract figures with bounding boxes
figures_output = []
for figure_desc in result.get("figures", []):
    if not vlm_endpoint:
        continue  # Skip captions if no VLM endpoint

    # Get bounding box
    page_number = figure_desc["boundingRegions"][0]["pageNumber"]
    polygon = figure_desc["boundingRegions"][0]["polygon"]
    bbox = [min_x/width, min_y/height, max_x/width, max_y/height]

    # Step 4: Crop image using PyMuPDF
    img = crop_image(file_path, bbox, page_number - 1)

    # Convert to base64
    img_base64 = convert_to_base64(img)

    # Step 5: Generate caption using GPT-4V
    caption = generate_single_figure_caption(
        figure=img_base64,
        vlm_endpoint=vlm_endpoint
    )

    # Create document
    figures_output.append(
        Document(
            text=caption,
            metadata={
                "type": "image",
                "image_origin": img_base64,
                "page_label": page_number
            }
        )
    )

# Step 6: Extract tables
tables_output = []
for table_desc in result.get("tables", []):
    # Extract table markdown from result
    offset = table_desc["spans"][0]["offset"]
    length = table_desc["spans"][0]["length"]
    table_text = text_content[offset:offset+length]

    tables_output.append(
        Document(
            text=table_text,
            metadata={
                "type": "table",
                "table_origin": table_text,
                "page_label": table_desc["boundingRegions"][0]["pageNumber"]
            }
        )
    )
```

**Output:**
```
Documents:
  ├─ Text (from Azure DI)
  │   metadata: {"page_label": 1}
  ├─ Table (from Azure DI)
  │   metadata: {"type": "table", "table_origin": "..."}
  ├─ Figure (from Azure DI + GPT-4V)
  │   text: "A bar chart showing quarterly sales..."
  │   metadata: {"type": "image", "image_origin": "data:image/png;base64,..."}
  └─ ...
```

**When to Use:**
- ✅ Enterprise document processing
- ✅ Multiple formats (PDF, DOCX, images, etc.)
- ✅ Need layout analysis
- ✅ Figure captions wanted
- ✅ High accuracy required
- 💰 Azure subscription required
- ⏱️ Slower (cloud API calls)

---

### Scenario 4: User Selects "adobe"
**Kotaemon UI → Settings → Retrieval Settings → File Loader: "adobe"**

**Libraries Used:**
1. **Adobe PDF Services API**
   - Main processing engine
   - Extracts text, tables, figures with high precision
   - USAGE: `request_adobe_service(file_path, output_path)`

2. **GPT-4-Vision (Azure OpenAI)**
   - Generates captions for extracted figures
   - USAGE: `generate_figure_captions(vlm_endpoint, figures, max_count)`

3. **PyMuPDF (fitz)** - Implicit (via Adobe extraction)

**Code Flow:**
```python
# User configures Adobe settings
loader = AdobeReader(
    vlm_endpoint="https://your-gpt4v-endpoint",
    max_figures_to_caption=100
)

# Load data
documents = loader.load_data(file_path)

# Inside AdobeReader.load_data():
# Step 1: Send PDF to Adobe API
output_path = request_adobe_service(
    file_path=str(file),
    output_path=""
)
results_path = os.path.join(output_path, "structuredData.json")

# Step 2: Parse Adobe's structured JSON output
data = load_json(results_path)
elements = data["elements"]  # Contains Text, Table, Figure elements

# Step 3: Process elements
texts = defaultdict(list)
tables = []
figures = []

for item in elements:
    page_number = item.get("Page", -1) + 1
    item_path = item["Path"]
    item_text = item.get("Text", "")

    if "/Table" in item_path:
        # Extract table
        table_content = parse_table_paths(item["filePaths"])
        tables.append((page_number, table_content, caption))

    elif "/Figure" in item_path:
        # Extract figure
        figure_content = parse_figure_paths(item["filePaths"])
        figures.append((page_number, figure_content, caption))

    else:
        # Regular text
        texts[page_number].append(item_text)

# Step 4: Generate figure captions with GPT-4V
figure_captions = generate_figure_captions(
    vlm_endpoint=vlm_endpoint,
    figures=[fig[1] for fig in figures],
    max_figures=max_figures_to_caption
)

# Update figures with captions
for fig, caption in zip(figures, figure_captions):
    fig[2] += " " + caption
```

**Output:**
```
Documents:
  ├─ Text (from Adobe)
  │   metadata: {"page_label": 1, "file_name": "..."}
  ├─ Table (from Adobe)
  │   metadata: {"type": "table", "table_origin": "..."}
  ├─ Figure (from Adobe + GPT-4V caption)
  │   text: "High-quality figure description..."
  │   metadata: {"type": "image", "image_origin": "data:image/png;base64,..."}
  └─ ...
```

**When to Use:**
- ✅ High-quality PDF processing
- ✅ Maximum accuracy for tables and figures
- ✅ Figure captions important
- 💰 Adobe subscription required
- ⏱️ Slowest (multiple API calls)

---

### Scenario 5: User Selects "docling"
**Kotaemon UI → Settings → Retrieval Settings → File Loader: "docling"**

**Libraries Used:**
1. **Docling DocumentConverter**
   - Main processing engine
   - Modern document structure parsing
   - USAGE: `converter.convert(file_path)`

2. **PyMuPDF (fitz)**
   - Crops figures using bounding boxes with coordinate conversion
   - USAGE: `crop_image(file_path, bbox, page_number)`

3. **GPT-4-Vision (Azure OpenAI)**
   - Generates additional captions (extractive + generative)
   - USAGE: `generate_single_figure_caption(figure, vlm_endpoint)`

**Code Flow:**
```python
# User configures Docling settings
loader = DoclingReader(
    vlm_endpoint="https://your-gpt4v-endpoint",
    max_figure_to_caption=100
)

# Load data
documents = loader.load_data(file_path)

# Inside DoclingReader.load_data():
# Step 1: Convert document using Docling
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert(file_path)
result_dict = result.document.export_to_dict()

# Step 2: Extract structured elements
# result_dict contains: texts, tables, pictures, pages

# Step 3: Process figures with extractive + generative captions
for figure_obj in result_dict.get("pictures", []):
    # Get extractive captions from Docling
    caption_refs = [c["$ref"] for c in figure_obj["captions"]]
    extractive_captions = []
    for caption_ref in caption_refs:
        text_id = int(caption_ref.split("/")[-1])
        caption_text = result_dict["texts"][text_id]["text"]
        extractive_captions.append(caption_text)

    # Get bounding box
    page_no = figure_obj["prov"][0]["page_no"]
    bbox_obj = figure_obj["prov"][0]["bbox"]
    bbox = [bbox_obj["l"], bbox_obj["t"], bbox_obj["r"], bbox_obj["b"]]

    # Handle coordinate system
    if bbox_obj["coord_origin"] == "BOTTOMLEFT":
        bbox = convert_bbox_bl_tl(bbox, page_width, page_height)

    # Step 4: Crop image using PyMuPDF
    img = crop_image(file_path, bbox, page_no - 1)
    img_base64 = convert_to_base64(img)

    # Step 5: Generate generative caption with GPT-4V
    gen_caption = generate_single_figure_caption(
        figure=img_base64,
        vlm_endpoint=vlm_endpoint
    )

    # Combine captions
    full_caption = "\n".join(extractive_captions + [gen_caption])
```

**Output:**
```
Documents:
  ├─ Text (from Docling)
  │   metadata: {"page_label": 1}
  ├─ Table (from Docling, Markdown format)
  │   metadata: {"type": "table", "table_origin": "..."}
  ├─ Figure (from Docling + extractive + generative captions)
  │   text: "Extractive caption\nGenerative GPT-4V caption"
  │   metadata: {"type": "image", "image_origin": "data:image/png;base64,..."}
  └─ ...
```

**When to Use:**
- ✅ Modern structured documents
- ✅ Hybrid captions (extractive + generative)
- ✅ Complex layouts
- ✅ Free and open-source
- ⏱️ Medium speed (local processing + GPT-4V calls)

---

### Scenario 6: User Selects "unstructured"
**Kotaemon UI → Settings → Retrieval Settings → File Loader: "unstructured"**

**Libraries Used:**
1. **Unstructured.io** (local or API)
   - Universal document parser
   - USAGE: `partition(filename)` or `partition_via_api(...)`

**Code Flow:**
```python
# User configures Unstructured settings
loader = UnstructuredReader(
    url="http://localhost:8000",  # Optional API
    api=False,                      # Use local by default
    split_documents=False
)

# Load data
documents = loader.load_data(file_path)

# Inside UnstructuredReader.load_data():
if self.api:
    # Use API
    from unstructured.partition.api import partition_via_api
    elements = partition_via_api(
        filename=str(file_path),
        api_key=self.api_key,
        api_url=self.server_url + "/general/v0/general"
    )
else:
    # Use local
    from unstructured.partition.auto import partition
    elements = partition(filename=str(file_path))

# Process elements
docs = []
for element in elements:
    if split_documents:
        docs.append(Document(
            text=str(element),
            metadata={"type": element.__class__.__name__}
        ))
    else:
        docs.append(Document(text=full_text))
```

**Output:**
```
Documents:
  ├─ Text (basic elements)
  └─ Mixed content (tables may be embedded in text)
```

**When to Use:**
- ✅ Any document format
- ✅ Universal parsing needed
- ✅ Cost-conscious
- ✅ Fast processing
- ❌ Limited figure extraction
- ❌ Limited table structure preservation

---

## Configuration Locations

### Where Users Select Loaders

**Option 1: UI Settings**
```
Kotaemon Web UI
  ↓
Settings (gear icon)
  ↓
Retrieval Settings
  ↓
File Loader: [dropdown]
  - normal (default)
  - ocr
  - azure_di
  - adobe
  - docling
  - unstructured
  - mathpix
  - auto
```

**Option 2: Environment Variables**
```bash
# Override default loader
export FILE_LOADER_TYPE="azure_di"
export AZURE_DI_ENDPOINT="https://..."
export AZURE_DI_CREDENTIAL="key"
```

**Option 3: Code Configuration**
```python
# In flowsettings.py
DEFAULT_FILE_READER_CLS = {
    ".pdf": "AzureAIDocumentIntelligenceLoader",
    ".docx": "DocxReader",
    ".xlsx": "ExcelReader",
}

# Or explicit in code
from kotaemon.loaders import AdobeReader
loader = AdobeReader(vlm_endpoint="...")
```

---

## API Keys & Endpoint Configuration

### Required for Each Loader

| Loader | Requires | Configuration |
|--------|----------|---------------|
| normal | None | PDF_LOADER_DPI env var |
| ocr | FullOCR Service | OCR_READER_ENDPOINT |
| azure_di | Azure Account | AZUREAI_DOCUMENT_INTELLIGENT_* |
| adobe | Adobe Account | Adobe API credential in ENV |
| docling | None | Optional: VLM endpoint for captions |
| unstructured | Optional | UNSTRUCTURED_API_KEY if using API |
| mathpix | Mathpix Account | MATHPIX_API_KEY |

### VLM Endpoint (for figure captions)

All multimodal loaders (azure_di, adobe, docling) use:
```python
vlm_endpoint = "https://your-instance.openai.azure.com/openai/deployments/gpt-4-vision/chat/completions?api-version=2024-12-01-preview"
```

or configure via:
```bash
export AZURE_OPENAI_ENDPOINT="https://..."
export AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-4-vision"
export OPENAI_API_VERSION="2024-12-01-preview"
```

---

## Library Usage Summary Table

| Library | Used By Loaders | Purpose | Always? |
|---------|-----------------|---------|---------|
| PyMuPDF (fitz) | normal, azure_di, docling | Rendering, cropping | ✅ When needed |
| pypdf | normal (via llama-index) | Text extraction | ✅ Normal loader |
| Unstructured.io | ocr (fallback), unstructured | Universal parsing | ⚠️ Conditional |
| FullOCR Pipeline | ocr | Table extraction | ✅ OCR loader |
| Adobe API | adobe | Main extraction | ✅ Adobe loader |
| Azure DI API | azure_di | Main extraction | ✅ Azure DI loader |
| Docling | docling | Document conversion | ✅ Docling loader |
| GPT-4-Vision | azure_di, adobe, docling | Figure captions | ⚠️ If enabled |
| llama-index | All | Base framework | ✅ Always |

---

## Decision: Which Loader to Use?

```
┌─ Fast & free?        → "normal" (PyMuPDF + pypdf)
├─ Tables important?   → "ocr" (FullOCR) or "azure_di"
├─ Figures important?  → "adobe" or "azure_di" or "docling"
├─ Best accuracy?      → "adobe"
├─ Any format?         → "unstructured"
├─ Formulas (math)?    → "mathpix"
├─ Modern structured?  → "docling"
└─ Enterprise?         → "azure_di" (multi-format, scale)
```

---

**File Location:** `/home/sshan/kotaemon/libs/kotaemon/kotaemon/loaders/`
**Last Updated:** 2025-11-11
