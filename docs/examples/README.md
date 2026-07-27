# Examples

This directory contains runnable examples for `llama-index-readers-opendma`.

Run examples from the repository root, e.g.:

```bash
uv run --package llama-index-readers-opendma python docs/examples/01_basic_usage.py
```

## Tutorial XML Repository Examples

The OpenDMA tutorial defines a portable sample repository in XML. It is also
made available through an OpenDMA REST service, packaged as a Docker image:

```bash
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
```

Verify the service at:

```text
http://localhost:8080/opendma
```

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
