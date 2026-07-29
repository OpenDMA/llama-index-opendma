"""LlamaIndex retrievers for OpenDMA."""

from __future__ import annotations

from llama_index.retrievers.opendma.base import (
    AlfrescoRetriever,
    DocumentumRetriever,
    FileNetP8Retriever,
    OnBaseRetriever,
    OpenDMARetriever,
)

__version__ = "0.2.0.dev1"

__all__ = [
    "AlfrescoRetriever",
    "DocumentumRetriever",
    "FileNetP8Retriever",
    "OnBaseRetriever",
    "OpenDMARetriever",
]
