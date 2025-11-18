"""LLM-based semantic chunker with window-based processing.

Implements gk-policy-chatbot's approach:
- Window-based processing for large documents
- LangChain structured output parsing
- Transition re-chunking for semantic boundaries
- Summary merging across windows
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import tiktoken
import urllib3
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate as LCPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from kotaemon.base import Document

from .llm_prompts import (
    CHUNKING_PROMPT_TEMPLATE,
    MERGE_SUMMARIES_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)

# Disable SSL warnings for development (comment out or use env var for production)
try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

# Set environment variables to disable SSL verification for tiktoken downloads
# This is for development only and should be avoided in production
if os.getenv("KOTAEMON_DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    os.environ["CURL_CA_BUNDLE"] = ""


class Chunk(BaseModel):
    """Representation of a chunk of text from a document."""

    chunk_number: int
    content: str
    chunk_title: str
    chunk_summary: str
    questions: list[str]
    word_count: Optional[int] = None


class ChunkedDocument(BaseModel):
    """Representation of a document that has been divided into chunks."""

    summary: str
    document_title: str
    chunks: list[Chunk]
    notes: Optional[str] = None


class LLMBasedChunker:
    """LLM-based semantic chunker with window-based processing.

    Features:
    - Handles large documents by splitting into token windows
    - Uses LangChain's structured output for reliable JSON parsing
    - Re-chunks transition boundaries for semantic coherence
    - Merges summaries across windows for unified document summary
    - Extracts simple metadata: chunk_title, chunk_summary, questions, word_count

    Note: Doesn't explicitly inherit from BaseSplitter (to avoid circular imports),
    but implements the same interface via duck typing.
    """

    nb_questions: int = 3
    max_tokens_per_window: int = 6000
    max_retries: int = 3
    concurrent: bool = True

    def __init__(
        self,
        nb_questions: int = 3,
        max_tokens_per_window: int = 6000,
        max_retries: int = 3,
        concurrent: bool = True,
    ):
        """Initialize chunker with configuration.

        Args:
            nb_questions: Number of questions to generate per chunk
            max_tokens_per_window: Maximum tokens per processing window (default: 6000)
            max_retries: Max retry attempts for LLM calls
            concurrent: Enable parallel processing of windows (default: True)
        """
        self.nb_questions = nb_questions
        self.max_tokens_per_window = max_tokens_per_window
        self.max_retries = max_retries
        self.concurrent = concurrent

        # Initialize LLM - using AzureChatOpenAI from environment
        self._llm = None

    def __call__(self, documents: List[Document]) -> List[Document]:
        """Make the chunker callable (delegates to run()).

        This is needed because the pipeline calls the splitter like a function:
        all_chunks = self.splitter(text_docs)
        """
        return self.run(documents)

    @property
    def llm(self):
        """Lazily initialize Azure OpenAI LLM."""
        if self._llm is None:
            self._llm = AzureChatOpenAI(
                deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-5-mini"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("OPENAI_API_VERSION", "2024-12-01-preview"),
                temperature=1.0,  # gpt-5-mini only supports temperature=1
            )
        return self._llm

    def run(self, documents: List[Document]) -> List[Document]:
        """Split documents into semantic chunks with metadata.

        Args:
            documents: List of Document objects to chunk

        Returns:
            List of Document objects representing chunks with metadata
        """
        all_chunks = []
        start_time = time.time()

        if self.concurrent and len(documents) > 1:
            # Parallel processing of multiple documents using ThreadPoolExecutor
            print(f"\n{'=' * 80}")
            print(f"⏳ PROCESSING {len(documents)} DOCUMENTS IN PARALLEL")
            print(f"{'=' * 80}\n")

            with ThreadPoolExecutor() as executor:
                futures = []
                for i, doc in enumerate(documents):
                    filename = doc.metadata.get("file_name", f"document_{i+1}")
                    logger.info(f"Submitting document {i + 1}/{len(documents)}: {filename}")
                    future = executor.submit(self._chunk_document, doc)
                    futures.append((i, filename, future))

                # Collect results as they complete
                doc_num = 1
                for i, filename, future in futures:
                    try:
                        chunks = future.result()
                        all_chunks.extend(chunks)
                        print(f"✓ Document {doc_num}/{len(documents)}: {filename} completed")
                        doc_num += 1
                    except Exception as e:
                        logger.error(
                            f"Error chunking document {filename}: {e}"
                        )
                        print(f"✗ Document {doc_num}/{len(documents)}: {filename} failed")
                        doc_num += 1
                        # Fall back to returning original document
                        all_chunks.append(documents[i])
        else:
            # Sequential processing (fallback or single document)
            print(f"\n{'=' * 80}")
            if len(documents) == 1:
                print(f"⏳ PROCESSING 1 DOCUMENT")
            else:
                print(f"⏳ PROCESSING {len(documents)} DOCUMENTS (Sequential)")
            print(f"{'=' * 80}\n")

            for i, doc in enumerate(documents):
                try:
                    chunks = self._chunk_document(doc)
                    all_chunks.extend(chunks)
                    filename = doc.metadata.get("file_name", f"document_{i+1}")
                    print(f"✓ Document {i + 1}/{len(documents)}: {filename} completed")
                except Exception as e:
                    filename = doc.metadata.get("file_name", f"document_{i+1}")
                    logger.error(
                        f"Error chunking document {filename}: {e}"
                    )
                    print(f"✗ Document {i + 1}/{len(documents)}: {filename} failed")
                    # Fall back to returning original document
                    all_chunks.append(doc)

        total_time = time.time() - start_time
        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents in {total_time:.2f}s")

        # Print completion message
        print(f"\n{'=' * 80}")
        print(f"✅ LLM SEMANTIC CHUNKING COMPLETED SUCCESSFULLY")
        print(f"{'=' * 80}")
        print(f"Total Documents Processed: {len(documents)}")
        print(f"Total Chunks Created: {len(all_chunks)}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Processing Mode: {'Parallel (ThreadPoolExecutor)' if self.concurrent and len(documents) > 1 else 'Sequential'}")
        print(f"{'=' * 80}\n")

        return all_chunks

    def _chunk_document(self, doc: Document) -> List[Document]:
        """Chunk a single document using windowed LLM processing.

        Args:
            doc: Document to chunk

        Returns:
            List of Document chunks with metadata
        """
        filename = doc.metadata.get("file_name", "unknown.pdf")
        text = doc.text

        # Calculate actual token count
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = encoding.encode(text)
        num_tokens = len(tokens)

        print(f"\n{'🤖' * 40}")
        print(f"LLM SEMANTIC CHUNKING IN PROGRESS")
        print(f"{'🤖' * 40}")
        print(f"File: {filename}")
        print(f"Size: {len(text)} characters | {num_tokens} tokens")
        print(f"Questions per chunk: {self.nb_questions}")
        print(f"Max window size: {self.max_tokens_per_window} tokens")
        if num_tokens <= self.max_tokens_per_window:
            print(f"Status: Document is smaller than max window size (1 window)")
        else:
            num_windows = (num_tokens // self.max_tokens_per_window) + 1
            print(f"Status: Processing {num_windows} windows...")
        print(f"{'🤖' * 40}\n")

        logger.info(f"Chunking '{filename}' with LLM ({len(text)} chars)")
        start_time = time.time()

        # Step 1: Split into windows
        print(f"⏳ Step 1/6: Splitting into windows...")
        step1_start = time.time()
        windows = self._split_into_windows(text)
        step1_time = time.time() - step1_start
        logger.info(f"Split document into {len(windows)} windows")
        print(f"✓ Step 1 completed in {step1_time:.2f}s ({len(windows)} windows)\n")

        # Step 2: Process each window
        print(f"⏳ Step 2/6: Processing {len(windows)} window(s) with LLM...")
        if self.concurrent:
            print(f"   Mode: Parallel (ThreadPoolExecutor)")
        else:
            print(f"   Mode: Sequential")
        print()

        step2_start = time.time()
        chunked_window_documents = []

        if self.concurrent:
            # Parallel processing using ThreadPoolExecutor (Kotaemon pattern)
            with ThreadPoolExecutor() as executor:
                futures = []
                for i, window_text in enumerate(windows):
                    logger.info(f"Submitting window {i + 1}/{len(windows)} to executor")
                    future = executor.submit(self._extract_from_window, window_text, filename)
                    futures.append((i, future))

                # Collect results as they complete
                for i, future in futures:
                    window_start = time.time()
                    try:
                        chunked_window = future.result()
                        window_time = time.time() - window_start
                        print(f"  Window {i + 1}/{len(windows)}: {window_time:.2f}s")
                        if chunked_window:
                            chunked_window_documents.append(chunked_window)
                    except Exception as e:
                        window_time = time.time() - window_start
                        logger.error(f"Error processing window {i + 1}: {e}")
                        print(f"  Window {i + 1}/{len(windows)}: ERROR ({window_time:.2f}s)")
        else:
            # Sequential processing (fallback)
            for i, window_text in enumerate(windows):
                window_start = time.time()
                logger.info(f"Processing window {i + 1}/{len(windows)}")
                chunked_window = self._extract_from_window(
                    window_text=window_text, filename=filename
                )
                window_time = time.time() - window_start
                print(f"  Window {i + 1}/{len(windows)}: {window_time:.2f}s")
                if chunked_window:
                    chunked_window_documents.append(chunked_window)

        step2_time = time.time() - step2_start

        if not chunked_window_documents:
            logger.warning(f"No chunks extracted from {filename}")
            return [doc]

        print(f"✓ Step 2 completed in {step2_time:.2f}s\n")

        # Step 3: Merge chunks across windows
        print(f"⏳ Step 3/6: Merging windows...")
        step3_start = time.time()
        merged_document = chunked_window_documents[0]
        for i in range(1, len(chunked_window_documents)):
            logger.info(f"Merging window {i - 1} and window {i}")
            merged_document = self._merge_chunked_windows(
                merged_document, chunked_window_documents[i]
            )
        step3_time = time.time() - step3_start
        print(f"✓ Step 3 completed in {step3_time:.2f}s\n")

        # Step 4: Merge summaries
        print(f"⏳ Step 4/6: Merging summaries...")
        step4_start = time.time()
        concatenated_summaries = "\n".join(
            [
                f"Summary {i + 1}: {doc.summary}"
                for i, doc in enumerate(chunked_window_documents)
            ]
        )
        final_summary = self._merge_summaries(concatenated_summaries)
        if final_summary:
            merged_document.summary = final_summary
        step4_time = time.time() - step4_start
        print(f"✓ Step 4 completed in {step4_time:.2f}s\n")

        # Step 5: Re-number chunks sequentially
        print(f"⏳ Step 5/6: Re-numbering chunks...")
        step5_start = time.time()
        for i, chunk in enumerate(merged_document.chunks, 1):
            chunk.chunk_number = i
        step5_time = time.time() - step5_start
        print(f"✓ Step 5 completed in {step5_time:.2f}s\n")

        # Step 6: Convert to Kotaemo Document objects
        print(f"⏳ Step 6/6: Converting to Kotaemo Documents...")
        step6_start = time.time()
        chunks = self._create_chunks(merged_document, doc)
        step6_time = time.time() - step6_start
        print(f"✓ Step 6 completed in {step6_time:.2f}s\n")

        total_time = time.time() - start_time

        print(f"\n{'✅' * 40}")
        print(f"LLM SEMANTIC CHUNKING COMPLETED")
        print(f"{'✅' * 40}")
        print(f"File: {filename}")
        print(f"Chunks created: {len(chunks)}")
        print(f"Total questions: {sum(len(c.metadata.get('questions', [])) for c in chunks)}")
        print(f"\n📊 TIMING BREAKDOWN:")
        print(f"  Step 1 (Split windows):    {step1_time:.2f}s")
        print(f"  Step 2 (LLM extraction):   {step2_time:.2f}s  ← Usually slowest")
        print(f"  Step 3 (Merge windows):    {step3_time:.2f}s")
        print(f"  Step 4 (Merge summaries):  {step4_time:.2f}s")
        print(f"  Step 5 (Re-numbering):     {step5_time:.2f}s")
        print(f"  Step 6 (Document convert): {step6_time:.2f}s")
        print(f"  {'─' * 38}")
        print(f"  TOTAL TIME:                {total_time:.2f}s")
        print(f"{'✅' * 40}\n")

        logger.info(f"Successfully chunked '{filename}' into {len(chunks)} chunks in {total_time:.2f}s")
        return chunks

    def _split_into_windows(self, text: str) -> List[str]:
        """Split text into token-based windows.

        Args:
            text: The full text to split

        Returns:
            List of window texts
        """
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        tokens = encoding.encode(text)
        num_tokens = len(tokens)

        logger.info(f"Total tokens: {num_tokens}")

        # Calculate number of windows needed
        num_windows = (num_tokens // self.max_tokens_per_window) + 1
        if num_windows == 1:
            return [text]

        max_tokens_per_window_adjusted = num_tokens // num_windows

        windows = []
        for i in range(num_windows):
            start = i * max_tokens_per_window_adjusted
            end = (
                min(start + max_tokens_per_window_adjusted, num_tokens)
                if i < num_windows - 1
                else num_tokens
            )
            window_tokens = tokens[start:end]
            window_text = encoding.decode(window_tokens)
            windows.append(window_text)

        logger.info(f"Split into {len(windows)} windows")
        return windows

    def _extract_from_window(
        self, window_text: str, filename: str
    ) -> Optional[ChunkedDocument]:
        """Extract chunks from a single window using LLM.

        Args:
            window_text: The window text to chunk
            filename: Original filename for context

        Returns:
            ChunkedDocument or None if extraction fails
        """
        try:
            # Create LangChain prompt template
            prompt_template = LCPromptTemplate(
                input_variables=["filename", "text", "nb_questions"],
                template=CHUNKING_PROMPT_TEMPLATE,
            )

            # Create chain with structured output
            llm_structured = self.llm.with_structured_output(ChunkedDocument)
            llm_chain = prompt_template | llm_structured

            # Invoke chain
            chunked_document = llm_chain.invoke(
                {
                    "filename": filename,
                    "text": window_text,
                    "nb_questions": self.nb_questions,
                }
            )
            return chunked_document

        except Exception as e:
            logger.error(f"Error extracting chunks from window: {e}")
            return None

    def _merge_chunked_windows(
        self, doc1: ChunkedDocument, doc2: ChunkedDocument
    ) -> ChunkedDocument:
        """Merge chunks from two adjacent windows with transition re-chunking.

        Args:
            doc1: First chunked document
            doc2: Second chunked document

        Returns:
            Merged ChunkedDocument
        """
        if not doc1 or not doc2:
            return doc1 or doc2

        # Re-chunk the transition boundary
        last_chunk_from_first = doc1.chunks[-1]
        first_chunk_from_second = doc2.chunks[0]

        transition_text = (
            last_chunk_from_first.content + " " + first_chunk_from_second.content
        )
        transition_chunked = self._extract_from_window(transition_text, "transition")

        # Merge chunks
        if transition_chunked:
            merged_chunks = (
                doc1.chunks[:-1] + transition_chunked.chunks + doc2.chunks[1:]
            )
        else:
            merged_chunks = doc1.chunks + doc2.chunks

        return ChunkedDocument(
            summary="",  # Will be merged later
            document_title=doc1.document_title,
            chunks=merged_chunks,
            notes=None,
        )

    def _merge_summaries(self, concatenated_summaries: str) -> Optional[str]:
        """Merge summaries from all windows into one.

        Args:
            concatenated_summaries: All window summaries concatenated

        Returns:
            Merged summary or None if merge fails
        """
        try:
            prompt_template = LCPromptTemplate(
                input_variables=["concatenated_summaries"],
                template=MERGE_SUMMARIES_PROMPT_TEMPLATE,
            )

            llm_chain = prompt_template | self.llm | StrOutputParser()
            merged_summary = llm_chain.invoke(
                {"concatenated_summaries": concatenated_summaries}
            )
            return merged_summary

        except Exception as e:
            logger.error(f"Error merging summaries: {e}")
            return None

    def _create_chunks(
        self, chunked_document: ChunkedDocument, original_doc: Document
    ) -> List[Document]:
        """Convert ChunkedDocument to Kotaemo Document objects.

        Args:
            chunked_document: The chunked document from LLM
            original_doc: Original document for metadata preservation

        Returns:
            List of Kotaemo Document objects
        """
        chunks = []
        document_metadata = {
            "document_title": chunked_document.document_title,
            "document_summary": chunked_document.summary,
        }

        for chunk in chunked_document.chunks:
            metadata = {
                **original_doc.metadata,  # Preserve original metadata
                **document_metadata,  # Add document-level metadata
                # Simple chunk metadata (gk-policy style)
                "chunk_number": chunk.chunk_number,
                "chunk_title": chunk.chunk_title,
                "chunk_summary": chunk.chunk_summary,
                "word_count": chunk.word_count,
                "questions": json.dumps(chunk.questions),  # Convert list to JSON string for vector store
                # Chunking method indicator
                "chunking_method": "llm_semantic_windowed",
            }

            # Remove None values
            metadata = {k: v for k, v in metadata.items() if v is not None}

            chunk_doc = Document(text=chunk.content, metadata=metadata)
            chunks.append(chunk_doc)

        return chunks
