"""
Basic example of AlfrescoRetriever performing a full-text search in the "Sample:
Web Site Design Project" site.

See docs/examples/README.md for instructions on running Alfresco Community Edition
and the OpenDMA endpoint used by this example.

This example requires the optional LlamaIndex file readers and Docling packages:
```
uv run --with llama-index-readers-file --with llama-index-readers-docling --package llama-index-retrievers-opendma python docs/examples/12_alfresco_retriever.py
```
"""

import sys

from llama_index.retrievers.opendma import AlfrescoRetriever

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import llama_index.readers.file  # noqa: F401
except ImportError:
    print(
        "This example requires LlamaIndex's file readers. Run it as:\n"
        "uv run --with llama-index-readers-file --with llama-index-readers-docling "
        "--package llama-index-retrievers-opendma python docs/examples/12_alfresco_retriever.py"
    )
    raise SystemExit(1) from None

try:
    from llama_index.readers.docling import DoclingReader
except ImportError:
    print(
        "This example requires Docling readers. Run it as:\n"
        "uv run --with llama-index-readers-file --with llama-index-readers-docling "
        "--package llama-index-retrievers-opendma python docs/examples/12_alfresco_retriever.py"
    )
    raise SystemExit(1) from None

retriever = AlfrescoRetriever(
    endpoint="http://localhost:7070/opendma/alf",
    username="admin",
    password="admin",
    repository_id="Alfresco",
    sites=["swsdp"],
    file_extractor_per_mimetype={
        "application/msword": DoclingReader(),
    },
)

# Retrieve nodes
nodes = retriever.retrieve("meeting notes")
print(f"Retrieved {len(nodes)} nodes")

for node_with_score in nodes:
    node = node_with_score.node
    print(f"\n{'-' * 80}")
    print(f"ID: {node.node_id}")
    print(f"Title: {node.metadata.get('opendma:Title')}")
    print(f"Content State: {node.metadata.get('content_state')}")
    print("Metadata:")
    for key, value in node.metadata.items():
        # Truncate long values for readability
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:97] + "..."
        print(f"  {key}: {value_str}")
    print("Content:")
    text = node.get_content()
    print(text[:200] + ("..." if len(text) > 200 else ""))
