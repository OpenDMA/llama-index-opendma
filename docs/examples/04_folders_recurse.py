"""
Example of OpenDMAReader recursing a folder hierarchy and loading all documents.

Run the tutorial REST service docker container:
```
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
```
It will provide the tutorial XML repository. Make sure that this service is available by opening
http://localhost:8080/opendma
in a web browser.
"""

from llama_index.readers.opendma import OpenDMAReader

print("recursive=False")

reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
    folder_ids=["sample-folder-root"],
    recursive=False,
    include_no_content=True,
    include_unhandled_content=True,
)

documents = reader.load_data()
print(f"Loaded {len(documents)} documents")

for doc in documents:
    print(f"ID: {doc.metadata.get('opendma:Id')}")

print("\nrecursive=True")

reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
    folder_ids=["sample-folder-root"],
    recursive=True,
    include_no_content=True,
    include_unhandled_content=True,
)

documents = reader.load_data()
print(f"Loaded {len(documents)} documents")

for doc in documents:
    print(f"ID: {doc.metadata.get('opendma:Id')}")
