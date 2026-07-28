"""
Basic example of AlfrescoReader retrieving files from the "Sample: Web Site Design
Project" site.

See docs/examples/README.md for instructions on running Alfresco Community Edition
and the OpenDMA endpoint used by this example.

This example requires the optional LlamaIndex file readers package:
```
uv run --with llama-index-readers-file --package llama-index-readers-opendma python docs/examples/11_alfresco_reader.py
```
"""

import sys

from llama_index.readers.opendma import AlfrescoReader

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import llama_index.readers.file  # noqa: F401
except ImportError:
    print(
        "This example requires LlamaIndex's file readers. Run it as:\n"
        "uv run --with llama-index-readers-file --with llama-index-readers-docling --package llama-index-readers-opendma "
        "python docs/examples/11_alfresco_reader.py"
    )
    raise SystemExit(1) from None

try:
    from llama_index.readers.docling import DoclingReader
except ImportError:
    print(
        "This example requires Docling readers. Run it as:\n"
        "uv run --with llama-index-readers-file --with llama-index-readers-docling --package llama-index-readers-opendma "
        "python docs/examples/11_alfresco_reader.py"
    )
    raise SystemExit(1) from None

reader = AlfrescoReader(
    endpoint="http://localhost:7070/opendma/alf",
    username="admin",
    password="admin",
    repository_id="Alfresco",
    sites=["swsdp"],
    file_extractor_per_mimetype={
        "application/msword": DoclingReader(),
    },
)

# Load documents
documents = reader.load_data()
print(f"Loaded {len(documents)} documents")

for doc in documents:
    print(f"\n{'-' * 80}")
    print(f"ID: {doc.id_}")
    print(f"Title: {doc.metadata.get('opendma:Title')}")
    print(f"Content State: {doc.metadata.get('content_state')}")
    print("Metadata:")
    for key, value in doc.metadata.items():
        # Truncate long values for readability
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:97] + "..."
        print(f"  {key}: {value_str}")
    print("Content:")
    print(doc.text[:200] + ("..." if len(doc.text) > 200 else ""))
