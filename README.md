# LlamaIndex OpenDMA

OpenDMA integrations for [LlamaIndex](https://www.llamaindex.ai/).

OpenDMA is a vendor-neutral abstraction layer for enterprise content management
systems. It provides a common API for repositories such as Alfresco, CMOD,
Documentum, FileNet P8, OnBase, SharePoint, and other ECM or document management
platforms.

This repository contains LlamaIndex integration packages for OpenDMA. Use these
packages when you want to build LlamaIndex applications, RAG pipelines, or
content analysis workflows on top of documents stored in ECM systems.

## Features

- Load documents from an OpenDMA REST service by document ID, folder ID, or query.
- Retrieve documents from OpenDMA search results through LlamaIndex's retriever API.
- Use specialized retrievers for Alfresco, Documentum, FileNet P8, and OnBase.
- Preserve OpenDMA and repository metadata on every LlamaIndex `Document`
  object and retrieved node.
- Process richer document formats with the optional `llama-index-readers-file`
  package.

## Packages

- `llama-index-readers-opendma`: reader integration for loading ECM content
  in ingestion pipelines
- `llama-index-retrievers-opendma`: retriever integration to search in ECM
  systems and make the result available in LlamaIndex

## Installation

Install OpenDMA and this integration from PyPI:

```bash
pip install llama-index-readers-opendma llama-index-retrievers-opendma
```

## Quickstart

```python
from llama_index.readers.opendma import OpenDMAReader

reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="my-repository",
    document_ids=["some-document-id"],
)

documents = reader.load_data()

for document in documents[:2]:
    print(document.id_)
    print("Title:", document.metadata.get("opendma:Title"))
    print(document.text)
```

By default, `OpenDMAReader` handles `text/plain` content. For PDF, Office,
image, media, and other binary formats, install the `llama-index-readers-file`
package.

Use `OpenDMARetriever` when you want LlamaIndex to call an OpenDMA search as part
of a retrieval pipeline:

```python
from llama_index.retrievers.opendma import OpenDMARetriever

retriever = OpenDMARetriever(
    endpoint="http://localhost:8080/opendma",
    username="admin",
    password="admin",
    repository_id="my-repository",
    query_language="opendma:sfts",
)

nodes = retriever.retrieve("needle keyword")
```

## Documentation

- [Tutorials](https://github.com/OpenDMA/llama-index-opendma/tree/main/docs/tutorials/README.md)
- [Documentation](https://github.com/OpenDMA/llama-index-opendma/tree/main/docs/README.md)
- [Examples](https://github.com/OpenDMA/llama-index-opendma/tree/main/docs/examples/README.md)

## Development

This project uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-packages
uv run pytest
uv run ruff check .
uv run --package llama-index-readers-opendma mypy -p llama_index.readers.opendma
uv run --package llama-index-retrievers-opendma mypy -p llama_index.retrievers.opendma
```
