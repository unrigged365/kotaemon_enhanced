"""Database migration script for LLM chunk metadata table.

Run this script to create the LLM chunk metadata table if it doesn't exist.
This table stores comprehensive metadata extracted during LLM-based chunking.

Usage:
    python -m ktem.index.file.migrate_llm_metadata
"""

import logging

from ktem.db.engine import engine
from ktem.index.file.llm_chunk_metadata import LLMChunkMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Create or update the LLM chunk metadata table."""
    try:
        logger.info("Creating LLM chunk metadata table...")
        LLMChunkMetadata.metadata.create_all(engine)
        logger.info("✓ LLM chunk metadata table created successfully")
        logger.info(f"✓ Table name: {LLMChunkMetadata.__tablename__}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create table: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    if success:
        print("\nMigration completed successfully!")
        print("You can now use LLM-based chunking with metadata extraction.")
    else:
        print("\nMigration failed. Please check the error messages above.")
