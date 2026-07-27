"""
Basic usage example of OpenDMAReader connecting to the tutorial-xmlrepo.

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
    document_ids=["hello-world-document"],
)

# Load documents
documents = reader.load_data()
print(f"Loaded {len(documents)} documents")

for doc in documents:
    print(f"\n{'-' * 80}")
    print(f"ID: {doc.id_}")
    print(f"Title: {doc.metadata.get('opendma:Title')}")
    print("Metadata:")
    for key, value in doc.metadata.items():
        # Truncate long values for readability
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:97] + "..."
        print(f"  {key}: {value_str}")
    print("Content:")
    print(doc.text[:200] + ("..." if len(doc.text) > 200 else ""))
