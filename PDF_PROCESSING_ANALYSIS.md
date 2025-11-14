# Kotaemon PDF & Document Processing Analysis

**Date:** 2025-11-11
**Project:** Kotaemon
**Focus:** PDF Processing Libraries, Methods, and Multimodal Support

---

## Table of Contents

1. [PDF Processing Libraries](#pdf-processing-libraries)
2. [Document Loaders Overview](#document-loaders-overview)
3. [Processing Methods for Images, Tables, Charts](#processing-methods-for-images-tables-charts)
4. [Integration Architecture](#integration-architecture)
5. [Configuration & Usage](#configuration--usage)
6. [Comparison: When to Use Which Loader](#comparison-when-to-use-which-loader)

---

## PDF Processing Libraries

### 1. **PyMuPDF (fitz)**
**Purpose:** PDF rendering, page thumbnails, image extraction
**Version:** `>=1.23,<=1.24.11`
**Files Used In:**
- `pdf_loader.py` (line 33-46)
- `azureai_document_intelligence_loader.py` (line 39-42)
- `docling_loader.py` (line 110)

**What it does:**
```python
import fitz  # PyMuPDF

doc = fitz.open(file_path)
page = doc.load_page(page_number)
pm = page.get_pixmap(dpi=dpi)  # Render page to image
```

**Capabilities:**
- ✅ Render PDF pages to high-quality images
- ✅ Extract page thumbnails at custom DPI
- ✅ Multi-page PDF handling
- ✅ Page-level image generation for visual representation

**When Used:**
- Creating page previews/thumbnails
- Visual display in UI
- Image extraction for processing by vision models

---

### 2. **pypdf**
**Purpose:** PDF text and metadata extraction
**Version:** `>=4.2.0,<4.3`
**Integration:** Via llama-index PDFReader

**What it does:**
- Extracts text content from PDF pages
- Reads PDF metadata
- Basic text parsing without layout analysis

**Location:** Used through llama-index (not directly imported)

---

### 3. **llama-index PDFReader**
**Purpose:** Base PDF text extraction framework
**Files Used In:**
- `pdf_loader.py` - PDFThumbnailReader extends PDFReader

**Code:**
```python
from llama_index.readers.file import PDFReader

class PDFThumbnailReader(PDFReader):
    def __init__(self):
        super().__init__(return_full_document=False)
```

**Features:**
- ✅ Document chunking
- ✅ Metadata preservation (page numbers, labels)
- ✅ Simple text extraction

---

### 4. **Unstructured.io**
**Purpose:** Universal document parser (PDFs, DOCX, images, HTML, etc.)
**Version:** `>=0.15.8,<0.16`
**Location:** `unstructured_loader.py`
**File:** `/home/sshan/kotaemon/libs/kotaemon/kotaemon/loaders/unstructured_loader.py`

**Supported Formats:**
- `.txt`, `.docx`, `.pptx`, `.jpg`, `.png`, `.eml`, `.html`, `.pdf`
- Optional: `.doc`, `.xls` (requires system dependencies)

**Code:**
```python
from unstructured.partition.auto import partition
elements = partition(filename=file_path_str)

# Or via API
from unstructured.partition.api import partition_via_api
elements = partition_via_api(
    filename=file_path_str,
    api_key=api_key,
    api_url=api_url
)
```

**Capabilities:**
- ✅ Automatic format detection
- ✅ Local or API-based processing
- ✅ Element-based parsing (tables, text blocks)
- ✅ Flexible document splitting

**System Requirements:**
```bash
sudo apt-get install -y libmagic-dev poppler-utils libreoffice
pip install xlrd  # For .xls files
```

---

### 5. **Adobe PDF Services SDK**
**Purpose:** Enterprise-grade multimodal PDF extraction
**Files Used In:** `adobe_loader.py` (line 24-189)
**Location:** `/home/sshan/kotaemon/libs/kotaemon/kotaemon/loaders/adobe_loader.py`

**What it Extracts:**
1. **Text** - Full document text with layout information
2. **Tables** - Structured table data
3. **Figures** - Images and visual elements

**Architecture:**
```
PDF Input
    ↓
Adobe API Service
    ↓
structuredData.json (contains elements with paths)
    ↓
Parse Elements → Categorize by Type (Text/Table/Figure)
    ↓
Generate Figure Captions (via GPT-4V)
    ↓
Documents with Metadata
```

**Code Flow:**
```python
# Step 1: Send PDF to Adobe Service
output_path = request_adobe_service(file_path=str(file), output_path="")
results_path = os.path.join(output_path, "structuredData.json")

# Step 2: Parse structured JSON
data = load_json(results_path)
elements = data["elements"]

# Step 3: Categorize elements
for item in elements:
    item_path = item["Path"]

    if re.search(r"/Table(\[\d+\])?$", item_path):
        # Process as table
        table_content = parse_table_paths(file_paths)

    elif re.search(r"/Figure(\[\d+\])?$", item_path):
        # Process as figure
        figure_content = parse_figure_paths(file_paths)

    else:
        # Process as text
```

**Figure Captioning:**
- Uses **GPT-4-Vision** endpoint (via Azure OpenAI)
- Configurable: `max_figures_to_caption` parameter
- Fallback: If captions disabled, figures still indexed without descriptions

**Output Documents:**
- Text documents with page labels
- Table documents with metadata `type: "table"`
- Figure documents with metadata `type: "image"`

---

### 6. **Azure Document Intelligence**
**Purpose:** Intelligent document analysis (OCR, layout, form recognition)
**Dependencies:**
- `azure-ai-documentintelligence` package
- `PyMuPDF` (for additional image processing)
- `Pillow` (PIL, for image handling)

**Files Used In:** `azureai_document_intelligence_loader.py` (line 59-240)
**Location:** `/home/sshan/kotaemon/libs/kotaemon/kotaemon/loaders/azureai_document_intelligence_loader.py`

**Supported Formats:**
```
PDF, JPEG/JPG, PNG, BMP, TIFF, HEIF, DOCX, XLSX, PPTX, HTML
```

**Models Available:**
- `prebuilt-layout` (default) - Layout analysis
- `prebuilt-document` - General document analysis
- `prebuilt-invoice` - Invoice-specific
- `prebuilt-receipt` - Receipt-specific
- See: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/

**Key Features:**
```python
# Configuration
client = DocumentIntelligenceClient(endpoint, credential)

# Analysis
poller = client.begin_analyze_document(
    model="prebuilt-layout",
    body=file_content,
    output_content_format="markdown"  # or "text"
)
result = poller.result()

# Output contains:
# - result.content (full text in markdown/text)
# - result.figures (list of figures with bounding boxes)
# - result.tables (list of tables)
# - result.pages (page information)
```

**Processing Pipeline:**
1. **Extract Figures:** Use bounding box to crop images
2. **Caption Figures:** Send to VLM endpoint (GPT-4V)
3. **Extract Tables:** Convert from OCR format to markdown
4. **Clean Text:** Remove figure/table references from main text
5. **Create Documents:** Separate docs for text/tables/figures

**Figure Extraction Process:**
```python
for figure_desc in result.get("figures", []):
    # Get bounding box (polygon coordinates)
    polygon = figure_desc["boundingRegions"][0]["polygon"]

    # Convert to normalized coordinates
    bbox = [min_x / page_width, min_y / page_height,
            max_x / page_width, max_y / page_height]

    # Crop from original file
    img = crop_image(file_path, bbox, page_number)

    # Convert to base64 for API
    img_base64 = f"data:image/png;base64,{base64_encoded}"

    # Generate caption via GPT-4V
    caption = generate_single_figure_caption(
        figure=img_base64,
        vlm_endpoint=vlm_endpoint
    )
```

---

### 7. **Docling**
**Purpose:** Modern document conversion and structure extraction
**Package:** `docling`
**Files Used In:** `docling_loader.py` (line 14-232)
**Location:** `/home/sshan/kotaemon/libs/kotaemon/kotaemon/loaders/docling_loader.py`

**Supported Formats:**
- PDF, DOCX, PPTX, HTML, and more

**Features:**
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert(file_path)
result_dict = result.document.export_to_dict()

# Structured output with:
# - result_dict["texts"] - Text elements
# - result_dict["tables"] - Table elements
# - result_dict["pictures"] - Figure/image elements
# - result_dict["pages"] - Page metadata
```

**Advanced Processing:**
1. **Extractive Captions:** Get captions provided by Docling
2. **Figure Bounding Boxes:** Extract with coordinate system handling
   - Handles both `TOPLEFT` and `BOTTOMLEFT` coordinate origins
   - Converts between coordinate systems
3. **Generative Captions:** Use VLM for additional descriptions
4. **Table Conversion:** Markdown table format
5. **Coordinate Handling:** Advanced bbox transformation

**Code Example:**
```python
# Extract figures with captions
for figure_obj in result_dict.get("pictures", []):
    # Get caption references
    caption_refs = [c["$ref"] for c in figure_obj["captions"]]

    # Resolve references to actual text
    extractive_captions = []
    for caption_ref in caption_refs:
        text_id = int(caption_ref.split("/")[-1])
        caption_text = result_dict["texts"][text_id]["text"]
        extractive_captions.append(caption_text)

    # Get bounding box with coordinate system handling
    page_no = figure_obj["prov"][0]["page_no"]
    bbox_obj = figure_obj["prov"][0]["bbox"]

    if bbox_obj["coord_origin"] == "BOTTOMLEFT":
        bbox = convert_bbox_bl_tl(bbox, page_width, page_height)

    # Crop and caption
    img = crop_image(file_path, bbox, page_no - 1)
    generative_caption = generate_single_figure_caption(img, vlm_endpoint)

    # Combine captions
    full_caption = "\n".join(extractive_captions + [generative_caption])
```

---

### 8. **FullOCR Pipeline** (Internal HTTP API)
**Purpose:** Table and text extraction via OCR
**Files Used In:** `ocr_loader.py` (line 35-128)
**Location:** `/home/sshan/kotaemon/libs/kotaemon/kotaemon/loaders/ocr_loader.py`

**Default Endpoint:** `http://127.0.0.1:8000/v2/ai/infer/`

**Loaders:**
- **OCRReader** - Full OCR with table extraction
- **ImageReader** - Image OCR results

**Process:**
```python
# Call FullOCR endpoint
resp = requests.post(
    url=ocr_endpoint,
    files={"input": pdf_file},
    data={"job_id": uuid4(), "table_only": use_ocr}
)
ocr_results = resp.json()["result"]

# Also read PDF normally
pdf_page_items = read_pdf_unstructured(file_path)

# Merge OCR results with normal PDF text
tables, texts = parse_ocr_output(ocr_results, pdf_page_items)

# Create documents
documents = [
    Document(text=table_text, metadata={"type": "table", ...})
    for table_text in tables
] + [
    Document(text=text, metadata={...})
    for text in texts
]
```

**Retry Logic:**
- Exponential backoff (multiplier=20, exp_base=2)
- Max 6 retry attempts
- Handles temporary failures gracefully

---

## Document Loaders Overview

### Available Loaders

| Loader | File | Format | Multimodal | Features |
|--------|------|--------|-----------|----------|
| **PDFThumbnailReader** | `pdf_loader.py` | PDF | ❌ Text only | Page thumbnails, simple text |
| **AdobeReader** | `adobe_loader.py` | PDF | ✅ Text + Tables + Figures | GPT-4V captions, high accuracy |
| **AzureAIDocumentIntelligenceLoader** | `azureai_document_intelligence_loader.py` | Multi-format | ✅ Text + Tables + Figures | Layout analysis, VLM captions |
| **DoclingReader** | `docling_loader.py` | Multi-format | ✅ Text + Tables + Figures | Modern structure, extractive captions |
| **OCRReader** | `ocr_loader.py` | PDF | ⚠️ Text + Tables | Table-focused OCR |
| **ImageReader** | `ocr_loader.py` | Images | ❌ Tables only | OCR from images |
| **UnstructuredReader** | `unstructured_loader.py` | Multi-format | ⚠️ Text + basic elements | Universal parser, API or local |
| **DocxReader** | `docx_loader.py` | DOCX | ❌ Text only | Word document parsing |
| **ExcelReader** | `excel_loader.py` | XLSX | ❌ Text only | Spreadsheet parsing |
| **MathpixPDFReader** | `mathpix_loader.py` | PDF | ❌ Math-aware text | Formula preservation |
| **HTMLReader** | `html_loader.py` | HTML | ❌ Text only | HTML parsing |
| **WebReader** | `web_loader.py` | Web URLs | ❌ Text only | Web scraping |
| **TxtReader** | `txt_loader.py` | TXT | ❌ Text only | Plain text |
| **DirectoryReader** | `composite_loader.py` | Multi-file | ⚠️ Mixed | Batch processing |

---

## Processing Methods for Images, Tables, Charts

### 1. **Image/Figure Processing**

#### Flow:
```
PDF/Document
    ↓
Extract Figure Location (Bounding Box)
    ↓
Crop Image from Original File
    ↓
Convert to Base64 PNG
    ↓
Send to VLM (GPT-4-Vision)
    ↓
Get Detailed Caption
    ↓
Store with Metadata
```

#### Code Implementation (Azure DI):
```python
# Extract figures with bounding boxes
for figure_desc in result.get("figures", []):
    # Get page and position
    page_number = figure_desc["boundingRegions"][0]["pageNumber"]
    polygon = figure_desc["boundingRegions"][0]["polygon"]

    # Normalize coordinates
    xs = [polygon[i] for i in range(0, len(polygon), 2)]
    ys = [polygon[i] for i in range(1, len(polygon), 2)]
    bbox = [
        min(xs) / page_width,
        min(ys) / page_height,
        max(xs) / page_width,
        max(ys) / page_height,
    ]

    # Crop from original file
    img = crop_image(file_path, bbox, page_number - 1)

    # Convert to base64
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
    img_base64 = f"data:image/png;base64,{img_base64}"

    # Generate caption via GPT-4V
    caption = generate_single_figure_caption(
        figure=img_base64,
        vlm_endpoint=azure_gpt4v_endpoint
    )

    # Create document
    document = Document(
        text=caption,
        metadata={
            "image_origin": img_base64,
            "type": "image",
            "page_label": page_number,
        }
    )
```

#### Image Captioning Tools:
- **GPT-4-Vision** (via Azure OpenAI)
- Functions: `generate_figure_captions()`, `generate_single_figure_caption()`
- File: `/home/sshan/kotaemon/libs/kotaemon/kotaemon/loaders/utils/adobe.py`

---

### 2. **Table Processing**

#### Flow:
```
PDF/Document
    ↓
Detect Table Structure
    ↓
Extract Table Data (Rows/Columns)
    ↓
Convert to Markdown Format
    ↓
Add Caption/Context
    ↓
Store with Metadata
```

#### Code Implementation (Adobe):
```python
# Extract table paths from Adobe output
for item in elements:
    if re.search(r"/Table(\[\d+\])?$", item["Path"]):
        # Parse table file paths
        file_paths = [Path(output_path) / p for p in item.get("filePaths", [])]

        # Extract table content
        table_content = parse_table_paths(file_paths)

        # Add caption from previous item
        title = prev_item.get("Text", "")
        page_number = item.get("Page", -1) + 1
        table_caption = (
            table_content.replace("|", "").replace("---", "")
            + f"\n(Table in Page {page_number}. {title})"
        )

        # Create document
        document = Document(
            text=table_content,
            metadata={
                "table_origin": table_content,
                "type": "table",
                "page_label": page_number,
            }
        )
```

#### Table Conversion:
- **Markdown Tables:** Standardized format with pipes and dashes
- **Utility:** `make_markdown_table()` function
- Handles: Row/column spans, headers, alignment

#### Table Sources:
- **Adobe:** Native table extraction
- **Azure DI:** Markdown-formatted tables
- **Docling:** Grid-based table conversion
- **OCR:** FullOCR table detection

---

### 3. **Chart Processing**

Charts are handled as **Figures** (images), not special structures:

```python
# Charts are extracted using same figure process:
1. Identify chart as figure element
2. Extract bounding box
3. Crop image
4. Generate visual description via GPT-4V
5. Store with "type": "image" metadata
```

### Special Handling:

#### Mathematical Formulas:
- **MathpixPDFReader:** Preserves LaTeX/MathML formulas
- Useful for research papers, technical documents

#### Layered Documents:
- **Docling:** Handles complex layouts with coordinate system conversion
- **Azure DI:** Form recognition for structured documents

---

## Integration Architecture

### Metadata Standard

All loaders output documents with consistent metadata:

```python
Document(
    text="content",
    metadata={
        # Standard fields
        "page_label": int,           # Page number
        "file_name": str,            # Original filename
        "file_path": str,            # Full path

        # Type-specific fields
        "type": "text|table|image",  # Element type

        # Original content (for retrieval)
        "table_origin": str,         # Original table markdown
        "image_origin": str,         # Base64 image data

        # Additional
        **extra_info                 # User-provided metadata
    }
)
```

### Configuration Paths

#### Environment Variables:
```bash
# Azure Document Intelligence
AZUREAI_DOCUMENT_INTELLIGENT_ENDPOINT=<endpoint>
AZUREAI_DOCUMENT_INTELLIGENT_CREDENTIAL=<credential>

# OCR Endpoint
OCR_READER_ENDPOINT=http://127.0.0.1:8000/v2/ai/infer/

# VLM (Vision Language Model) Endpoint
# Used for figure captioning (Azure OpenAI GPT-4V)
AZURE_OPENAI_ENDPOINT=<endpoint>
OPENAI_API_VERSION=<version>
```

#### Configuration File (`.env` or `flowsettings.py`):
```python
# Default file loader selection
DEFAULT_FILE_READER_CLS = {
    ".pdf": "AdobeReader",           # or "AzureAIDocumentIntelligenceLoader"
    ".docx": "DocxReader",
    ".xlsx": "ExcelReader",
    ".html": "HTMLReader",
    ".txt": "TxtReader",
}

# Optional: Custom VLM endpoint
VLM_ENDPOINT = "https://your-gpt4v-endpoint"

# Optional: Figure captioning limits
MAX_FIGURES_TO_CAPTION = 100
```

---

## Comparison: When to Use Which Loader

### Selection Matrix

```
Use Case                          → Best Loader                  Reason
───────────────────────────────────────────────────────────────────────
Fast PDF text extraction          → PDFThumbnailReader          Simple, quick
Simple PDFs (text only)           → UnstructuredReader          Universal, flexible
Academic/Research papers          → MathpixPDFReader            Preserves formulas
Complex documents + OCR           → AzureAIDocumentIntelligenceLoader  Layout analysis
High-quality multimodal           → AdobeReader                 Best figure accuracy
Modern structured documents       → DoclingReader               Advanced parsing
Table-heavy PDFs                  → OCRReader                   Table-focused
Batch processing multiple files   → DirectoryReader             Automated routing
```

### Detailed Comparison

| Feature | Adobe | Azure DI | Docling | Unstructured | OCR |
|---------|-------|----------|---------|--------------|-----|
| Figure Captions | ✅ GPT-4V | ✅ GPT-4V | ✅ Extractive | ❌ | ❌ |
| Table Extraction | ✅ High | ✅ Medium | ✅ Medium | ⚠️ | ✅ |
| Layout Analysis | ✅ | ✅ | ✅ | ⚠️ | ❌ |
| Cost | 💰 API | 💰 API | Free | Free/API | Free |
| Speed | Slow | Medium | Medium | Fast | Medium |
| Accuracy | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

---

## Configuration & Usage

### 1. Using Adobe Reader

```python
from kotaemon.loaders import AdobeReader

reader = AdobeReader(
    vlm_endpoint="https://your-gpt4v-endpoint",
    max_figures_to_caption=100
)

documents = reader.load_data(
    file="path/to/pdf.pdf",
    extra_info={"source": "research"}
)

# Output: List of Documents with text/tables/figures
```

**Requirements:**
```bash
pip install pdfservices-sdk  # Adobe SDK
```

---

### 2. Using Azure Document Intelligence

```python
from kotaemon.loaders import AzureAIDocumentIntelligenceLoader

loader = AzureAIDocumentIntelligenceLoader(
    endpoint="https://your-instance.cognitiveservices.azure.com",
    credential="your-api-key",
    model="prebuilt-layout",
    output_content_format="markdown",
    vlm_endpoint="https://your-gpt4v-endpoint",
    figure_friendly_filetypes=[".pdf", ".jpg", ".png"],
)

documents = loader.load_data(
    file_path="path/to/document.pdf",
    extra_info={"document_type": "invoice"}
)
```

**Supported Models:**
- `prebuilt-layout` (default)
- `prebuilt-document`
- `prebuilt-invoice`
- `prebuilt-receipt`
- `prebuilt-table`

---

### 3. Using Docling Reader

```python
from kotaemon.loaders import DoclingReader

reader = DoclingReader(
    vlm_endpoint="https://your-gpt4v-endpoint",
    max_figure_to_caption=100,
    figure_friendly_filetypes=[".pdf", ".jpg", ".png"],
)

documents = reader.load_data(
    file_path="path/to/document.pdf",
    extra_info={"language": "en"}
)
```

---

### 4. Using Unstructured Reader

```python
from kotaemon.loaders import UnstructuredReader

# Local processing
reader = UnstructuredReader()
documents = reader.load_data(
    file="path/to/document.pdf",
    split_documents=True,
    extra_info={"batch": "001"}
)

# API-based processing
reader = UnstructuredReader(
    url="https://unstructured-api.example.com",
    api_key="your-api-key",
    api=True
)
documents = reader.load_data("path/to/document.pdf")
```

---

## Advanced Features

### Coordinate System Handling (Docling)

```python
def _convert_bbox_bl_tl(bbox, page_width, page_height):
    """Convert bounding box from BOTTOMLEFT to TOPLEFT origin"""
    x0, y0, x1, y1 = bbox
    return [
        x0 / page_width,
        (page_height - y1) / page_height,
        x1 / page_width,
        (page_height - y0) / page_height,
    ]
```

### Merging Multiple Extraction Methods

```python
# Combine OCR results with standard PDF parsing
pdf_text = read_pdf_unstructured(file_path)
ocr_results = call_ocr_endpoint(file_path)

# Merge outputs
tables, texts = parse_ocr_output(ocr_results, pdf_text)

# Create unified documents
documents = format_documents(texts, tables)
```

---

## Summary

### PDF Processing in Kotaemon

```
Incoming PDF
    ↓
[Select Loader Based on Content Type]
    ├─ Text-only? → PDFThumbnailReader
    ├─ Tables heavy? → OCRReader / AzureAIDocumentIntelligenceLoader
    ├─ Formulas? → MathpixPDFReader
    ├─ Complex layout? → DoclingReader / AdobeReader
    └─ Unknown format? → UnstructuredReader
    ↓
[Extract Content]
    ├─ Text blocks (via PDF libraries)
    ├─ Tables (via layout analysis/OCR)
    └─ Figures (via detection + cropping)
    ↓
[Process Multimodal]
    ├─ Text: Store as-is
    ├─ Tables: Convert to Markdown
    └─ Figures: Caption with GPT-4V, store as Base64
    ↓
[Standardize]
    └─ Create Documents with consistent metadata
    ↓
Output: List[Document] ready for indexing
```

---

**Project Location:** `/home/sshan/kotaemon/libs/kotaemon/kotaemon/loaders/`
**Last Updated:** 2025-11-11
