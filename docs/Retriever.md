# OpenDMA Retriever

An OpenDMA Retriever performs a search in an ECM repository through
OpenDMA and converts the content and metadata into LlamaIndex
`NodeWithScore` objects.

Every returned `NodeWithScore` wraps a LlamaIndex node containing:

- text extracted from the repository document
- `metadata`: OpenDMA metadata, repository-specific metadata, and integration metadata

For a short project overview, see the project [README](../README.md).

Guided LlamaIndex application tutorials are documented in
[tutorials/README.md](tutorials/README.md).

## Installation

Install OpenDMA and te OpenDMA Retrievers for LlamaIndex from PyPI:

```bash
pip install llama-index-retrievers-opendma
```

## Basic Usage

Create an `OpenDMARetriever` with the OpenDMA REST endpoint, credentials,
repository ID, and query language.

The generic `OpenDMARetriever` passes the input string through unchanged as
the OpenDMA query. This keeps repository-specific query syntax explicit.

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

Retrievers use the same [content-state](./Reader.md#content-states)
options as readers:

```python
retriever = OpenDMARetriever(
    ...,
    query_language="opendma:sfts",
    include_no_content=True,
    include_unhandled_content=True,
)
```

Use `similarity_top_k` to limit how many LlamaIndex `NodeWithScore`
objects are returned:

```python
retriever = OpenDMARetriever(
    ...,
    query_language="opendma:sfts",
    similarity_top_k=5,
)
```

The limit applies after LlamaIndex transformations have converted documents
into nodes. If transformations split a repository document into several nodes,
each node counts as one returned LlamaIndex `NodeWithScore`. Once the limit is
reached, the retriever stops consuming additional OpenDMA search results.

## Options

Required constructor arguments:

- `endpoint`: OpenDMA REST service endpoint
- `username`: username for authentication
- `password`: password for authentication
- `repository_id`: ID of the OpenDMA repository
- `query_language`: query language used to execute the input query

Optional arguments:

- `include_no_content`: include documents without content as empty documents
- `include_unhandled_content`: include documents with unsupported MIME types as
  empty documents
- `file_extractor_per_mimetype`: MIME-type mapped LlamaIndex readers for binary
  content
- `transformations`: LlamaIndex transformations used to turn documents into
  nodes
- `similarity_top_k`: maximum number of LlamaIndex `NodeWithScore` objects to
  return
- `raise_on_error`: raise exceptions while retrieving or transforming individual
  documents instead of continuing
- `metadata_fn`: optional callable for adding custom metadata
- `callback_manager`: optional LlamaIndex callback manager
- `verbose`: enable verbose retriever output

## AlfrescoRetriever

`AlfrescoRetriever` is a convenience retriever for Alfresco repositories exposed
through OpenDMA. It turns the input string into an Alfresco AFTS full-text query
while respecting escaping rules for special characters.

```python
from llama_index.retrievers.opendma import AlfrescoRetriever

retriever = AlfrescoRetriever(
    endpoint="http://localhost:7070/opendma/alf",
    username="admin",
    password="admin",
    sites=["swsdp"],
)

nodes = retriever.retrieve("website design")
```

When `sites` is set, retrieval is restricted to the matching Alfresco site short
names.

`AlfrescoRetriever` supports the same options as `OpenDMARetriever`, with these
defaults and additions:

- `repository_id="Alfresco"`
- `query_language="alfresco:afts"`
- `sites`: optional Alfresco site short names used to restrict retrieval

## FileNetP8Retriever

`FileNetP8Retriever` is a convenience retriever for FileNet P8 repositories
exposed through OpenDMA. It turns the input string into a valid FileNet P8
Content Based Retrieval (CBR) query while respecting escaping rules for
special characters.

```python
from llama_index.retrievers.opendma import FileNetP8Retriever

retriever = FileNetP8Retriever(
    endpoint="http://localhost:8080/opendma/filenet",
    username="admin",
    password="admin",
    repository_id="FileNetP8",
)

nodes = retriever.retrieve("contract invoice")
```

`FileNetP8Retriever` supports the same options as `OpenDMARetriever`, with this
default:

- `query_language="filenetp8:sql"`

## DocumentumRetriever

`DocumentumRetriever` is a convenience retriever for Documentum repositories
exposed through OpenDMA. It turns the input string into a valid Documentum
Full-Text Search query while respecting escaping rules for special characters.

```python
from llama_index.retrievers.opendma import DocumentumRetriever

retriever = DocumentumRetriever(
    endpoint="http://localhost:8080/opendma/documentum",
    username="admin",
    password="admin",
    repository_id="Documentum",
)

nodes = retriever.retrieve("contract invoice")
```

`DocumentumRetriever` supports the same options as `OpenDMARetriever`, with this
default:

- `query_language="dctm:dql"`

## OnBaseRetriever

`OnBaseRetriever` is a convenience retriever for OnBase repositories exposed
through OpenDMA. It turns the input string into a valid OnBase Full-Text
Search query while respecting escaping rules for special characters.

```python
from llama_index.retrievers.opendma import OnBaseRetriever

retriever = OnBaseRetriever(
    endpoint="http://localhost:8080/opendma/onbase",
    username="admin",
    password="admin",
    repository_id="OnBase",
)

nodes = retriever.retrieve("contract invoice")
```

`OnBaseRetriever` supports the same options as `OpenDMARetriever`, with this
default:

- `query_language="onbase:DocumentQuery"`

## Examples

Runnable examples are documented in [examples/README.md](examples/README.md).

## Development

Contributor setup, test, build, and release commands are documented in
[Development.md](Development.md).
