# Agentic RAG

This tutorial is a continuation of the previous [Metadata-Aware Retrieval](./02_metadata_aware_retrieval.md).

The query engine in the previous RAG application followed a straight path by first
retrieving context from a knowledge base and then synthesising a response for the user.

Here, we show an agentic approach where an orchestrator can choose to run multiple
searches against the knowledge base until it has discovered enough information to
respond to the question.

We provide the orchestrator with two tools:
- ``list_sites``: reads available Alfresco sites through the OpenDMA API
- ``search_content``: runs similarity search, optionally restricted to one site

The agent loops between the orchestrator and the tools, with the orchestrator
deciding for its next move:
- List all available sites
- Re-run the search with different query terms
- Run the search against a different site
- Run the search globally against the entire knowledge base
- Respond to the user

## Alfresco Repository

This tutorial is using the same Alfresco Repository and OpenDMA endpoint we have
set up during the last tutorial.

Please follow the [Running Alfresco](./02_metadata_aware_retrieval.md#running-alfresco-community-edition)
and [Running an OpenDMA Endpoint](02_metadata_aware_retrieval.md#running-an-opendma-endpoint-for-alfresco)
instructions if you have skipped the previous tutorial. Also make sure to
[add the "Engineering" site](./02_metadata_aware_retrieval.md#adding-more-content) as well.

## Install Dependencies

Install LlamaIndex, File Readers, OpenDMA readers, and the Docling readers:

```bash
pip install llama-index llama-index-readers-opendma llama-index-readers-file llama-index-readers-docling
```

## Setup

We use the same OpenAI chat and embedding models as in previous tutorials.

```python
import sys
import os
import getpass
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")
llm = OpenAI(model="gpt-4o-mini", temperature=0)
```

## Ingestion

The repository may contain more sites than this RAG application should use.
We define an explicit list of sites in scope and use it both for ingestion
and for filtering the site list exposed to the agent.

We use the `AlfrescoReader` to read all documents. It is configured with the
`DoclingReader` to process legacy Word documents.

```python
from llama_index.readers.opendma import AlfrescoReader
from llama_index.readers.docling import DoclingReader

ALFRESCO_ENDPOINT = "http://localhost:7070/opendma/alf"
ALFRESCO_USERNAME = "admin"
ALFRESCO_PASSWORD = "admin"
ALFRESCO_REPOSITORY_ID = "Alfresco"
ALFRESCO_SITES_IN_SCOPE = ["swsdp", "engineering"]

reader = AlfrescoReader(
    endpoint=ALFRESCO_ENDPOINT,
    username=ALFRESCO_USERNAME,
    password=ALFRESCO_PASSWORD,
    repository_id=ALFRESCO_REPOSITORY_ID,
    sites=ALFRESCO_SITES_IN_SCOPE,
    recursive=True,
    file_extractor_per_mimetype={
        "application/msword": DoclingReader(),
    },
)

documents = reader.load_data()
print(f"Loaded {len(documents)} documents from sites in scope.\n")
```

```text
Loaded 9 documents from sites in scope.
```

We use an in-memory vector store  as knowledge base.

```python
from llama_index.core import VectorStoreIndex

index = VectorStoreIndex.from_documents(documents)
print(f"Indexed documents: {len(index.ref_doc_info)}")
print(f"Indexed nodes: {len(index.storage_context.docstore.docs)}\n")
```

```text
Indexed documents: 9
Indexed nodes: 283
```

## Tools

For our tools, we prepare a small helper to get the list of sites from Alfresco.
This list is filtered down to the `ALFRESCO_SITES_IN_SCOPE` which have been
ingested in the knowledge base.

```python
import opendma.remote
from opendma.api import OdmaId, OdmaObject, OdmaQName

def get_property_string(obj: OdmaObject, qname: str) -> str:
    """Read an OpenDMA string property, returning an empty string when absent."""
    prop = obj.get_property(OdmaQName.from_string(qname))
    if prop is None:
        return ""
    value = prop.get_string()
    return value or ""

def load_sites_from_opendma() -> list[dict[str, str]]:
    """Load in-scope Alfresco site metadata through OpenDMA."""
    session = opendma.remote.connect(
        endpoint=ALFRESCO_ENDPOINT,
        username=ALFRESCO_USERNAME,
        password=ALFRESCO_PASSWORD,
    )
    try:
        search_result = session.search(
            OdmaId(ALFRESCO_REPOSITORY_ID),
            OdmaQName.from_string("alfresco:afts"),
            'TYPE:"st:site"',
        )
        discovered_sites = [
            {
                "id": get_property_string(site_obj, "alfresco:cm:name"),
                "title": get_property_string(site_obj, "alfresco:cm:title"),
                "description": get_property_string(site_obj, "alfresco:cm:description"),
            }
            for site_obj in search_result.get_objects()
            if isinstance(site_obj, OdmaObject)
        ]
        return [site for site in discovered_sites if site["id"] in ALFRESCO_SITES_IN_SCOPE]
    finally:
        session.close()
```

For our agent, we implement two tools: `list_sites` and `search_content`. In LlamaIndex,
these tools are simple functions.

```python
import re
from typing import Any
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

def list_sites() -> str:
    """Return in-scope Alfresco sites with short name, title, and description."""
    sites = load_sites_from_opendma()
    if not sites:
        return "No Alfresco sites were returned by the OpenDMA endpoint."

    return "\n".join(
        (
            f"- {site['id']}: {site['title'] or site['id']}"
            f" - {site['description'] or 'No description'}"
        )
        for site in sites
    )

def normalize_whitespace(text: str) -> str:
    """Collapse whitespace for compact console output and tool responses."""
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()

def build_metadata_filters(site: str | None) -> MetadataFilters:
    """Build metadata filters for active Alfresco documents."""
    filters = [
        MetadataFilter(key="opendma:CheckedOut", value=0),
    ]
    if site:
        filters.insert(0, MetadataFilter(key="alfresco:Site", value=site))
    return MetadataFilters(filters=filters)


def format_search_result(index: int, node: Any) -> str:
    """Format one retrieved node for the agent."""
    content = normalize_whitespace(node.get_content())
    if len(content) > 1200:
        content = content[:1200] + "..."

    return (
        f"Result {index}\n"
        f"Title: {node.metadata.get('opendma:Title')}\n"
        f"Site: {node.metadata.get('alfresco:Site')}\n"
        f"Path: {node.metadata.get('alfresco:Path')}\n"
        f"Content:\n{content}"
    )

def search_content(query: str, site: str = "", top_k: int = 5) -> str:
    """Search indexed Alfresco content. Retry with fewer focused terms when results are weak."""
    site_filter = site.strip() or None
    if site_filter and site_filter not in ALFRESCO_SITES_IN_SCOPE:
        return (
            f"Site {site_filter!r} is not in scope for this RAG application. "
            "Use list_sites to inspect available in-scope sites."
        )

    retriever = index.as_retriever(
        similarity_top_k=top_k,
        filters=build_metadata_filters(site_filter),
    )
    nodes = retriever.retrieve(query)

    if not nodes:
        return "No indexed document chunks matched this search."

    return "\n\n---\n\n".join(
        format_search_result(result_index, node_with_score.node)
        for result_index, node_with_score in enumerate(nodes, start=1)
    )

TOOLS = [list_sites, search_content]
```

## Agent

With these two tools, we can define our Agent.

```python
from llama_index.core.agent import FunctionAgent

system_prompt = (
    "You answer questions about documents stored in Alfresco.\n"
    "\n"
    "You have two tools:\n"
    "\n"
    "- list_sites: use this when the question implies a project, team, department, "
    "business area, or site, but you do not know which Alfresco site is relevant.\n"
    "- search_content: use this to search indexed Alfresco document content. Prefer "
    "a site-restricted search when a relevant site is known.\n"
    "\n"
    "Use search_content before answering factual questions about repository content. "
    "If the first search results are weak, irrelevant, or contain only links, "
    "navigation pages, overview pages, or general project references, do not answer "
    "and do not give up yet. Search again with a shorter, more focused query using "
    "the key domain term from the user's question. For example, after a weak search "
    "for 'localisation of new website design', search again for 'localisation' in "
    "the same site.\n"
    "\n"
    "Do not answer factual repository questions unless the answer is supported by "
    "retrieved context. If repeated searches do not find enough context, say that "
    "the available context does not contain the answer. Before saying that context "
    "is insufficient, make at least two search_content calls unless no indexed "
    "documents matched at all."
)

agent = FunctionAgent(
    name="OpenDMAAgenticRAG",
    description="An agent that answers questions about Alfresco content exposed through OpenDMA.",
    system_prompt=system_prompt,
    tools=TOOLS,
    llm=llm,
    timeout=120,
    verbose=False,
)
```

## Running the agentic RAG

Let's run the agent with a sample question.

We print out the outcome of each step while the agent transitions through
the workflow.

```python
import asyncio
from llama_index.core.agent.workflow import ToolCall, ToolCallResult

def print_tool_result(tool_result: ToolCallResult) -> None:
    """Print a compact representation of a tool result."""
    output = str(tool_result.tool_output.raw_output)
    print(f"Tool result: {tool_result.tool_name}")
    print(normalize_whitespace(output)[:1200])
    print()
    print("-" * 80)
    print()

async def print_agent_events() -> None:

    QUESTION = "What is the state of localisation of our new website design?"
    print(f"Question: {QUESTION}\n")

    handler = agent.run(QUESTION)

    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            print(f"Tool call: {event.tool_name}")
            print(f"Args: {event.tool_kwargs}")
            print()
            print("-" * 80)
            print()
        elif isinstance(event, ToolCallResult):
            print_tool_result(event)

    response = await handler
    print("Final answer:")
    print(response)


asyncio.run(print_agent_events())
```

We can see how the orchestrator first decides to get a list of sites and the
`list_sites` tool returns that list:

```text
Tool call: list_sites
Args: {}

--------------------------------------------------------------------------------

Tool result: list_sites
- swsdp: Sample: Web Site Design Project - This is a Sample Alfresco Team site.
- engineering: Engineering - All product engineering related documents
```

Next, the orchestrator decides to run a search scoped to the `swsdp` site with
the query term "localisation of new website design".

```text
Tool call: search_content
Args: {'query': 'localisation of new website design', 'site': 'swsdp'}

--------------------------------------------------------------------------------

Tool result: search_content
Result 1
Title: link-1297806244007_178
Site: swsdp Path: /Company Home/Sites/swsdp/links
Content: http://www.w3.org/standards/webdesign/
---
Result 2
Title: Main_Page
Site: swsdp Path: /Company Home/Sites/swsdp/wiki
Content: <p><img title="undefined" src="/share/proxy/alfresco/api/node/content/
workspace/SpacesStore/79a03a3e-a027-4b91-9f14-02b62723591e/GE Logo.png" alt="" />
</p> <h1><font size="5" color="#457F32">Wiki Pages for the new corporate web
site design project</font></h1>...
```

It only found a link and the Main Wiki page. It is not possible to  answer the
question based on this information. The orchestrator decides to run  another
search in the same site with just ther term "localisation".

```text
Tool call: search_content
Args: {'query': 'localisation', 'site': 'swsdp'}

--------------------------------------------------------------------------------

Tool result: search_content
Result 1
Title: link-1297806244007_178
Site: swsdp
Path: /Company Home/Sites/swsdp/links
Content: http://www.w3.org/standards/webdesign/
---
Result 2
Title: Meeting Notes 2011-02-10.doc
Site: swsdp
Path: /Company Home/Sites/swsdp/documentLibrary/Meeting Notes
Content: ## Meeting Notes ### Date: 10th February 2011 ### Attendees: Mike Jackson
Benjamin Scobell Betty Silver Jimmy Pitt Angela Travers Izzy Previn ## Actions: |
**Action** | **Action Owner** | **Date** | |----------------------------|
--------------------|-----------------------| | Define TCO calculator spec |
Izzy Previn | 15 th February 2011 | | Select localization agency | Betty Silver
| Next meeting | | Modify budget spread sheet | Mike Jackson | 20 th February 2011
| | | | | | | | | ### Key Decisions - Decided to included TCO calculator in phase 1
 - Decided to include localization in phase 1 - Adjusted budgets inline with new
 additions...
 ```

 Now the search result contains the Meeting notes that contains localisation as one
 of the Key decision.

 Now the orchestrator decides to answer the question.

```text
Final answer:
The state of localisation for the new website design indicates that it is included
in the project's first phase. During a meeting on February 10, 2011, it was decided
to include localisation as part of the project scope, along with other key features
like a TCO calculator.

For further details, you can refer to the meeting notes from that date, which
outline the decisions made regarding the project.
```

## Conclusion and Further Reading

This tutorial demonstrates the benefits of using OpenDMA in an agentic RAG
application when your content is stored in an ECM system like Alfresco,
CMOD, Documentum, FileNet P8, Nuxeo, OpenText, and the like.

The additional information contained in these systems, like the site name in Alfresco,
can help the orchestrator choose where and how to search for relevant context.

LlamaIndex provides a wealth of tutorials showing different strategies for
answer generation, agentic chat bots, or applications working on unstructured
data in general.

Head over to the open source [OpenDMA](https://opendma.org) project to learn
how to connect your ECM to LlamaIndex.
