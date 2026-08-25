# LlamaIndex Readers OpenDMA

LlamaIndex reader integration for [OpenDMA](https://opendma.org/).

OpenDMA is a vendor-neutral abstraction layer for enterprise content management
systems. It provides a common API for repositories such as Alfresco, CMOD,
Documentum, FileNet P8, OnBase, SharePoint, and other ECM or document management
platforms.

This package connects that API to LlamaIndex by loading OpenDMA
documents as `llama_index.core.schema.Document` objects.

Use this package when you want to build LlamaIndex applications, RAG pipelines, or
content analysis workflows on top of documents stored in ECM systems.

## Installation

```bash
pip install llama-index-readers-opendma
```

Install additional LlamaIndex file readers when you want to parse rich document
formats such as PDF, Office documents, images, or media. When this package is
available, `OpenDMAReader` automatically uses its default readers for supported
MIME types:

```bash
pip install llama-index-readers-file
```

## Documentation

- [Tutorials](https://github.com/OpenDMA/llama-index-opendma/tree/main/docs/tutorials/README.md)
- [Documentation](https://github.com/OpenDMA/llama-index-opendma/tree/main/docs/README.md)
- [Examples](https://github.com/OpenDMA/llama-index-opendma/tree/main/docs/examples/README.md)
