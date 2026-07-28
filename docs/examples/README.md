# Examples

This directory contains runnable examples for `llama-index-opendma`.

Run examples from the repository root, e.g.:

```bash
uv run --package llama-index-readers-opendma python docs/examples/01_basic_usage.py
```

## Tutorial XML Repository Examples

The OpenDMA tutorial defines a portable sample repository in XML.
It is also made available through an OpenDMA REST service, conveniently
packaged as Docker image:

```bash
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
```

Verify the service at:

```text
http://localhost:8080/opendma
```

These examples demonstrate the basic usage of the Document Loader with sample
content from this tutorial repository.

Features of the Tutorial XML Repository are limited, but it allows us to
explore the basic functionality of this LangChain integration without complex
setups.

### `01_basic_usage.py`

Loads one document by document ID from the tutorial repository and prints its
metadata and content.

This is the best first example to run.

### `02_content_states.py`

Shows how `include_no_content=True` and `include_unhandled_content=True` affect
reader output.

Documents can have these content states:

- `Processed`: content was decoded directly or transformed by a file reader
- `Missing`: no content was available
- `Unsupported`: content exists, but no configured reader supports its MIME type

### `03_folders.py`

Reads documents directly contained in a folder.

This example uses `folder_ids` and does not recurse into subfolders.

### `04_folders_recurse.py`

Compares non-recursive and recursive folder loading.

It runs the reader twice:

- once with `recursive=False`
- once with `recursive=True`

### `05_pdf.py`

Loads a PDF document and lets LlamaIndex's optional file readers package parse
the binary content.

Run it with the optional dependency available:

```bash
uv run --with llama-index-readers-file --package llama-index-readers-opendma python docs/examples/05_pdf.py
```
