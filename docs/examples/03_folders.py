"""
Basic example of OpenDMAReader loading all documents from a folder in the tutorial-xmlrepo.

Run the tutorial REST service docker container:
```
docker run -p 8080:8080 ghcr.io/opendma/tutorial-xmlrepo:0.8.1
```
It will provide the tutorial XML repository. Make sure that this service is available by opening
http://localhost:8080/opendma
in a web browser.
"""

from llama_index.readers.opendma import OpenDMAReader

reader = OpenDMAReader(
    endpoint="http://localhost:8080/opendma",
    username="ignored",
    password="ignored",
    repository_id="sample-repo",
    folder_ids=["sample-folder-b"],
    include_no_content=True,
    include_unhandled_content=True,
)

# Load documents
documents = reader.load_data()
print(f"Loaded {len(documents)} documents")

for doc in documents:
    print("\n")
    print(f"Document ID: {doc.id_}")
    print(f"Title: {doc.metadata.get('opendma:Title')}")
    print(f"OpenDMA ID: {doc.metadata.get('opendma:Id')}")
    print(f"Content State: {doc.metadata.get('content_state')}")
