# OpenDMA ToolSpec

An OpenDMA ToolSpec provides a set of tools that can be used by agents
to browse around the repository, explore the data model, and read
sections of documents.

ToolSpecs consist of:

- `opendma_get_metadata`: get information about an object in the repository
- `opendma_list_children`: list objects in a container (e.g. a folder)
- `opendma_describe_class`: investigate data model in the repository
- `opendma_search`: perform a full-text search
- `opendma_read_text`: read sections of a document

The `llama-index-tools-opendma` package offers specialised tool specs for
various ECM vendors to cover platform dependent features, e.g. the Sites
concept in Alfresco.

For installation and a short project overview, see the project
[README](../README.md).

Guided LlamaIndex application tutorials are documented in
[tutorials/README.md](tutorials/README.md).

## Basic Usage

Create an `OpenDMAToolSpec` with the OpenDMA REST endpoint, credentials,
repository ID, and optionally file extractors.

```python
from llama_index.tools.opendma import OpenDMAToolSpec
from llama_index.readers.file import PDFReader

tool_spec = OpenDMAToolSpec(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
    file_extractor_per_mimetype={
        "application/pdf": PDFReader(),
    },
)
```

The `endpoint` expects an OpenDMA REST service. The quickest way to map your ECM
to the OpenDMA data model and expose such an endpoint is to run the
[ECI Server](https://github.com/xaldon/eci-server).
It is available free of charge for non-production use.

Tools use the same [file_extractor_per_mimetype](./Reader.md#file-extractors)
dict as readers to transform binary files into text chunks.

Documents are read in pages of chunks with a continuation token. To optimise
performance, the tools cache chunks in memory after the binary data has been
transformed by a file reader. This mechanism can be controlled with these
parameters:

- `read_chunk_page_size`: Number of chunks to be returned in a single tool call. Default `3`.
- `read_text_cache_enabled`: Enable chunk caching. Default `True`.
- `read_text_cache_max_objects`: Cache size in number of documents. Default `32`.
- `read_text_cache_ttl_seconds`: Duration in seconds after which documents in cache are re-read. Default 6hrs `21600`.

## Tools

Call `to_tool_list()` to get the list of LlamaIndex tools:

```python
tools = tool_spec.to_tool_list()
tools_by_name = {tool.metadata.name: tool for tool in tools}
```

### `opendma_get_metadata`

Gets class, aspect, and scalar metadata for one OpenDMA object.

Input:

- `object_id` required string: OpenDMA object ID.

Output:

- `object_id`: OpenDMA object ID.
- `type_name`: qualified OpenDMA class name.
- `aspect_names`: list of qualified OpenDMA aspect names.
- `name`: display name derived from OpenDMA metadata.
- `metadata`: key/value pairs containing scalar OpenDMA property values.

Example:

```python
metadata = tools_by_name["opendma_get_metadata"].call(
    object_id="opendma-spec-document"
)
print(metadata.raw_output)
```

### `opendma_list_children`

Lists child folders and documents of an OpenDMA folder.

Input:

- `object_id` required string: OpenDMA folder object ID.
- `include_folders` optional boolean: include child folders. Default `True`.
- `include_files` optional boolean: include child documents. Default `True`.
- `name_pattern` optional string: glob-style name pattern applied to child names.
- `continuation_token` optional string: token returned by a previous call.
- `included_metadata` optional list of string: qualified OpenDMA property names to include.

Output:

- `items`: list of matching child objects.
- `has_more`: whether more child objects are available.
- `continuation_token`: token for the next call when `has_more` is true.

Each item contains:

- `object_id`: OpenDMA object ID.
- `type_name`: qualified OpenDMA class name.
- `aspect_names`: list of qualified OpenDMA aspect names.
- `name`: display name derived from OpenDMA metadata.
- `metadata`: selected metadata values.

Example:

```python
children = tools_by_name["opendma_list_children"].call(
    object_id="sample-folder-a"
)
print(children.raw_output)
```

### `opendma_read_text`

Reads transformed text chunks from one OpenDMA document.

Input:

- `object_id` required string: OpenDMA document object ID.
- `chunk_continuation_token` optional string: token returned by a previous call.

Output:

- `chunks`: list of text chunks.
- `has_more`: whether more chunks are available.
- `chunk_continuation_token`: token for the next call when `has_more` is true.

Each chunk contains:

- `text`: transformed text.
- `metadata`: metadata from the LlamaIndex `Document` returned by OpenDMAReader / configured file extractor.
- `chunk_index`: zero-based index of the chunk within the source document.

Example:

```python
spectext = tools_by_name["opendma_read_text"].call(
    object_id="opendma-spec-document"
)
print(spectext.raw_output)
```

### `opendma_describe_class`

Describes an OpenDMA type or aspect and its properties.

Input:

- `type_or_aspect_name` required string: qualified OpenDMA type or aspect name.

Output:

- `name`: qualified OpenDMA class or aspect name.
- `kind`: `type` or `aspect`.
- `parent`: qualified parent type name, if present.
- `inherited_properties`: properties inherited from parent types or aspects.
- `declared_properties`: properties declared directly on this type or aspect.

Each property contains:

- `name`: qualified OpenDMA property name.
- `type`: OpenDMA property type.
- `description`: display name or description.
- `required`: whether the property is required.
- `multi_value`: whether the property can contain multiple values.
- `queryable`: whether the property can be used in queries, if known.
- `possible_values`: list of allowed values, if known.

Example:

```python
tutorial_document = tools_by_name["opendma_describe_class"].call(
    type_or_aspect_name="tutorial:SampleDocument"
)
print(tutorial_document.raw_output)
```

### `opendma_search`

Performs a repository search and returns matching OpenDMA objects.
The search backend and query syntax depend on the ToolSpec implementation.

Input:

- `full_text` optional string: full-text query.
- `in_folder` optional string: folder object ID used to restrict the search.
- `include_subfolder_in_folder` optional boolean: include subfolders when `in_folder` is set.
- `included_metadata` optional list of string: qualified OpenDMA property names to include.

Output:

- `items`: list of matching objects.
- `has_more`: whether more objects are available.
- `continuation_token`: token for the next call when `has_more` is true.

Each item contains the same fields as `opendma_list_children` items.

Example:

```python
results = tools_by_name["opendma_search"].call(
    full_text="lorem ipsum",
)
print(results.raw_output)
```

## AlfrescoToolSpec

`AlfrescoToolSpec` configures `opendma_search` for Alfresco AFTS and adds the
Alfresco-specific `alfresco_list_sites` tool.

```python
from llama_index.tools.opendma import AlfrescoToolSpec

tool_spec = AlfrescoToolSpec(
    endpoint="http://localhost:7070/opendma/alf",
    username="admin",
    password="admin",
)
```

The `endpoint` expects an OpenDMA REST service. The quickest way to map your
Alfresco deployment to the OpenDMA data model and expose such an endpoint is
to run the [ECI Server](https://github.com/xaldon/eci-server).
It is available free of charge for non-production use.

The search tool converts `full_text` into an Alfresco `TEXT` query. If
`in_folder` is set, the search is restricted to direct children of that folder.
Set `include_subfolder_in_folder=True` to include descendants.

```python
results = tools_by_name["opendma_search"].call(
    full_text="lorem ipsum",
    in_folder="node:5515d3e1-bb2a-42ed-833c-52802a367033",
    include_subfolder_in_folder=True,
)
```

Additional tools:

- `alfresco_list_sites`: discover Alfresco sites and their root folder IDs

### `alfresco_list_sites`

Lists Alfresco sites.

Input:

- No input parameters.

Output:

- List of site descriptions.

Each site description contains:

- `short_name`: Alfresco site short name.
- `title`: site title.
- `description`: site description.
- `root_folder_id`: OpenDMA object ID of the site root folder.

Example:

```python
sites = tools_by_name["alfresco_list_sites"].call()
print(sites.raw_output)
```

## FileNetP8ToolSpec

`FileNetP8ToolSpec` configures `opendma_search` for FileNet P8 SQL full-text
search.

```python
from llama_index.tools.opendma import FileNetP8ToolSpec

tool_spec = FileNetP8ToolSpec(
    endpoint="http://localhost:7070/opendma/filenet",
    username="admin",
    password="admin",
    repository_id="FileNetP8",
)
```

The `endpoint` expects an OpenDMA REST service. The quickest way to map your
FileNet P8 deployment to the OpenDMA data model and expose such an endpoint is
to run the [ECI Server](https://github.com/xaldon/eci-server).
It is available free of charge for non-production use.

The search tool splits `full_text` into words, escapes FileNet content-search
special characters, joins the terms with `OR`, and places the result into a
FileNet `CONTAINS` clause.

If `in_folder` is set, it must be an OpenDMA ID backed by a FileNet object store
object ID in this format:

```text
objectstore:<classId>:<objectId>
```

The `<objectId>` part must be a braced FileNet object ID, for example
`{01234567-89AB-CDEF-0123-456789ABCDEF}`. Folder restrictions use `INFOLDER` by
default and `INSUBFOLDER` when `include_subfolder_in_folder=True`.

```python
results = tools_by_name["opendma_search"].call(
    full_text="contract invoice",
    in_folder="objectstore:Folder:{01234567-89AB-CDEF-0123-456789ABCDEF}",
    include_subfolder_in_folder=True,
)
```

## DocumentumToolSpec

`DocumentumToolSpec` configures `opendma_search` for Documentum DQL full-text
search.

```python
from llama_index.tools.opendma import DocumentumToolSpec

tool_spec = DocumentumToolSpec(
    endpoint="http://localhost:7070/opendma/documentum",
    username="admin",
    password="admin",
    repository_id="Documentum",
)
```

The `endpoint` expects an OpenDMA REST service. The quickest way to map your
Documentum deployment to the OpenDMA data model and expose such an endpoint is
to run the [ECI Server](https://github.com/xaldon/eci-server).
It is available free of charge for non-production use.

The search tool splits `full_text` into words, escapes DQL string literals,
joins the terms with `OR`, and places the result into a
`SEARCH DOCUMENT CONTAINS` clause.

If `in_folder` is set, it is used as the Documentum object ID in a `FOLDER`
predicate. Set `include_subfolder_in_folder=True` to add `DESCEND`.

```python
results = tools_by_name["opendma_search"].call(
    full_text="contract invoice",
    in_folder="0b00000180000123",
    include_subfolder_in_folder=True,
)
```

## OnBaseToolSpec

`OnBaseToolSpec` configures `opendma_search` for OnBase `DocumentQuery`
full-text search.

```python
from llama_index.tools.opendma import OnBaseToolSpec

tool_spec = OnBaseToolSpec(
    endpoint="http://localhost:7070/opendma/onbase",
    username="admin",
    password="admin",
    repository_id="OnBase",
)
```

The `endpoint` expects an OpenDMA REST service. The quickest way to map your
OnBase deployment to the OpenDMA data model and expose such an endpoint is
to run the [ECI Server](https://github.com/xaldon/eci-server).
It is available free of charge for non-production use.

The search tool splits `full_text` into words, joins the terms with `OR`, XML
escapes the result, and places it into `FullTextSearchString`.

The OnBase ToolSpec exposes an OnBase-specific search schema without folder
restriction parameters because OnBase folder restrictions are not available.

```python
results = tools_by_name["opendma_search"].call(
    full_text="contract invoice",
)
```
