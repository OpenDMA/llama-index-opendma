# Agentic RAG using OpenDMA Retriever

The previous tutorials all use a semantic search in a vector store. This
requires ingesting all content in advance, extracting text, chunk it, calculate
embeddings and store it in a vector store.

A vector store often provides better retrieval results. The original question from
the user might not contain any of the words that appear in text snippets which
are needed to answer this question. A semantic search solves this problem.

The previous [Agentic RAG with Vector Store](./03_agentic_rag_vectorstore.md)
tutorial uses an orchestrator that can decide to run another search with a
different query term. It can perform multiple searches until it has decided
that either enough information has been found to answer the question or to
give up.

This raises an important question: **Do we even need a Vector Store?**

Building this knowledge base is a time-consuming and costly task. More
importantly, it introduces new problems. The store needs to be kept up-to-date
with the latest changes in the repository. Especially in Enterprise Scenarios,
complex access rights are a key barrier.

If an agentic workflow can perform multiple searches, is it able to formulate
search queries that reveal relevant information even without a semantic search?

> [!NOTE]
> This tutorial uses live LLM calls. Even with `temperature=0`, hosted models can
> change over time and may choose slightly different retrieval queries or produce
> different answer text. The exact output shown below should be treated as one
> representative run.

## Alfresco Repository

This tutorial is using the same Alfresco Repository and OpenDMA endpoint we have
set up during the last tutorial.

Please follow the [Running Alfresco](./02_metadata_aware_retrieval.md#running-alfresco-community-edition)
and [Running an OpenDMA Endpoint](./02_metadata_aware_retrieval.md#running-an-opendma-endpoint-for-alfresco)
instructions if you have skipped the previous tutorial. Also make sure to
[add the "Engineering" site](./02_metadata_aware_retrieval.md#adding-more-content) as well.

## Install Dependencies

Install LlamaIndex, OpenDMA retrievers and Docling readers:

```bash
pip install llama-index llama-index-retrievers-opendma llama-index-readers-docling
```

## Setup

We use the same OpenAI chat model as in previous tutorials.

```python
import sys
import os
import getpass
from llama_index.llms.openai import OpenAI
from llama_index.readers.docling import DoclingReader

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

llm = OpenAI(model="gpt-4o-mini", temperature=0)
docling_reader = DoclingReader()

ALFRESCO_ENDPOINT = "http://localhost:7070/opendma/alf"
ALFRESCO_USERNAME = "admin"
ALFRESCO_PASSWORD = "admin"
ALFRESCO_REPOSITORY_ID = "Alfresco"
ALFRESCO_SITES_IN_SCOPE = ["swsdp", "engineering"]
```

## Search Tool

The `search_content` tool is built around the `AlfrescoRetriever`.

Unlike the previous tutorial, we do not build a vector store. Each tool call
performs a live search against Alfresco through OpenDMA. The agent can change
the search terms or restrict the search to a specific Alfresco site.

```python
import re
from typing import Any
from llama_index.core.node_parser import SentenceSplitter
from llama_index.retrievers.opendma import AlfrescoRetriever

transformations = [
    SentenceSplitter(chunk_size=1024, chunk_overlap=100),
]

def normalize_whitespace(text: str) -> str:
    """Collapse whitespace for compact console output and tool responses."""
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()

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

def search_content(query: str, site: str = "", top_k: int = 8) -> str:
    """Search Alfresco content. Retry with simpler terms when no chunks match."""
    site_filter = site.strip() or None
    if site_filter and site_filter not in ALFRESCO_SITES_IN_SCOPE:
        return (
            f"Site {site_filter!r} is not in scope for this RAG application. "
            "Use list_sites to inspect available in-scope sites."
        )

    retriever = AlfrescoRetriever(
        endpoint=ALFRESCO_ENDPOINT,
        username=ALFRESCO_USERNAME,
        password=ALFRESCO_PASSWORD,
        repository_id=ALFRESCO_REPOSITORY_ID,
        sites=[site_filter] if site_filter else None,
        file_extractor_per_mimetype={
            "application/msword": docling_reader,
        },
        transformations=transformations,
        similarity_top_k=top_k,
    )
    nodes = retriever.retrieve(query)

    if not nodes:
        return "No document chunks matched this search."

    return "\n\n---\n\n".join(
        format_search_result(result_index, node_with_score.node)
        for result_index, node_with_score in enumerate(nodes, start=1)
    )
```

The `top_k` parameter limits the number of LlamaIndex nodes returned by the
OpenDMA retriever. Since this retriever does not use a vector store, this is not
a semantic similarity ranking. It is a limit over the nodes produced from the
repository search results.

## Site Tool

We use the same `list_sites` tool as before.

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

TOOLS = [list_sites, search_content]
```

## Agent

With these two tools, we can define our agent. The prompt is similar to the
previous tutorial, but the `search_content` tool now performs live Alfresco
searches instead of vector-store similarity search.

```python
from llama_index.core.agent import FunctionAgent

system_prompt = (
    "You answer questions about documents stored in Alfresco.\n"
    "\n"
    "You have two tools:\n"
    "\n"
    "- list_sites: use this when the question implies a project, team, department, "
    "business area, or site, but you do not know which Alfresco site is relevant.\n"
    "- search_content: use this to search Alfresco document content through "
    "OpenDMA. Prefer a site-restricted search when a relevant site is known.\n"
    "\n"
    "Use search_content before answering factual questions about repository content. "
    "The search_content tool uses Alfresco full-text search, not semantic vector "
    "search. If a search returns no document chunks or weak results, do not answer "
    "and do not give up yet. Search again with a shorter, simpler, or broader query "
    "using the key domain terms from the user's question. For example, after a weak "
    "search for 'localisation of new website design', try 'website design' or "
    "'localisation' in the same site.\n"
    "\n"
    "Do not answer factual repository questions unless the answer is supported by "
    "retrieved context. If repeated searches do not find enough context, say that "
    "the available context does not contain the answer. Before saying that context "
    "is insufficient, make multiple search_content calls with different query terms."
)

agent = FunctionAgent(
    name="OpenDMAAgenticRetrieverRAG",
    description="An agent that answers questions by searching Alfresco through OpenDMA.",
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

await print_agent_events()
```

## Investigate agentic RAG steps

We can see the individual steps taken by the orchestrator. Pay attention to the
search tool calls (`Tool call: search_content`).

```text
Question: What is the state of localisation of our new website design?

Tool call: list_sites
Args: {}

--------------------------------------------------------------------------------

Tool result: list_sites
- engineering: Engineering - All product engineering related documents
- swsdp: Sample: Web Site Design Project - This is a Sample Alfresco Team site.

--------------------------------------------------------------------------------

Tool call: search_content
Args: {'query': 'localisation of new website design', 'site': 'swsdp'}

--------------------------------------------------------------------------------

Tool result: search_content
No document chunks matched this search.

--------------------------------------------------------------------------------

Tool call: search_content
Args: {'query': 'website design', 'site': 'swsdp'}

--------------------------------------------------------------------------------

Tool result: search_content
No document chunks matched this search.

--------------------------------------------------------------------------------

Tool call: search_content
Args: {'query': 'localisation', 'site': 'swsdp'}

--------------------------------------------------------------------------------

Tool result: search_content
Result 1
Title: Meetings
Site: swsdp
Path: /Company Home/Sites/swsdp/wiki
Content: <h1><font size="5">This wiki page has a summary of project meetings</font></h1>
<p><font size="4"><strong>Meeting: 2011-01-27 </strong></font></p>
<p><font size="4">Key Decisions:</font></p>
<ul>
<li><font size="4">Selected design number 2</font></li>
...

--------------------------------------------------------------------------------

Final answer:
The available context indicates that localisation is included in the first phase of the
website design project. Specifically, during a meeting, it was decided to include
localisation as part of the initial phase of the project. 

For more detailed information, you can refer to the full meeting reports linked in the documents.
```

This time, the orchestrator needs three search attempts rather than two to find the
relevant information.

## Conclusion

With an agentic RAG workflow, it is possible to avoid the additional vector store
required for a semantic search.
