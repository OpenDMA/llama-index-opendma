"""
Example demonstrating each tool in the OpenDMAToolSpec.

Run the tutorial REST service docker container:
```
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
```
It will provide the tutorial XML repository. Make sure that this service is available by opening
http://localhost:8080/opendma
in a web browser.

Run this example from the repository root:
```
uv run --package llama-index-tools-opendma python docs/examples/06_tools.py
```
"""

import json

from llama_index.tools.opendma import OpenDMAToolSpec


def print_json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


tool_spec = OpenDMAToolSpec(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
)

tools = tool_spec.to_tool_list()

print("Tools in ToolSpec")
for tool in tools:
    print(tool.metadata.name)

tools_by_name = {tool.metadata.name: tool for tool in tools}

print("\nTool `opendma_get_metadata` for `opendma-spec-document`:")
metadata = tools_by_name["opendma_get_metadata"].call(object_id="opendma-spec-document")
print_json(metadata.raw_output)

print("\nTool `opendma_list_children` for `sample-folder-a`:")
children = tools_by_name["opendma_list_children"].call(object_id="sample-folder-a")
print_json(children.raw_output)

print("\nTool `opendma_read_text` for `hello-world-document`:")
hello_world_text = tools_by_name["opendma_read_text"].call(object_id="hello-world-document")
print_json(hello_world_text.raw_output)

print("\nTool `opendma_describe_class` for `tutorial:SampleDocument`:")
tutorial_document = tools_by_name["opendma_describe_class"].call(type_or_aspect_name="tutorial:SampleDocument")
print_json(tutorial_document.raw_output)
