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
