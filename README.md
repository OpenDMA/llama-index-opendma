# LlamaIndex OpenDMA

Integrate LlamaIndex with Enterprise Content Management systems such as Alfresco,
CMOD, Documentum, FileNet P8, OnBase, SharePoint, and other platforms.

[OpenDMA](https://opendma.org/) is a vendor-neutral abstraction layer for
Enterprise Content Management. It provides a common API for repositories allowing
developers to build applications that access content stored on different
platforms, including federating across multiple repositories.

This repository contains LlamaIndex integration packages that connect the OpenDMA
API to LlamaIndex. OpenDMA documents can be loaded as LlamaIndex `Document` objects
and native search results are returned as `NodeWithScore` objects.

A convenient ToolSpec allows agentic applications to browse through complex
repository layouts to retrieve information.

See our [examples](https://github.com/OpenDMA/llama-index-opendma/tree/main/docs/examples/README.md)
and [tutorials](https://github.com/OpenDMA/llama-index-opendma/tree/main/docs/tutorials/README.md)
to learn how to build RAG pipelines and tool-calling agents.

## Features

- Tools to browse an ECM repository, e.g. to enable agents to discover relevant documents.
- Tools for reading text chunks of documents, e.g. to allow agents to read sections of documents.
- Load documents by document ID, folder ID, or query, e.g. to build a knowledge base.
- Use LlamaIndex's retriever API for full text search, e.g. to use an existing repository as knowledge base.
- Preserve full metadata on every LlamaIndex `Document`, e.g. to scope RAG retrieval to a subset of relevant items.
- Process richer document formats with optional `llama-index-readers-file` package.

## Packages

- `llama-index-readers-opendma`: reader integration for loading ECM content
  in ingestion pipelines
- `llama-index-retrievers-opendma`: retriever integration to search in ECM
  systems and make the result available in LlamaIndex
- `llama-index-tools-opendma`: ToolSpec to allow tool-calling agents to browse
  through complex repository layouts

## Installation

Install OpenDMA and this integration from PyPI:

```bash
pip install llama-index-readers-opendma llama-index-retrievers-opendma llama-index-tools-opendma
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

The `OpenDMAToolSpec` provides various tools to allow agents to browse repository
layouts and read sections of text documents:

```python
from llama_index.tools.opendma import OpenDMAToolSpec
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

tool_spec = OpenDMAToolSpec(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
)

agent = FunctionAgent(
    tools=tool_spec.to_tool_list(),
    llm=OpenAI(model="gpt-4o-mini"),
    system_prompt="You are...",
)

response = await agent.run("Where can I find the latest meeting notes of project orion?")
print(response)
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
uv run --package llama-index-tools-opendma mypy -p llama_index.tools.opendma
```

## Related Projects

- [LlamaIndex](https://developers.llamaindex.ai/python/framework/)
- [OpenDMA](https://opendma.org/)
- [opendma-api](https://pypi.org/project/opendma-api/)
- [opendma-remote](https://pypi.org/project/opendma-remote/)
