"""OpenDMA tools for LlamaIndex."""

from llama_index.tools.opendma.base import (
    AlfrescoToolSpec,
    DocumentumToolSpec,
    FileNetP8ToolSpec,
    OnBaseToolSpec,
    OpenDMAToolSpec,
)

__version__ = "0.2.0"

__all__ = [
    "AlfrescoToolSpec",
    "DocumentumToolSpec",
    "FileNetP8ToolSpec",
    "OnBaseToolSpec",
    "OpenDMAToolSpec",
]
