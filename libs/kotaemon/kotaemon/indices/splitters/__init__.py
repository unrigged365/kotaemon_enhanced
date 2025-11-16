from ..base import DocTransformer, LlamaIndexDocTransformerMixin


class BaseSplitter(DocTransformer):
    """Represent base splitter class"""

    ...


# Import LLM-based chunker
# Note: LLMBasedChunker doesn't explicitly inherit from BaseSplitter to avoid circular imports,
# but it implements the same interface (run() method) so it works via duck typing
try:
    from .llm_chunker import LLMBasedChunker
except Exception as e:
    # Log the ACTUAL error so we can see what's wrong
    import traceback
    print(f"\n{'!'*80}")
    print(f"ERROR IMPORTING LLMBasedChunker:")
    print(f"{'!'*80}")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
    print(f"Full traceback:")
    traceback.print_exc()
    print(f"{'!'*80}\n")
    # LLM chunker may not be available in all environments
    LLMBasedChunker = None


class TokenSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 20,
        separator: str = " ",
        **params,
    ):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=separator,
            **params,
        )

    def _get_li_class(self):
        from llama_index.core.text_splitter import TokenTextSplitter

        return TokenTextSplitter


class SentenceWindowSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    def __init__(
        self,
        window_size: int = 3,
        window_metadata_key: str = "window",
        original_text_metadata_key: str = "original_text",
        **params,
    ):
        super().__init__(
            window_size=window_size,
            window_metadata_key=window_metadata_key,
            original_text_metadata_key=original_text_metadata_key,
            **params,
        )

    def _get_li_class(self):
        from llama_index.core.node_parser import SentenceWindowNodeParser

        return SentenceWindowNodeParser
