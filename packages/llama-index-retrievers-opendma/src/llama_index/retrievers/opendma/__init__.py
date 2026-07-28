"""LlamaIndex retrievers for OpenDMA."""

from __future__ import annotations

from llama_index.retrievers.opendma.base import (
    AlfrescoRetriever,
    DocumentumRetriever,
    FileNetP8Retriever,
    OnBaseRetriever,
    OpenDMARetriever,
)

__version__ = "0.1.0"

__all__ = [
    "AlfrescoRetriever",
    "DocumentumRetriever",
    "FileNetP8Retriever",
    "OnBaseRetriever",
    "OpenDMARetriever",
]
