"""Database models for LLM-extracted chunk metadata (gk-policy style - simplified).

This module defines the schema for storing simple metadata extracted from chunks
using LLM-based semantic chunking with window processing.

Simple metadata fields (gk-policy approach):
- chunk_title: Descriptive title for the chunk
- chunk_summary: 2-3 sentence summary
- questions: Array of questions this chunk answers
- word_count: Number of words in the chunk
"""

from datetime import datetime
from typing import Optional

from ktem.db.engine import engine
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableList
from tzlocal import get_localzone

Base = declarative_base()


class LLMChunkMetadata(Base):
    """Metadata for chunks created with LLM-based semantic chunking.

    This table stores simple, essential metadata extracted by the LLM during windowed
    semantic chunking. It complements the standard chunk storage in DocStore and VectorStore.

    Follows gk-policy-chatbot's simpler approach with focus on retrieval-critical fields:
    - Chunk identification (title, summary, number)
    - Question-answer pairs (critical for retrieval)
    - Basic metrics (word count)
    - Technical metadata (LLM model, timestamp)
    """

    __tablename__ = "ktem__llm_chunk_metadata"

    # Primary key and relationships
    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String, unique=True, index=True, nullable=False)
    """Unique chunk identifier matching the target_id in Index table"""

    source_id = Column(String, index=True, nullable=False)
    """Source file identifier"""

    created_at = Column(DateTime(timezone=True), default=datetime.now(get_localzone()))
    """When this metadata was created"""

    # === Content Identification (Essential) ===
    chunk_number = Column(Integer)
    """Sequential chunk number within the document"""

    chunk_title = Column(String(500))
    """Descriptive title for the chunk"""

    chunk_summary = Column(Text)
    """2-3 sentence summary of chunk content"""

    word_count = Column(Integer)
    """Number of words in the chunk"""

    # === Question-Answer Pairs (CRITICAL for retrieval) ===
    questions = Column(MutableList.as_mutable(JSON), default=[])
    """Array of questions this chunk can answer - enables question-based retrieval"""

    # === Technical metadata ===
    llm_model = Column(String(100))
    """Name of LLM model used for extraction (e.g., 'gpt-5-mini')"""

    extraction_timestamp = Column(DateTime(timezone=True), default=datetime.now(get_localzone()))
    """When metadata was extracted"""

    def __repr__(self):
        return (
            f"<LLMChunkMetadata("
            f"chunk_id='{self.chunk_id}', "
            f"title='{self.chunk_title}'"
            f")>"
        )

    def to_dict(self) -> dict:
        """Convert metadata to dictionary for storage in DocStore.

        Returns:
            Dictionary with simple metadata fields
        """
        return {
            # Content Identification
            "chunk_number": self.chunk_number,
            "chunk_title": self.chunk_title,
            "chunk_summary": self.chunk_summary,
            "word_count": self.word_count,
            # Question-Answer Pairs
            "questions": self.questions,
            # Technical
            "llm_model": self.llm_model,
            "extraction_timestamp": self.extraction_timestamp.isoformat() if self.extraction_timestamp else None,
        }

    @classmethod
    def from_llm_response(
        cls, chunk_data: dict, chunk_id: str, source_id: str, llm_model: str = "gpt-5-mini"
    ):
        """Create metadata record from LLM chunking response.

        Args:
            chunk_data: Dictionary from LLM chunking response
            chunk_id: Unique chunk identifier
            source_id: Source file identifier
            llm_model: Name of LLM model used

        Returns:
            LLMChunkMetadata instance
        """
        return cls(
            chunk_id=chunk_id,
            source_id=source_id,
            llm_model=llm_model,
            # Content Identification
            chunk_number=chunk_data.get("chunk_number"),
            chunk_title=chunk_data.get("chunk_title", "")[:500],  # Truncate to column size
            chunk_summary=chunk_data.get("chunk_summary", ""),
            word_count=chunk_data.get("word_count"),
            # Question-Answer Pairs
            questions=chunk_data.get("questions", []),
        )


# Create the table
LLMChunkMetadata.metadata.create_all(engine)
