"""Integration tests against the OpenDMA tutorial repository."""

from __future__ import annotations

import asyncio

import pytest
from llama_index.core.schema import Document
from llama_index.readers.opendma import OpenDMAReader


def assert_hello_world_document(document: Document) -> None:
    """Assert the expected hello-world tutorial document metadata and content."""
    assert document.id_ == "opendma://sample-repo/hello-world-document"
    assert "source" not in document.metadata
    assert document.metadata["repository_id"] == "sample-repo"
    assert document.metadata["opendma_id"] == "hello-world-document"
    assert document.metadata["opendma_class"] == "tutorial:SampleDocument"
    assert document.metadata["mime_type"] == "text/plain"
    assert document.metadata["content_state"] == "Processed"
    assert "file_name" not in document.metadata
    assert "file_size" not in document.metadata
    assert document.metadata["opendma:Title"] == "Hello, World!"
    assert "Lorem ipsum dolor sit amet, consectetur adipiscing elit" in document.text


def hello_world_reader(tutorial_endpoint: str) -> OpenDMAReader:
    return OpenDMAReader(
        endpoint=tutorial_endpoint,
        username="ignored",
        password="ignored",
        repository_id="sample-repo",
        document_ids=["hello-world-document"],
    )


@pytest.mark.integration
def test_load_hello_world_document(tutorial_endpoint: str) -> None:
    reader = hello_world_reader(tutorial_endpoint)

    documents = reader.load_data()

    assert len(documents) == 1
    assert_hello_world_document(documents[0])


@pytest.mark.integration
def test_lazy_load_hello_world_document(tutorial_endpoint: str) -> None:
    reader = hello_world_reader(tutorial_endpoint)

    documents = list(reader.lazy_load_data())

    assert len(documents) == 1
    assert_hello_world_document(documents[0])


@pytest.mark.integration
def test_iter_data_hello_world_document(tutorial_endpoint: str) -> None:
    reader = hello_world_reader(tutorial_endpoint)

    document_batches = list(reader.iter_data())

    assert len(document_batches) == 1
    assert len(document_batches[0]) == 1
    assert_hello_world_document(document_batches[0][0])


@pytest.mark.integration
def test_aload_hello_world_document(tutorial_endpoint: str) -> None:
    reader = hello_world_reader(tutorial_endpoint)

    documents = asyncio.run(reader.aload_data())

    assert len(documents) == 1
    assert_hello_world_document(documents[0])


@pytest.mark.integration
@pytest.mark.parametrize(
    ("recursive", "expected_document_ids"),
    [
        (
            False,
            [
                "hello-world-document",
                "opendma-spec-document",
            ],
        ),
        (
            True,
            [
                "hello-world-document",
                "opendma-spec-document",
                "sample-no-content-document",
                "sample-document-b1",
                "sample-document-b2",
                "sample-document-a1",
                "sample-document-a2",
            ],
        ),
    ],
)
def test_load_documents_from_folder(
    tutorial_endpoint: str,
    recursive: bool,
    expected_document_ids: list[str],
) -> None:
    reader = OpenDMAReader(
        endpoint=tutorial_endpoint,
        username="ignored",
        password="ignored",
        repository_id="sample-repo",
        folder_ids=["sample-folder-root"],
        recursive=recursive,
        include_no_content=True,
        include_unhandled_content=True,
    )

    documents = reader.load_data()

    assert [document.metadata["opendma:Id"] for document in documents] == expected_document_ids


@pytest.mark.integration
def test_load_documents_with_all_content_states(tutorial_endpoint: str) -> None:
    expected_content_states = {
        "hello-world-document": "Processed",
        "sample-document-a1": "Unsupported",
        "sample-no-content-document": "Missing",
    }
    reader = OpenDMAReader(
        endpoint=tutorial_endpoint,
        username="ignored",
        password="ignored",
        repository_id="sample-repo",
        document_ids=list(expected_content_states),
        include_no_content=True,
        include_unhandled_content=True,
    )

    documents = reader.load_data()

    assert len(documents) == len(expected_content_states)
    content_states_by_id = {
        document.metadata["opendma:Id"]: document.metadata["content_state"]
        for document in documents
    }
    assert content_states_by_id == expected_content_states
    empty_document_ids = {
        document.metadata["opendma:Id"] for document in documents if document.text == ""
    }
    assert empty_document_ids == {"sample-document-a1", "sample-no-content-document"}
