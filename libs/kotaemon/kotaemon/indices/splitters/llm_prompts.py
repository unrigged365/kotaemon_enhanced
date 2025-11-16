"""LLM prompts for semantic chunking with simple metadata extraction.

This module contains prompts for gk-policy-style semantic chunking:
- Simple metadata: chunk_title, chunk_summary, questions, word_count
- Window-based processing for large documents
- Summary merging across windows
"""

# Chunking prompt for semantic document chunking (gk-policy style)
CHUNKING_PROMPT_TEMPLATE = """
Divide a document into smaller, semantically coherent chunks while preserving the logical flow and meaning within each chunk. You must preserve the content of the document.

# Task Details

- **Objective**: Create meaningful sub-sections or chunks from a larger document, each covering a distinct and coherent topic or idea.
- **Constraints**: Maintain semantic coherence within each chunk. Do not break sentences or paragraphs mid-thought, and ensure related ideas are grouped together. Ensure that the content from the document is preserved in one of the chunks.
- **Considerations**:
  - Chunk size: Aim for 500 to 1000 words per chunk.
  - Respect natural breaks: Prefer logical segment boundaries such as section headers, paragraph breaks, or changes in topics.
  - Avoid redundancy: Do not repeat content across chunks unless necessary to maintain coherence.
  - Handle edge cases where:
    - Input content has no clear semantic transitions (offer a single chunk).
    - Logical breaks (like section headers) lead to chunks under the size range (use the entirety of the section as a single chunk).

# Steps

1. **Understand the Content**:
   - Read the file name.
   - Read the document and understand its content.
   - Parse and analyze the document for its structure and themes (e.g., via headings, key phrases, or thematic changes).

2. **Determine Boundaries**:
   - Section-Based: Divide the text according to natural sections and subtopics.
   - Topical Cohesion: Each chunk covers a distinct concept or theme. Identify logical chunks based on topic shifts, paragraph grouping, and overall semantic flow.
   - Make sure the boundaries keep the WHOLE content of the document.
   - The only part you may leave out is the Content section if it is only a list of section titles.

3. **Refine the Chunks**:
   - Ensure every chunk is self-contained and cohesive without disrupting its meaning. Each chunk should be understood independently.
   - Maintain an appropriate size range without exceeding limits or breaking semantic integrity.

4. **Generate a chunk title**
- The title should reflect the general idea or topic contained in the chunk, what it is about.

5. **Generate questions**
- Attach a list of at most {nb_questions} questions that you think the chunk contains the answer to.

6. **Verify Sequence**:
   - Retain the document's logical flow between chunks.
   - Preserve the entirety of the document content as much as possible.

7. **Short document summary**
- Generate a short summary of what the full document is about.
- The summary should be around 100 words maximum.

8. **Generate the title of the document**:
- Based on the content of the document, infer a title for the document.
- It can be inferred from the name of the file or generated from the summary.

# Output Format

The output should be presented as JSON with the following structure:

```json
{{
  "summary": "Summary of the whole document, max 100 words",
  "document_title": "Inferred or generated title of the document",
  "chunks": [
    {{
      "chunk_number": 1,
      "content": "<Text of chunk 1>",
      "chunk_title": "<Title for chunk 1>",
      "chunk_summary": "<2-3 sentence summary>",
      "questions": ["question 1 answered by chunk 1", "question 2 answered by chunk 1", ...],
      "word_count": <Word count of chunk 1>
    }},
    {{
      "chunk_number": 2,
      "content": "<Text of chunk 2>",
      "chunk_title": "<Title for chunk 2>",
      "chunk_summary": "<2-3 sentence summary>",
      "questions": ["question 1 answered by chunk 2", "question 2 answered by chunk 2", ...],
      "word_count": <Word count of chunk 2>
    }},
    ...
  ],
  "notes": "Optional commentary on semantic boundaries or edge cases if encountered."
}}
```

# Final Notes

- If the document is highly technical or lacks clear thematic shifts, add clarifying notes when dividing chunks.
- For documents with pre-existing section headers, use these as guides for starting and ending chunks, when feasible.
- Remember that it is important to not lose content from the document while dividing into chunks.

# Input

File name: "{filename}"
Text:
\"\"\"
{text}
\"\"\"

# Instructions

- Preserve ALL content - do not omit any information
- Generate {nb_questions} relevant questions per chunk
- Output valid JSON only
- Ensure chunk boundaries respect semantic meaning
""".strip()


# Prompt for merging summaries from multiple windows
MERGE_SUMMARIES_PROMPT_TEMPLATE = """
You are a helpful assistant that merges summaries of consecutive parts of a document into a single summary for the entire document.

Here are the summaries of the consecutive parts of the document:
{concatenated_summaries}

Please merge these summaries into a single, coherent summary for the entire document.
Keep the same order of length for the merged summary.
""".strip()


# Keep old prompts for backwards compatibility (deprecated)
GENERIC_CHUNKING_PROMPT = CHUNKING_PROMPT_TEMPLATE
MINIMAL_CHUNKING_PROMPT = CHUNKING_PROMPT_TEMPLATE
