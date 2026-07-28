"""Unit tests for OpenDMA retrievers."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

import pytest
from llama_index.core.schema import (
    BaseNode,
    Document,
    NodeWithScore,
    QueryBundle,
    TextNode,
    TransformComponent,
)
from llama_index.retrievers.opendma import AlfrescoRetriever, OpenDMARetriever


class RecordingReader:
    """Reader test double that records document consumption."""

    def __init__(self, retriever: Any) -> None:
        self.retriever = retriever

    def lazy_load_data(self) -> Iterable[Document]:
        for index in range(self.retriever.document_count):
            document = Document(
                text="result" if self.retriever.document_count == 1 else f"result {index}",
                id_=f"document-{index}",
            )
            self.retriever.yielded_documents += 1
            yield document

    async def alazy_load_data(self) -> Iterable[Document]:
        return self.lazy_load_data()


class RecordingOpenDMARetriever(OpenDMARetriever):
    """Retriever test double that records the query passed to reader creation."""

    created_query: str | None
    document_count: int
    yielded_documents: int

    def __init__(self, *args: Any, document_count: int = 1, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.created_query = None
        self.document_count = document_count
        self.yielded_documents = 0

    def _create_reader(self, query: str) -> RecordingReader:  # type: ignore[override]
        self.created_query = query
        return RecordingReader(self)


class RecordingAlfrescoRetriever(AlfrescoRetriever):
    """Alfresco retriever test double that records the generated AFTS query."""

    created_query: str | None
    document_count: int
    yielded_documents: int

    def __init__(self, *args: Any, document_count: int = 1, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.created_query = None
        self.document_count = document_count
        self.yielded_documents = 0

    def _create_reader(self, query: str) -> RecordingReader:  # type: ignore[override]
        self.created_query = query
        return RecordingReader(self)


class SplitFirstDocument(TransformComponent):
    """Test transformation that splits the first document into two nodes."""

    def __call__(self, nodes: list[BaseNode], **_: Any) -> list[BaseNode]:  # type: ignore[override]
        node = nodes[0]
        text = node.get_content()
        return [
            TextNode(text=f"{text} chunk 0", id_=f"{node.node_id}-chunk-0"),
            TextNode(text=f"{text} chunk 1", id_=f"{node.node_id}-chunk-1"),
        ]


def node_texts(nodes: list[NodeWithScore]) -> list[str]:
    return [node.node.get_content() for node in nodes]


class TestOpenDMARetriever:
    """Test cases for OpenDMARetriever."""

    def test_retrieve_passes_query_through_unchanged(self) -> None:
        retriever = RecordingOpenDMARetriever(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            query_language="test:test-query-language",
            transformations=[],
        )

        nodes = retriever.retrieve("test-raw input")

        assert node_texts(nodes) == ["result"]
        assert retriever.created_query == "test-raw input"

    def test_retrieve_accepts_query_bundle(self) -> None:
        retriever = RecordingOpenDMARetriever(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            query_language="test:test-query-language",
            transformations=[],
        )

        retriever.retrieve(QueryBundle("test-query-bundle input"))

        assert retriever.created_query == "test-query-bundle input"

    def test_retrieve_returns_all_nodes_without_similarity_top_k(self) -> None:
        retriever = RecordingOpenDMARetriever(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            query_language="test:test-query-language",
            transformations=[],
            document_count=3,
        )

        nodes = retriever.retrieve("test-raw input")

        assert node_texts(nodes) == ["result 0", "result 1", "result 2"]
        assert retriever.yielded_documents == 3

    def test_retrieve_respects_similarity_top_k(self) -> None:
        retriever = RecordingOpenDMARetriever(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            query_language="test:test-query-language",
            transformations=[],
            similarity_top_k=2,
            document_count=5,
        )

        nodes = retriever.retrieve("test-raw input")

        assert node_texts(nodes) == ["result 0", "result 1"]
        assert retriever.yielded_documents == 2

    def test_retrieve_applies_similarity_top_k_after_transformations(self) -> None:
        retriever = RecordingOpenDMARetriever(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            query_language="test:test-query-language",
            transformations=[SplitFirstDocument()],
            similarity_top_k=1,
            document_count=2,
        )

        nodes = retriever.retrieve("test-raw input")

        assert node_texts(nodes) == ["result 0 chunk 0"]
        assert retriever.yielded_documents == 1

    def test_aretrieve_respects_similarity_top_k(self) -> None:
        retriever = RecordingOpenDMARetriever(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            query_language="test:test-query-language",
            transformations=[],
            similarity_top_k=2,
            document_count=5,
        )

        nodes = asyncio.run(retriever.aretrieve("test-raw input"))

        assert node_texts(nodes) == ["result 0", "result 1"]
        assert retriever.yielded_documents == 2

    @pytest.mark.parametrize("similarity_top_k", [0, -1])
    def test_init_rejects_non_positive_similarity_top_k(self, similarity_top_k: int) -> None:
        with pytest.raises(ValueError, match="similarity_top_k must be greater than 0"):
            RecordingOpenDMARetriever(
                endpoint="http://localhost:8080/opendma",
                username="ignored",
                password="ignored",
                repository_id="sample-repo",
                query_language="test:test-query-language",
                similarity_top_k=similarity_top_k,
            )

    def test_retrieve_returns_node_with_score(self) -> None:
        retriever = RecordingOpenDMARetriever(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            query_language="test:test-query-language",
            transformations=[],
        )

        nodes = retriever.retrieve("test-raw input")

        assert isinstance(nodes[0], NodeWithScore)
        assert nodes[0].score is None


class TestAlfrescoRetriever:
    """Test cases for AlfrescoRetriever."""

    def test_retrieve_builds_afts_full_text_query(self) -> None:
        retriever = RecordingAlfrescoRetriever(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
            transformations=[],
        )

        retriever.retrieve("website design")

        assert retriever.repository_id == "Alfresco"
        assert retriever.query_language == "alfresco:afts"
        assert retriever.created_query == 'TEXT:"website design"'

    def test_retrieve_respects_inherited_similarity_top_k(self) -> None:
        retriever = RecordingAlfrescoRetriever(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
            transformations=[],
            similarity_top_k=1,
            document_count=3,
        )

        nodes = retriever.retrieve("website design")

        assert node_texts(nodes) == ["result 0"]
        assert retriever.yielded_documents == 1

    def test_retrieve_escapes_afts_phrase(self) -> None:
        retriever = RecordingAlfrescoRetriever(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
            transformations=[],
        )

        retriever.retrieve(r'website "design" \ localisation')

        assert retriever.created_query == r'TEXT:"website \"design\" \\ localisation"'

    def test_retrieve_adds_site_filter(self) -> None:
        retriever = RecordingAlfrescoRetriever(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
            transformations=[],
            sites=["swsdp", "engineering"],
        )

        retriever.retrieve("website design")

        assert retriever.created_query == (
            'TEXT:"website design" AND (SITE:"swsdp" OR SITE:"engineering")'
        )

    def test_retrieve_rejects_empty_query(self) -> None:
        retriever = RecordingAlfrescoRetriever(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
            transformations=[],
        )

        with pytest.raises(ValueError, match="query must not be empty"):
            retriever.retrieve("  \n\t  ")

    @pytest.mark.parametrize("character", ['"', "*", "\\", ">", "<", "?", "/", ":", "|"])
    def test_init_rejects_site_names_with_forbidden_characters(self, character: str) -> None:
        with pytest.raises(ValueError, match="Alfresco site names cannot contain"):
            RecordingAlfrescoRetriever(
                endpoint="http://localhost:7070/opendma/alf",
                username="admin",
                password="admin",
                sites=[f"site{character}name"],
            )

    @pytest.mark.parametrize(
        ("site_name", "message"),
        [
            ("site.", "end with a period"),
            ("site ", "end with a space"),
        ],
    )
    def test_init_rejects_site_names_with_invalid_endings(
        self,
        site_name: str,
        message: str,
    ) -> None:
        with pytest.raises(ValueError, match=message):
            RecordingAlfrescoRetriever(
                endpoint="http://localhost:7070/opendma/alf",
                username="admin",
                password="admin",
                sites=[site_name],
            )
