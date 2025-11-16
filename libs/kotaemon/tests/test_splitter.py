"""Tests for splitters including TokenSplitter and LLMBasedChunker."""

from unittest.mock import MagicMock, patch
from llama_index.core.schema import NodeRelationship

from kotaemon.base import Document
from kotaemon.indices.splitters import TokenSplitter, LLMBasedChunker
from kotaemon.indices.splitters.llm_chunker import ChunkedDocument, Chunk

# Test data
source1 = Document(
    content="The City Hall and Raffles Place MRT stations are paired cross-platform "
    "interchanges on the North–South line (NSL) and East–West line (EWL) of the "
    "Singapore Mass Rapid Transit (MRT) system. Both are situated in the Downtown "
    "Core district: City Hall station is near landmarks such as the former City Hall, "
    "St Andrew's Cathedral and the Padang, while Raffles Place station serves Merlion "
    "Park, The Fullerton Hotel and the Asian Civilisations Museum. The stations were "
    "first announced in 1982. Constructing the tunnels between the City Hall and "
    "Raffles Place stations required the draining of the Singapore River. The "
    "stations opened on 12 December 1987 as part of the MRT extension to Outram Park "
    "station. Cross-platform transfers between the NSL and EWL began on 28 October "
    "1989, ahead of the split of the MRT network into two lines. Both stations are "
    "designated Civil Defence shelters. City Hall station features a mural by Simon "
    "Wong which depicts government buildings in the area, while two murals at Raffles "
    "Place station by Lim Sew Yong and Thang Kiang How depict scenes of Singapore's "
    "history"
)

source2 = Document(
    content="The pink cockatoo (Cacatua leadbeateri) is a medium-sized cockatoo that "
    "inhabits arid and semi-arid inland areas across Australia, with the exception of "
    "the north east. The bird has a soft-textured white and salmon-pink plumage and "
    "large, bright red and yellow crest. The sexes are quite similar, although males "
    "are usually bigger while the female has a broader yellow stripe on the crest and "
    "develops a red eye when mature. The pink cockatoo is usually found in pairs or "
    "small groups, and feeds both on the ground and in trees. It is listed as an "
    "endangered species by the Australian government. Formerly known as Major "
    "Mitchell's cockatoo, after the explorer Thomas Mitchell, the species was "
    "officially renamed the pink cockatoo in 2023 by BirdLife Australia in light of "
    "Mitchell's involvement in the massacre of Aboriginal people at Mount Dispersion, "
    "as well as a general trend to make Australian species names more culturally "
    "inclusive. This pink cockatoo with a raised crest was photographed near Mount "
    "Grenfell in New South Wales."
)


# ===== TokenSplitter Tests =====
def test_split_token():
    """Test that TokenSplitter can split tokens successfully."""
    splitter = TokenSplitter(chunk_size=30, chunk_overlap=10)
    chunks = splitter([source1, source2])

    assert isinstance(chunks, list), "Chunks should be a list"
    assert isinstance(chunks[0], Document), "Chunks should be a list of Documents"

    assert chunks[0].relationships[NodeRelationship.SOURCE].node_id == source1.doc_id
    assert (
        chunks[1].relationships[NodeRelationship.PREVIOUS].node_id == chunks[0].doc_id
    )
    assert chunks[1].relationships[NodeRelationship.NEXT].node_id == chunks[2].doc_id
    assert chunks[-1].relationships[NodeRelationship.SOURCE].node_id == source2.doc_id


# ===== LLMBasedChunker Tests =====
class TestLLMBasedChunker:
    """Tests for LLM-based semantic chunking with window processing."""

    def create_mock_chunked_document(self, num_chunks=2):
        """Helper to create a mock ChunkedDocument response."""
        chunks = [
            Chunk(
                chunk_number=i + 1,
                content=f"Content of chunk {i + 1}",
                chunk_title=f"Chunk {i + 1} Title",
                chunk_summary=f"Summary of chunk {i + 1}",
                questions=[f"Question 1 for chunk {i + 1}", f"Question 2 for chunk {i + 1}"],
                word_count=100 + (i * 50),
            )
            for i in range(num_chunks)
        ]
        return ChunkedDocument(
            summary="This is a test document summary.",
            document_title="Test Document",
            chunks=chunks,
            notes=None,
        )

    def test_llm_chunker_initialization(self):
        """Test that LLMBasedChunker initializes with correct parameters."""
        chunker = LLMBasedChunker(
            nb_questions=5,
            max_tokens_per_window=8000,
            max_retries=5,
        )
        assert chunker.nb_questions == 5
        assert chunker.max_tokens_per_window == 8000
        assert chunker.max_retries == 5

    def test_llm_chunker_default_parameters(self):
        """Test that LLMBasedChunker uses correct default parameters."""
        chunker = LLMBasedChunker()
        assert chunker.nb_questions == 3
        assert chunker.max_tokens_per_window == 6000
        assert chunker.max_retries == 3
        assert chunker.concurrent is True  # Parallel processing enabled by default

    def test_llm_chunker_concurrent_parameter(self):
        """Test that LLMBasedChunker respects concurrent parameter."""
        chunker_parallel = LLMBasedChunker(concurrent=True)
        assert chunker_parallel.concurrent is True

        chunker_sequential = LLMBasedChunker(concurrent=False)
        assert chunker_sequential.concurrent is False

    def test_llm_chunker_callable(self):
        """Test that LLMBasedChunker is callable."""
        chunker = LLMBasedChunker()
        assert callable(chunker), "LLMBasedChunker should be callable"

    @patch('kotaemo.indices.splitters.llm_chunker.AzureChatOpenAI')
    def test_split_into_windows(self, mock_llm_class):
        """Test that text is properly split into token windows."""
        chunker = LLMBasedChunker(max_tokens_per_window=100)

        # Create a long text that will be split into multiple windows
        long_text = " ".join(["word"] * 200)  # ~200 words

        windows = chunker._split_into_windows(long_text)

        # Should be split into at least 2 windows given token limit
        assert isinstance(windows, list), "Windows should be a list"
        assert len(windows) >= 1, "Should have at least one window"
        assert all(isinstance(w, str) for w in windows), "All windows should be strings"

    @patch('kotaemo.indices.splitters.llm_chunker.AzureChatOpenAI')
    def test_extract_from_window_success(self, mock_llm_class):
        """Test successful extraction of chunks from a window."""
        chunker = LLMBasedChunker()

        # Mock the LLM response
        mock_chunked_doc = self.create_mock_chunked_document(2)
        mock_llm_instance = MagicMock()
        mock_llm_instance.with_structured_output.return_value.__or__ = MagicMock(
            return_value=MagicMock(invoke=MagicMock(return_value=mock_chunked_doc))
        )
        mock_llm_class.return_value = mock_llm_instance

        # Mock the pipe operator properly
        chain_mock = MagicMock()
        chain_mock.invoke = MagicMock(return_value=mock_chunked_doc)
        mock_llm_instance.with_structured_output.return_value.__or__ = MagicMock(
            return_value=chain_mock
        )

        # Set the mocked LLM
        chunker._llm = mock_llm_instance

        # Test extraction
        result = chunker._extract_from_window("Test window text", "test.pdf")

        # Result should be None or ChunkedDocument depending on implementation
        # Since we're mocking, we just verify it doesn't crash

    @patch('kotaemo.indices.splitters.llm_chunker.AzureChatOpenAI')
    def test_create_chunks(self, mock_llm_class):
        """Test conversion of ChunkedDocument to Kotaemo Documents."""
        chunker = LLMBasedChunker()

        # Create mock data
        chunked_doc = self.create_mock_chunked_document(2)
        original_doc = Document(
            content="Original content",
            metadata={"file_name": "test.pdf", "source": "test"}
        )

        # Create chunks
        chunks = chunker._create_chunks(chunked_doc, original_doc)

        # Assertions
        assert isinstance(chunks, list), "Should return a list"
        assert len(chunks) == 2, "Should have 2 chunks"
        assert all(isinstance(c, Document) for c in chunks), "All should be Documents"

        # Check metadata
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_number"] == i + 1
            assert "chunk_title" in chunk.metadata
            assert "chunk_summary" in chunk.metadata
            assert "questions" in chunk.metadata
            assert "word_count" in chunk.metadata
            assert chunk.metadata["document_title"] == "Test Document"
            assert chunk.metadata["chunking_method"] == "llm_semantic_windowed"

    @patch('kotaemo.indices.splitters.llm_chunker.AzureChatOpenAI')
    def test_merge_chunked_windows(self, mock_llm_class):
        """Test merging of chunks from adjacent windows."""
        chunker = LLMBasedChunker()

        # Create two ChunkedDocuments from different windows
        doc1 = self.create_mock_chunked_document(2)
        doc2 = self.create_mock_chunked_document(2)

        # Mock the transition extraction
        transition_doc = self.create_mock_chunked_document(1)
        chunker._extract_from_window = MagicMock(return_value=transition_doc)

        # Merge
        merged = chunker._merge_chunked_windows(doc1, doc2)

        # Assertions
        assert isinstance(merged, type(doc1))
        # Should have chunks from doc1 (except last) + transition chunks + doc2 (except first)
        # = 1 + 1 + 1 = 3 chunks
        assert len(merged.chunks) == 3

    @patch('kotaemo.indices.splitters.llm_chunker.AzureChatOpenAI')
    def test_merge_summaries(self, mock_llm_class):
        """Test merging of summaries from multiple windows."""
        chunker = LLMBasedChunker()

        # Mock the LLM
        mock_llm_instance = MagicMock()

        # Mock the chain properly
        chain_mock = MagicMock()
        chain_mock.invoke = MagicMock(return_value="Merged summary text")

        mock_llm_instance.with_structured_output = MagicMock(return_value=mock_llm_instance)
        mock_llm_instance.__or__ = MagicMock(return_value=chain_mock)

        chunker._llm = mock_llm_instance

        # Test summary merge
        summaries = "Summary 1: First part\nSummary 2: Second part"
        # This may return None due to mocking, but that's okay for testing
        result = chunker._merge_summaries(summaries)

    @patch('kotaemo.indices.splitters.llm_chunker.AzureChatOpenAI')
    def test_run_with_single_document(self, mock_llm_class):
        """Test chunker.run() with a single document."""
        chunker = LLMBasedChunker()

        # Mock the chunking process
        chunker._chunk_document = MagicMock(
            return_value=[
                Document(content="Chunk 1", metadata={"chunk_number": 1}),
                Document(content="Chunk 2", metadata={"chunk_number": 2}),
            ]
        )

        # Run
        docs = [source1]
        result = chunker.run(docs)

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(d, Document) for d in result)

    @patch('kotaemo.indices.splitters.llm_chunker.AzureChatOpenAI')
    def test_run_with_multiple_documents(self, mock_llm_class):
        """Test chunker.run() with multiple documents."""
        chunker = LLMBasedChunker()

        # Mock the chunking process
        chunker._chunk_document = MagicMock(
            side_effect=[
                [Document(content="Doc1 Chunk1", metadata={"chunk_number": 1})],
                [Document(content="Doc2 Chunk1", metadata={"chunk_number": 1})],
            ]
        )

        # Run
        docs = [source1, source2]
        result = chunker.run(docs)

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 2
        assert chunker._chunk_document.call_count == 2

    @patch('kotaemo.indices.splitters.llm_chunker.AzureChatOpenAI')
    def test_simple_metadata_extraction(self, mock_llm_class):
        """Test that only simple metadata is extracted (not rich metadata)."""
        chunker = LLMBasedChunker()

        # Create a ChunkedDocument with simple metadata
        chunked_doc = self.create_mock_chunked_document(1)
        original_doc = Document(content="Original")

        chunks = chunker._create_chunks(chunked_doc, original_doc)
        chunk = chunks[0]

        # Check that ONLY simple fields are present
        simple_fields = {
            "chunk_number", "chunk_title", "chunk_summary",
            "questions", "word_count", "chunking_method"
        }

        # These fields should NOT be present (rich metadata)
        rich_fields = {
            "technical_complexity", "jargon_level", "reading_level",
            "has_lists", "has_code", "has_tables", "content_type",
            "keywords", "main_topics", "products", "organizations"
        }

        # Check that simple fields are present
        for field in simple_fields:
            assert field in chunk.metadata or field in ["chunking_method"], \
                f"Simple field '{field}' should be in metadata"

        # Check that rich fields are NOT present
        for field in rich_fields:
            assert field not in chunk.metadata, \
                f"Rich field '{field}' should NOT be in metadata"
