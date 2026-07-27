"""
Example demonstrating PDF handling with LlamaIndex file readers.

Run the tutorial REST service docker container:
```
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
```
It will provide the tutorial XML repository. Make sure that this service is available by opening
http://localhost:8080/opendma
in a web browser.

This example requires the optional LlamaIndex file readers package:
```
uv run --with llama-index-readers-file --package llama-index-readers-opendma python docs/examples/05_pdf.py
```
"""

import sys

from llama_index.readers.opendma import OpenDMAReader

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from llama_index.readers.file import PDFReader  # noqa: F401
except ImportError:
    print(
        "This example requires LlamaIndex's PDFReader. Run it as:\n"
        "uv run --with llama-index-readers-file --package llama-index-readers-opendma "
        "python docs/examples/05_pdf.py"
    )
    raise SystemExit(1) from None

reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
    document_ids=["opendma-spec-document"],
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
