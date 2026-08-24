# Tool-Calling Agent with ToolSpec

In this tutorial, we build a simple tool-calling agent and provide it with the
OpenDMA tools.

We observe how this agent is using its tools to gather the information required
to answer different questions.

> [!NOTE]
> This tutorial uses live LLM calls. Even with `temperature=0`, hosted models can
> change over time and may choose slightly different retrieval queries or produce
> different answer text. The exact output shown below should be treated as one
> representative run.

## Tutorial Repository

OpenDMA provides a tutorial repository which contains, among other things, the
OpenDMA Specification as a PDF file. This repository comes in a convenient Docker
image exposing the OpenDMA REST API:

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

Install LlamaIndex, OpenDMA tools and Docling readers:

```bash
pip install llama-index llama-index-tools-opendma llama-index-readers-docling
```

## Initialise OpenAI API key

Make sure you have the `OPENAI_API_KEY` environment variable set.

```python
import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
  os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")
```

## Create the ToolSpec

The ToolSpec is instantiated for an OpenDMA REST endpoint using a fixed account
and repository.

To convert binary content into text chunks, we need to provide a file reader.
For this tutorial, we use the Docling library.

```python
from llama_index.tools.opendma import OpenDMAToolSpec
from llama_index.readers.docling import DoclingReader

tool_spec = OpenDMAToolSpec(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
    file_extractor_per_mimetype={
        "application/msword": DoclingReader(),
    },
)
```

## Define the system prompt

The system prompt steers the reasoning phase and the tools choice. We use the
following for our tutorial.

```python
system_prompt="""
You answer questions using documents stored in an ECM repository.

In some cases, it is sufficient to locate the relevant documents in the
repository and use the metadata of these documents to answer the user’s question.

In other cases, the requested information is in the documents and you need to
read the documents to answer the question. Reading documents is much more
expensive than listing children or getting metadata. Use it carefully.

Avoid guessing file names.

Avoid requesting more text chunks than needed.

Use opendma_list_children to find candidate documents.
Use opendma_get_metadata to inspect a candidate document.
Use opendma_read_text to read document text.

The root of the repository has the ID `sample-folder-root`.

Do not answer factual repository questions unless the answer is supported by
tool results. If the repository does not contain enough information, say so.
"""
```

## Create the agent loop

We use the LlamaIndex `FunctionAgent` and instantiate it with our system
prompt and tools.

```python
from llama_index.core.agent import FunctionAgent

agent = FunctionAgent(
    name="OpenDMAAgenticRetrieverRAG",
    description="An agent that answers questions by searching a repository through OpenDMA.",
    system_prompt=system_prompt,
    tools=tool_spec.to_tool_list(),
    llm=llm,
    timeout=120,
    verbose=False,
)
```

## Helper function to inspect agent loop

To inspect the steps of the agent, we define these helper functions.

```python
import re
from llama_index.core.agent.workflow import ToolCall, ToolCallResult

def normalize_whitespace(text: str) -> str:
    """Collapse whitespace for compact console output and tool responses."""
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()

def print_tool_result(tool_result: ToolCallResult) -> None:
    """Print a compact representation of a tool result."""
    output = str(tool_result.tool_output.raw_output)
    print(f"Tool result: {tool_result.tool_name}")
    print(normalize_whitespace(output)[:1200])
    print()
    print("-" * 80)
    print()

async def print_agent_events(question: str) -> None:
    print(f"Question: {question}\n")

    handler = agent.run(question)

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
```

## See the agent in action

Now we can start asking different questions and inspect how this agent uses
different tools to handle the request.

### Information about documents

First, let's ask a question that requires the agent to find a document in the
repository.

```python
await print_agent_events("Where can I find the latest OpenDMA spec?")
```

This prints out the following steps:

```text
Question: Where can I find the latest OpenDMA spec?

Tool call: opendma_list_children
Args: {'object_id': 'sample-folder-root', 'include_folders': True, 'include_files': True}

--------------------------------------------------------------------------------

Tool result: opendma_list_children
{'items': [
    {'object_id': 'sample-folder-a', 'type_name': 'tutorial:SampleFolder', ...},
    {'object_id': 'sample-folder-b', 'type_name': 'tutorial:SampleFolder', ...},
    ...

--------------------------------------------------------------------------------

Final answer:
The latest OpenDMA specification available in the repository is titled "OpenDMA Specification 0.8." You can find it as a document with the ID `opendma-spec-document`.
```

The agent first lists the children of the root folder, finds a document in that
listing where the title suggests that it is the requested document, and then
generates the final answer.

### Information contained in documents

Now let's ask a question that requires the agent to read a document.

```python
await print_agent_events("Who is the editor of the latest OpenDMA specification?")
```

As before, the agent first tries to find a relevant document:

```text
Question: Who is the editor of the latest OpenDMA specification?

Tool call: opendma_list_children
Args: {'object_id': 'sample-folder-root', 'include_folders': True, 'include_files': True}

--------------------------------------------------------------------------------

Tool result: opendma_list_children
{'items': [
    {'object_id': 'sample-folder-a', 'type_name': 'tutorial:SampleFolder', ...},
    {'object_id': 'sample-folder-b', 'type_name': 'tutorial:SampleFolder', ...},
    ...

--------------------------------------------------------------------------------

Tool call: opendma_get_metadata
Args: {'object_id': 'opendma-spec-document'}

--------------------------------------------------------------------------------

Tool result: opendma_get_metadata
{
    'object_id': 'opendma-spec-document',
    'type_name': 'tutorial:SampleDocument',
    'aspect_names': [],
    'name': 'OpenDMA Specification 0.8',
    'metadata': {
        'opendma:Class': 'sample-document-class',
        'opendma:Aspects': [],
        'opendma:Id': 'opendma-spec-document',
        ...
    }
}
```

Once it has identified the relevant document, it reads the text content.

```text
Tool call: opendma_read_text
Args: {'object_id': 'opendma-spec-document'}

--------------------------------------------------------------------------------

Tool result: opendma_read_text
{'chunks': [
    {'text': 'OpenDMA – Open Document Management\nArchitecture\nFinal\nVersion:...
```

Reading this first chunk is already sufficient to answer the question.

```text
Final answer:
The editor of the latest OpenDMA specification (Version 0.8) is Stefan Kopf.
```