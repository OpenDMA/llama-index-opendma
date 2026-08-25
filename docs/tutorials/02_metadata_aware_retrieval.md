# Metadata-Aware Retrieval

In this tutorial, we start with the same indexing pipeline and query engine we
have built in the previous [Basic RAG tutorial](./01_basic_rag.md). But this
time, we connect it to a real ECM system.

We choose Alfresco, as it is available at no cost in a community edition and
comes with a convenient Docker Compose deployment.

After ingesting the information from the "Sample: Web Site Design" site and
asking a couple of questions, we extend the knowledge base and ingest more,
similar content. We can observe how this degrades the response quality.

To fix this, we extend the basic RAG and enable it to take additional
information into account, like the Site where the document is stored.

> [!NOTE]
> The example in this tutorial is a bit brittle and might not always work.
> The Alfresco Sample Site is full of "Lorem Ipsum" text making similarity
> search challenging.  
> Following tutorials present advanced techniques based on deepagents.

## Running Alfresco Community Edition

Alfresco Community Edition is available free of charge. Each new setup contains
the "Sample: Web Site Design Project" site used in this tutorial.

If you do not already have an Alfresco system running, start one with Docker
Compose:

```bash
git clone https://github.com/Alfresco/acs-deployment.git
cd acs-deployment/docker-compose
docker compose -f community-compose.yaml up -d
```

Verify that Alfresco is running by opening:

```text
http://localhost:8080/share
```

The default credentials are:

```text
admin/admin
```

## Running an OpenDMA Endpoint for Alfresco

The quickest way to map Alfresco to the OpenDMA data model and expose an OpenDMA
REST endpoint is to run the [ECI Server](https://github.com/xaldon/eci-server).
It is available free of charge for non-production use.

Start it with Docker Compose:

```bash
git clone https://github.com/xaldon/eci-server.git
cd eci-server/docker_compose
docker compose up -d
```

After the service is running:

1. Open the web UI at `http://localhost:7070`.
2. Initialise the admin account.
3. Accept the license agreement.
4. Install a free-of-charge license key.
5. Navigate to "Admin" > "Connections".
6. Add a new connection to `Alfresco Content Services`.
7. Choose "Automatically detect parameters with Smart Setup" for target server `host.docker.internal`.
8. Save the new connection as `Alfresco @ host.docker.internal`.
9. Navigate to "Admin" > "REST Endpoints".
10. Add a new REST Endpoint.
11. Set the slug to `opendma/alf`.
12. Select the `Alfresco @ host.docker.internal` connection.
13. Keep the proposed "Inbound Authentication" ("HTTP Basic" and "Propagate Inbound").
14. Save the new REST Endpoint

The example expects the OpenDMA endpoint at:

```text
http://localhost:7070/opendma/alf
```

To verify this REST endpoint, you can open `http://localhost:7070/opendma/alf/` (with a trailing slash)
in a web browser and authenticate with your Alfresco credentials (`admin/admin` by default).

## Install Dependencies

Install LlamaIndex, File Readers, OpenDMA readers, and the Docling readers:

```bash
pip install llama-index llama-index-readers-opendma llama-index-readers-file llama-index-readers-docling
```

## Indexing Pipeline

We set the API key for OpenAI as `OPENAI_API_KEY` environment variable.

```python
import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")
```

In this tutorial, we use a specialised version of the OpenDMAReader which
is capable of understanding Alfresco specific concepts, like sites. We simply
ingest all information from the Sample Site that comes pre-installed with
each new Alfresco instance:

```python
from llama_index.readers.opendma import AlfrescoReader
from llama_index.readers.docling import DoclingReader
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding

reader = AlfrescoReader(
    endpoint="http://localhost:7070/opendma/alf",
    username="admin",
    password="admin",
    repository_id="Alfresco",
    sites=["swsdp"],
    recursive=True,
    file_extractor_per_mimetype={
        "application/msword": DoclingReader(),
    },
)

documents = reader.load_data()
print(f"Loaded {len(documents)} documents from Alfresco through OpenDMA.")

Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")
index = VectorStoreIndex.from_documents(documents)

print(f"Indexed {len(index.ref_doc_info)} documents.")
print(f"Indexed nodes: {len(index.storage_context.docstore.docs)}")
```

```text
Loaded 32 documents from Alfresco through OpenDMA.
Indexed 27 documents.
Indexed nodes: 55
```

If you want, you can investigate the loaded documents and the content
in the vector store as in the previous tutorial.

## Query Engine

We create a `QueryEngine` from that index using the top 5 results:

```python
query_engine = index.as_query_engine(similarity_top_k=5)
```

Let's ask a question about the "Sample: Web Site Design Project" we have
ingested in the vector store.

```python
question_meeting_jan = "Who attended the meeting in January 2011?"
response_meeting_jan = query_engine.query(question_meeting_jan)

print(f"Question:\n{question_meeting_jan}\n")
print(f"Answer:\n{response_meeting_jan}")
```

It will print out this result:

```text
Question:
Who attended the meeting in January 2011?

Answer:
Mike Jackson, Benjamin Scobell, Betty Silver, Jimmy Pitt, and Angela Travers
attended the meeting in January 2011.
```

We can also inspect the retrieval and look at the individual text snippets that
have been used to generate this answer:

```python
import re


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


for node_with_score in query_engine.retrieve(question_meeting_jan):
    node = node_with_score.node
    print(f"Title: {node.metadata.get('opendma:Title')}")
    print(normalize_whitespace(node.get_content()[:75]))
    print("-" * 80)
```

```text
Title: Meetings
<h1><font size="5">This wiki page has a summary of project meetings</font><
--------------------------------------------------------------------------------
Title: Meetings
size="4"><br /></font></p> <p><font size="4"><strong>Meeting: 2011-02-10 </
--------------------------------------------------------------------------------
Title: Meeting Notes 2011-01-27.doc
## Meeting Notes ### Date: 27th January 2011 ### Attendees: Mike Jackso
--------------------------------------------------------------------------------
Title: Meeting Notes 2011-02-10.doc
## Meeting Notes ### Date: 10th February 2011 ### Attendees: Mike Jacks
--------------------------------------------------------------------------------
Title: Meeting Notes 2011-02-03.doc
## Meeting Notes ### Date: 3rd February 2011 ### Attendees: Mike Jackso
--------------------------------------------------------------------------------
```

The retriever found all three meeting notes and presented these to the LLM to generate the response.  
This allows us to ask also less specific questions like:

```python
question_action_last_meeting = "What action items are listed in the meeting notes?"
response_action_last_meeting = query_engine.query(question_action_last_meeting)

print(f"Question:\n{question_action_last_meeting}\n")
print(f"Answer:\n{response_action_last_meeting}")
```

```text
Question:
What action items are listed in the meeting notes?

Answer:
The action items listed in the meeting notes are as follows:
- Define TCO calculator spec
- Select localization agency
- Modify budget spread sheet
- Secure domain name
- Select agency
- Draft requirements document
- Confirm budget
```

```python
question_localisation = "What is the state of localisation of our new website design?"
response_localisation = query_engine.query(question_localisation)

print(f"Question:\n{question_localisation}\n")
print(f"Answer:\n{response_localisation}")
```

```text
Question:
What is the state of localisation of our new website design?

Answer:
The state of localisation of the new website design is that it has been decided
to include localisation in phase 1 of the project.
```

> [!IMPORTANT]  
> The quality and actual text of the answers depend strongly on external factors
> we do not control.  
> We intentionally want this tutorial to be close to real world scenarios rather
> than working in a strictly constrained artificial environment.

This works pretty well so far.

However, this is just a demo scenario and not really comparable to production use cases.
The sample site in Alfresco consists only of a handful of documents, most of them with
little to no content beyond "lorem ipsum". There is not really a haystack where we
need to find our needle in.

## Adding more content

Let's see what happens after ingesting the content of additional sites with similar
content. First, we add an "Engineering" site to Alfresco:

1. Open `http://localhost:8080/share` in a web browser
2. Log in as "admin" with password "admin"
3. Open the "Sites" main menu and select "Create Site"
4. In the dialog, create a "Collaboration Site" with name "Engineering" and set the
   description to "All product engineering related documents"
5. Keep visibility "Public" and create this site
6. In the newly created "Engineering" site, navigate to "Document Library"
7. Upload [this](./sample-files/product-webui-design.txt) text file to the Document
   Library root

We ingest this new site as well into the same vector store:

```python
engineering_reader = AlfrescoReader(
    endpoint="http://localhost:7070/opendma/alf",
    username="admin",
    password="admin",
    repository_id="Alfresco",
    sites=["engineering"],
    recursive=True,
    file_extractor_per_mimetype={
        "application/msword": DoclingReader(),
    },
)

engineering_documents = engineering_reader.load_data()
print(f"Loaded {len(engineering_documents)} additional documents from Engineering Site.")

for doc in engineering_documents:
    index.insert(doc)

print(f"New index size: {len(index.ref_doc_info)}")
print(f"Indexed nodes after update: {len(index.storage_context.docstore.docs)}")
```

```text
Loaded 1 additional documents from Engineering Site.
New index size: 28
Indexed nodes after update: 318
```

The indexing pipeline has split the single text document into multiple nodes.

After updating the index, we need to create a new `QueryEngine`. The retriever
component in the query engine holds a list of nodes, which limits the existing
query engine to those nodes that existed before we updated the index with more
content.

```python
larger_index_query_engine = index.as_query_engine(similarity_top_k=5)
```
Now we ask the same question again, using a larger index:

```python
larger_index_response_localisation = larger_index_query_engine.query(question_localisation)

print(f"Question:\n{question_localisation}\n")
print(f"Answer:\n{larger_index_response_localisation}")
```

```text
Question:
What is the state of localisation of our new website design?

Answer:
The state of localisation of the new website design is intentionally not documented
in the provided information. The focus is on exploring localisation principles,
recommendations, and best practices without reporting any specific implementation
status, completion percentage, or current progress of the localisation efforts.
```

This demonstrates an effect called **retrieval dilution**. Let's investigate the context
retrieved from the vector store:

```python
for node_with_score in larger_index_query_engine.retrieve(question_localisation):
    node = node_with_score.node
    print(f"Title: {node.metadata.get('opendma:Title')}")
    print(normalize_whitespace(node.get_content()[:75]))
    print("-" * 80)
```

```text
Title: product-webui-design.txt
This section intentionally explores localisation in depth without reporting
--------------------------------------------------------------------------------
Title: product-webui-design.txt
It deliberately avoids documenting the current state of localisation of the
--------------------------------------------------------------------------------
Title: product-webui-design.txt
This section intentionally explores localisation in depth without reporting
--------------------------------------------------------------------------------
Title: product-webui-design.txt
This section intentionally explores localisation in depth without reporting
--------------------------------------------------------------------------------
Title: product-webui-design.txt
Examples include translation workflows, language fallback, locale-aware for
--------------------------------------------------------------------------------
```

The new Engineering site contains so many information chunks similar to the
question that the actual relevant meeting notes are no longer within the top
5 chunks retrieved from the index.

In this case, the `product-webui-design.txt` document has been specifically
created to cause this.

A real world ECM system contains hundreds of thousands, if not millions of
documents. A company may have numerous teams, all storing their meeting
notes in the same system. It will contain thousands of contracts, agreements,
product specifications, and more.

A plain similarity search in the entire ECM repository is very likely to return
way too many irrelevant text chunks.

## Extending the RAG application with query analysis

Documents loaded through the OpenDMA ECI middleware carry additional information.
For Alfresco, we get the Content Type, additional Aspects, the property values
as well as additional information like the path or the Site.

All of this information is available as `metadata` in the LlamaIndex `Document`s.

```python
print("Imported from Site `Sample: Web Site Design Project`")
print("=" * 80)
for document in documents[:2]:
    print("Title:", document.metadata.get("opendma:Title"))
    print("Site:", document.metadata.get("alfresco:Site"))
    print("Path:", document.metadata.get("alfresco:Path"))
    print("-" * 80)
print("\nImported from Site `Engineering`")
print("=" * 80)
for document in engineering_documents[:2]:
    print("Title:", document.metadata.get("opendma:Title"))
    print("Site:", document.metadata.get("alfresco:Site"))
    print("Path:", document.metadata.get("alfresco:Path"))
    print("-" * 80)
```

```text
Imported from Site `Sample: Web Site Design Project`
================================================================================
Title: Meeting Notes 2011-01-27.doc
Site: swsdp
Path: /Company Home/Sites/swsdp/documentLibrary/Meeting Notes
--------------------------------------------------------------------------------
Title: Meeting Notes 2011-02-03.doc
Site: swsdp
Path: /Company Home/Sites/swsdp/documentLibrary/Meeting Notes
--------------------------------------------------------------------------------

Imported from Site `Engineering`
================================================================================
Title: product-webui-design.txt
Site: engineering
Path: /Company Home/Sites/engineering/documentLibrary
--------------------------------------------------------------------------------
```

This metadata is preserved on the nodes when these documents are inserted into
the index. We can use this information to guide the retrieval process and
ultimately get better results. This is achieved by adding an additional query
analysis step in front of the retrieval.

This step looks at the initial user question and selects a Site where the file
is most likely located.

We use OpenDMA to get the list of sites with their descriptions from Alfresco.

```python
from opendma.api import OdmaId, OdmaQName
import opendma.remote

opendma_session = opendma.remote.connect(
    endpoint="http://localhost:7070/opendma/alf",
    username="admin",
    password="admin",
)

sites_search_result = opendma_session.search(
    OdmaId("Alfresco"),
    OdmaQName.from_string("alfresco:afts"),
    'TYPE:"st:site"',
)

sites = [
    {
        "id": site_obj.get_property(OdmaQName.from_string("alfresco:cm:name")).get_string(),
        "title": site_obj.get_property(OdmaQName.from_string("alfresco:cm:title")).get_string(),
        "description": site_obj.get_property(
            OdmaQName.from_string("alfresco:cm:description")
        ).get_string(),
    }
    for site_obj in sites_search_result.get_objects()
]

opendma_session.close()

for site in sites:
    print(site)
```

```text
{'id': 'swsdp', 'title': 'Sample: Web Site Design Project', 'description': 'This is a Sample Alfresco Team site.'}
{'id': 'engineering', 'title': 'Engineering', 'description': 'All product engineering related documents'}
```

We create our own `MetadataAwareSiteRetriever` which analyses the query and
selects a site before retrieving nodes from the index. The nodes are filtered
down based on the selected site.

```python
from pydantic import BaseModel, Field
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.schema import QueryBundle, NodeWithScore
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.core import PromptTemplate


class AnalyzedQuery(BaseModel):
    query: str = Field(description="Optimized semantic search query.")
    site: str = Field(description="Alfresco site id to search.")


class MetadataAwareSiteRetriever(BaseRetriever):
    def __init__(self, index, sites, similarity_top_k=5, llm=None):
        super().__init__()
        self.index = index
        self.sites = sites
        self.similarity_top_k = similarity_top_k
        self.llm = llm or OpenAI(model="gpt-4o-mini", temperature=0)

    def _analyze_query(self, question: str) -> AnalyzedQuery:
        site_descriptions = "\n".join(
            f"- id: {site['id']}, title: {site['title']}, description: {site['description']}"
            for site in self.sites
        )
        prompt = PromptTemplate(
            "Select the best Alfresco site and produce a focused search query.\n"
            "\n"
            "Available sites:\n"
            f"{site_descriptions}\n"
            "\n"
            "Question:\n"
            f"{question}"
        )
        return self.llm.structured_predict(
            AnalyzedQuery, prompt, site_descriptions=site_descriptions, question=question
        )

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        analyzed_query = self._analyze_query(query_bundle.query_str)
        filters = MetadataFilters(
            filters=[
                MetadataFilter(key="alfresco:Site", value=analyzed_query.site),
                MetadataFilter(key="opendma:CheckedOut", value=0),
            ]
        )
        retriever = self.index.as_retriever(
            similarity_top_k=self.similarity_top_k,
            filters=filters,
        )
        return retriever.retrieve(analyzed_query.query)
```

We build a  new query engine using this retriever and the list of sites:

```python
metadata_aware_retriever = MetadataAwareSiteRetriever(
    index=index,
    sites=sites,
    similarity_top_k=5,
)

metadata_aware_query_engine = RetrieverQueryEngine.from_args(metadata_aware_retriever)
```

Now we ask the same question again:

```python
metadata_aware_response = metadata_aware_query_engine.query(question_localisation)

print(f"Question:\n{question_localisation}\n")
print(f"Answer:\n{metadata_aware_response}")
```

```text
Question:
What is the state of localisation of our new website design?

Answer:
The state of localisation of the new website design is that it has been
decided to include localisation in phase 1 of the project.
```

This is the advantage of using OpenDMA as document source for LlamaIndex. The
RAG application does not only receive text chunks. It also receives repository
metadata that can guide retrieval and improve the quality of the generated
answer.
