# OpenDMA Document Readers

An OpenDMA Document Reader fetches content and metadata from an ECM system
through OpenDMA and converts the data into LlamaIndex `Document` objects.

Every returned LlamaIndex `Document` contains:

- `text`: text extracted from the repository document
- `metadata`: OpenDMA metadata, repository-specific metadata, and integration metadata

For a short project overview, see the project [README](../README.md).

Guided LlamaIndex application tutorials are documented in
[tutorials/README.md](tutorials/README.md).

## Installation

Install OpenDMA and the OpenDMA Readers for LlamaIndex from PyPI:

```bash
pip install llama-index-readers-opendma
```

## Basic Usage

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

## Reading Strategies

`OpenDMAReader` can load documents by document ID:

```python
reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="admin",
    password="admin",
    repository_id="my-repository",
    document_ids=["doc-1", "doc-2"],
)
```

It can load documents directly contained in folders:

```python
reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="admin",
    password="admin",
    repository_id="my-repository",
    folder_ids=["folder-1"],
)
```

Set `recursive=True` to include documents in subfolders:

```python
reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="admin",
    password="admin",
    repository_id="my-repository",
    folder_ids=["folder-1"],
    recursive=True,
)
```

It can also load documents from an OpenDMA query:

```python
reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="admin",
    password="admin",
    repository_id="Alfresco",
    query="SELECT * FROM cmis:document",
    query_language="alfresco:cmis",
)
```

The query language and query syntax depend on the OpenDMA repository
implementation.

The ECM repository might contain objects where it is not possible to convert
the binary data into text, or that might not carry any binary data at all.
These objects are ignored by default.

Use these options when you want placeholder `Document` objects for missing or
unsupported content:

```python
reader = OpenDMAReader(
    ...,
    include_no_content=True,
    include_unhandled_content=True,
)
```

## Content States

Content state is stored in `document.metadata["content_state"]`:

- `Processed`: content was decoded directly or transformed by a file reader
- `Missing`: no content was available and `include_no_content=True`
- `Unsupported`: no configured reader accepted the MIME type and
  `include_unhandled_content=True`

## Error Handling

Individual document failures do not stop reading by default. The reader emits a
`RuntimeWarning` and continues with the next document.

Use `raise_on_error=True` to fail fast:

```python
reader = OpenDMAReader(
    ...,
    raise_on_error=True,
)
```

## File Extractors

`OpenDMAReader` decodes plain text content directly. Binary formats such as PDF,
Office documents, images, or media are delegated to LlamaIndex file readers.

The mapping is based on MIME type, not file extension:

```python
from llama_index.readers.file import PDFReader
from llama_index.readers.opendma import OpenDMAReader

reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="admin",
    password="admin",
    repository_id="my-repository",
    document_ids=["contract-123"],
    file_extractor_per_mimetype={
        "application/pdf": PDFReader(),
    },
)
```

When `llama-index-readers-file` is installed, `OpenDMAReader` automatically uses
the default LlamaIndex file readers for supported MIME types. You can still pass
`file_extractor_per_mimetype` to override or extend that mapping.

Some formats require additional readers. For example, legacy Word files with
MIME type `application/msword` can be processed with Docling:

```python
from llama_index.readers.docling import DoclingReader

reader = OpenDMAReader(
    ...,
    file_extractor_per_mimetype={
        "application/msword": DoclingReader(),
    },
)
```

## Async Reading

`OpenDMAReader` supports the standard LlamaIndex reader methods:

- `load_data()`: eagerly load all matching documents
- `lazy_load_data()`: yield documents one by one
- `aload_data()`: asynchronously load all matching documents
- `alazy_load_data()`: asynchronously return a lazy iterable through the
  inherited `BaseReader` implementation
- `iter_data()`: yield lists of documents per OpenDMA source document

Use `lazy_load_data()` when you want to process results as they are loaded:

```python
for document in reader.lazy_load_data():
    print(document.id_)
```

Use `iter_data()` when file readers may split one repository document into
multiple LlamaIndex documents and you want to preserve that grouping:

```python
for document_group in reader.iter_data():
    print(f"Loaded {len(document_group)} documents from one OpenDMA object")
```

Use `aload_data()` in async workflows:

```python
documents = await reader.aload_data()
```

## AlfrescoReader

`AlfrescoReader` is a convenience subclass of `OpenDMAReader` for Alfresco
repositories exposed through OpenDMA.

It adds Alfresco-specific defaults:

- `repository_id="Alfresco"`
- `query_language="alfresco:afts"`

It also adds `sites`, which accepts Alfresco site short names and loads all
documents below the matching site folders recursively.

```python
from llama_index.readers.opendma import AlfrescoReader

reader = AlfrescoReader(
    endpoint="http://localhost:7070/opendma/alf",
    username="admin",
    password="admin",
    sites=["swsdp"],
)

documents = reader.load_data()
```

`AlfrescoReader` still supports the generic reading options such as
`document_ids`, `folder_ids`, `query`, `include_no_content`, and
`raise_on_error`.

When `sites` is set, the reader searches Alfresco sites by name with AFTS and
then recursively traverses the site folders. For setup instructions and a
runnable example, see [examples/README.md](examples/README.md).

## Examples

Runnable examples are documented in [examples/README.md](examples/README.md).

## Development

Contributor setup, test, build, and release commands are documented in
[Development.md](Development.md).
