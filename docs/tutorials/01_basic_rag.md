# Basic RAG with OpenDMA

In the first part of this tutorial, we build an indexing pipeline that ingests
PDF files from an Enterprise Content Management (ECM) system and builds an
[index](https://developers.llamaindex.ai/python/framework/module_guides/indexing/).

The second part builds a [query engine](https://developers.llamaindex.ai/python/framework/understanding/rag/querying/)
to answer questions about the OpenDMA specification.

## Tutorial Repository

OpenDMA provides a tutorial repository contains, among other things, the OpenDMA
Specification as a PDF file. This repository comes in a convenient Docker image
exposing the OpenDMA REST API:

```bash
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
```

This allows you to follow the tutorial without preparing a real ECM system like
Alfresco, Documentum, Nuxeo or FileNet.

Make sure that this service is available by opening  (including the trailing slash):

```text
http://localhost:8080/opendma/
```

You can adjust the port if `8080` is already in use.

## Install Dependencies

Install LlamaIndex, File Readers, and the OpenDMA readers:

```bash
pip install llama-index llama-index-readers-opendma llama-index-readers-file
```

## Initialise Embeddings and Vector Store

In this tutorial, we are using OpenAI LLM and embeddings. You need an API key
and set as `OPENAI_API_KEY` environment variable.

```python
import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
  os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")
```

## OpenDMA Document Reader

The OpenDMA document reader retrieves documents from ECM systems exposed through
the OpenDMA API.

The tutorial repository contains several sample documents. We load the full
folder tree below `sample-folder-root`.

For binary document conversion, we use the file readers provided by LlamaIndex.

```python
from llama_index.readers.opendma import OpenDMAReader

OPENDMA_ENDPOINT = "http://localhost:8080/opendma"

reader = OpenDMAReader(
    endpoint=OPENDMA_ENDPOINT,
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
    folder_ids=["sample-folder-root"],
    recursive=True,
)

documents = reader.load_data()
print(f"Loaded {len(documents)} documents through OpenDMA.")
```

```text
Loaded 24 documents through OpenDMA.
```

The tutorial repository contains a PDF with the OpenDMA specification. After
loading, we can inspect the returned documents and their metadata:

```python
import re

def normalize_whitespace(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


for document in documents[:5]:
    print(f"ID: {document.id_}")
    print(f"Title: {document.metadata.get('opendma:Title')}")
    print("Preview:", normalize_whitespace(document.text[:75]))
    print("-" * 80)
```

Each returned LlamaIndex `Document` contains the extracted text in
`text` and OpenDMA metadata in `metadata`.

```text
ID: opendma://sample-repo/hello-world-document
Title: Hello, World!
Preview: Lorem ipsum dolor sit amet, consectetur adipiscing elit
--------------------------------------------------------------------------------
ID: opendma://sample-repo/opendma-spec-document
Title: OpenDMA Specification 0.8
Preview: OpenDMA – Open Document Management Architecture Final Version: 0.8 Editor:
--------------------------------------------------------------------------------
ID: opendma://sample-repo/opendma-spec-document
Title: OpenDMA Specification 0.8
Preview: The simple object model is able to hold data as scalar values or un-typed r
--------------------------------------------------------------------------------
ID: opendma://sample-repo/opendma-spec-document
Title: OpenDMA Specification 0.8
Preview: Double (§2.1) 6 Boolean (§2.1) 7 DateTime (§2.1)8 Binary (§2.1) 9 Reference
--------------------------------------------------------------------------------
ID: opendma://sample-repo/opendma-spec-document
Title: OpenDMA Specification 0.8
Preview: Write property input: qualiﬁed name (§1) and value(s) Modiﬁes only the valu
--------------------------------------------------------------------------------
```

## Create Vector Store Index

Now that we have prepared the text for our index, we create a
`VectorStoreIndex`.

```python
from llama_index.llms.openai import OpenAI
from llama_index.core import VectorStoreIndex

index = VectorStoreIndex.from_documents(documents)
```

In a production system, you would run the indexing pipeline only once for
new and changed documents and use a persistent vector store.

## RAG with Query Engine

LlamaIndex allows us to create a `QueryEngine` from that index.

```python
query_engine = index.as_query_engine(similarity_top_k=10)
```

This engine encapsulates the retrieval, postprocessing and response synthesis
steps of a RAG system.

Now it is time to test what we have built. Let's ask a question about the
OpenDMA specification:

```python
question = "How are objects identified in OpenDMA?"
response = query_engine.query(question)

print(f"Question:\n{question}\n")
print(f"Answer:\n{response}")
```

```text
Question:
How are objects identified in OpenDMA?

Answer:
Objects in OpenDMA are identified by a unique object identifier, which is represented as a string.
This identifier is defined in the context of the document management system and must be presentable
as a string. Each object can be uniquely identified within its context by this unique object identifier.
```

This is the basic RAG flow: documents are retrieved from the vector store, and
the model generates an answer from the retrieved context.

## Next

In the next tutorial, [Metadata-Aware Retrieval](./02_metadata_aware_retrieval.md), we ingest
data from a real ECM system: Alfresco.

We observe how the quality of the RAG degrades after ingesting more information into
the knowledge base. Additional information about the documents is used to guide retrieval and
increase precision and recall.