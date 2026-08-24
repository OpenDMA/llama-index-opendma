# Documentation

This page explains how to use `llama-index-opendma` in LlamaIndex applications.

For installation and a short project overview, see the project
[README](../README.md).

## Core Concepts

OpenDMA provides a uniform API for Enterprise Content Management (ECM) and
document management repositories. It supports Alfresco, CMOD (Content Manager
OnDemand), Documentum, FileNet P8, OpenText, OnBase, Nuxeo, SharePoint,
and many more.

`OpenDMAReader` fetches content and metadata through OpenDMA and makes it
available in LlamaIndex as `Document` objects. Typically used in ingestion
pipelines to build indices.

`OpenDMARetriever` runs a search through OpenDMA and makes the result available
in LlamaIndex. Typically used to get relevant context into your agents, e.g. as
part of RAG.

Every returned LlamaIndex `Document` or retrieved node contains:

- text extracted from the repository document
- `metadata`: OpenDMA metadata, repository-specific metadata, and integration metadata

`OpenDMAToolSpec` provides a set of tools to be used by tool-calling agents to
navigate around the repository, investigate the data model and read sections of
documents.

## [OpenDMAReader](./Reader.md)

Create an `OpenDMAReader` with the OpenDMA REST endpoint, credentials,
repository ID, and one or more loading strategies.

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
```

See the [Reader](./Reader.md) documentation for details.

## [OpenDMARetriever](./Retriever.md)

`OpenDMARetriever` implements LlamaIndex's retriever API. It accepts a string
query and returns LlamaIndex `NodeWithScore` objects.

```python
from llama_index.retrievers.opendma import OpenDMARetriever

retriever = OpenDMARetriever(
    endpoint="http://localhost:8080/opendma",
    username="admin",
    password="admin",
    repository_id="Alfresco",
    query_language="alfresco:cmis",
)

nodes = retriever.retrieve("SELECT * FROM cmis:document")
```

See the [Retriever](./Retriever.md) documentation for details.

## [OpenDMAToolSpec](./ToolSpec.md)

`OpenDMAToolSpec` provides a set of tools to be used by agents.

```python
from llama_index.tools.opendma import OpenDMAToolSpec

tool_spec = OpenDMAToolSpec(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
)

for tool in tool_spec.to_tool_list():
    print(tool.metadata.name)
```

See the [ToolSpec](./ToolSpec.md) documentation for details.

## Tutorials

Guided LlamaIndex application tutorials are documented in
[tutorials/README.md](tutorials/README.md).

## Development

Contributor setup, test, build, and release commands are documented in
[Development.md](Development.md).
