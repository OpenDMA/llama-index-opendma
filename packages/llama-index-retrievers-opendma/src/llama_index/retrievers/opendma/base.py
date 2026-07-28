"""OpenDMA retrievers for LlamaIndex."""

from __future__ import annotations

import re
from typing import Any

from llama_index.core import Settings
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.callbacks import CallbackManager
from llama_index.core.ingestion import arun_transformations, run_transformations
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import BaseNode, NodeWithScore, QueryBundle, TransformComponent
from llama_index.readers.opendma import AlfrescoReader, OpenDMAReader


class OpenDMARetriever(BaseRetriever):
    """Retrieve LlamaIndex nodes from OpenDMA search results.

    The generic retriever passes the input string through unchanged as the
    OpenDMA query. Vendor-specific subclasses can override ``_build_query`` to
    construct safe repository-specific queries from natural-language input.
    """

    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        repository_id: str,
        query_language: str,
        file_extractor_per_mimetype: dict[str, BaseReader] | None = None,
        transformations: list[TransformComponent] | None = None,
        similarity_top_k: int | None = None,
        include_no_content: bool = False,
        include_unhandled_content: bool = False,
        raise_on_error: bool = False,
        metadata_fn: Any | None = None,
        callback_manager: CallbackManager | None = None,
        object_map: dict[Any, Any] | None = None,
        objects: list[Any] | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the OpenDMA retriever."""
        if similarity_top_k is not None and similarity_top_k <= 0:
            raise ValueError("similarity_top_k must be greater than 0")

        super().__init__(
            callback_manager=callback_manager,
            object_map=object_map,
            objects=objects,
            verbose=verbose,
        )

        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.repository_id = repository_id
        self.query_language = query_language
        self.file_extractor_per_mimetype = file_extractor_per_mimetype
        self.transformations = transformations
        self.similarity_top_k = similarity_top_k
        self.include_no_content = include_no_content
        self.include_unhandled_content = include_unhandled_content
        self.raise_on_error = raise_on_error
        self.metadata_fn = metadata_fn

    def _build_query(self, query: str) -> str:
        """Build the OpenDMA query from the retriever input."""
        return query

    def _get_transformations(self) -> list[TransformComponent]:
        if self.transformations is not None:
            return self.transformations
        return [Settings.node_parser]

    def _create_reader(self, query: str) -> OpenDMAReader:
        return OpenDMAReader(
            endpoint=self.endpoint,
            username=self.username,
            password=self.password,
            repository_id=self.repository_id,
            query=query,
            query_language=self.query_language,
            file_extractor_per_mimetype=self.file_extractor_per_mimetype,
            include_no_content=self.include_no_content,
            include_unhandled_content=self.include_unhandled_content,
            raise_on_error=self.raise_on_error,
            metadata_fn=self.metadata_fn,
        )

    def _nodes_from_document(self, document: BaseNode) -> list[BaseNode]:
        nodes = run_transformations(
            [document],
            self._get_transformations(),
            show_progress=False,
        )
        return list(nodes)

    async def _anodes_from_document(self, document: BaseNode) -> list[BaseNode]:
        nodes = await arun_transformations(
            [document],
            self._get_transformations(),
            show_progress=False,
        )
        return list(nodes)

    def _limit_nodes(self, nodes: list[NodeWithScore]) -> list[NodeWithScore]:
        if self.similarity_top_k is None:
            return nodes
        return nodes[: self.similarity_top_k]

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        query = self._build_query(query_bundle.query_str)
        reader = self._create_reader(query)

        nodes_with_score: list[NodeWithScore] = []
        for document in reader.lazy_load_data():
            for node in self._nodes_from_document(document):
                nodes_with_score.append(NodeWithScore(node=node, score=None))
                if (
                    self.similarity_top_k is not None
                    and len(nodes_with_score) >= self.similarity_top_k
                ):
                    return nodes_with_score
        return nodes_with_score

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        query = self._build_query(query_bundle.query_str)
        reader = self._create_reader(query)

        nodes_with_score: list[NodeWithScore] = []
        documents = await reader.alazy_load_data()
        for document in documents:
            for node in await self._anodes_from_document(document):
                nodes_with_score.append(NodeWithScore(node=node, score=None))
                if (
                    self.similarity_top_k is not None
                    and len(nodes_with_score) >= self.similarity_top_k
                ):
                    return nodes_with_score
        return nodes_with_score


class AlfrescoRetriever(OpenDMARetriever):
    """Retrieve LlamaIndex nodes from Alfresco via OpenDMA AFTS full-text search.

    The input string is converted into a safe Alfresco AFTS ``TEXT`` query. When
    ``sites`` is set, retrieval is restricted to the matching Alfresco site
    short names.
    """

    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        repository_id: str = "Alfresco",
        query_language: str = "alfresco:afts",
        sites: list[str] | None = None,
        file_extractor_per_mimetype: dict[str, BaseReader] | None = None,
        transformations: list[TransformComponent] | None = None,
        similarity_top_k: int | None = None,
        include_no_content: bool = False,
        include_unhandled_content: bool = False,
        raise_on_error: bool = False,
        metadata_fn: Any | None = None,
        callback_manager: CallbackManager | None = None,
        object_map: dict[Any, Any] | None = None,
        objects: list[Any] | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the Alfresco retriever."""
        if sites is not None:
            for site in sites:
                AlfrescoReader._validate_site_name(site)

        super().__init__(
            endpoint=endpoint,
            username=username,
            password=password,
            repository_id=repository_id,
            query_language=query_language,
            file_extractor_per_mimetype=file_extractor_per_mimetype,
            transformations=transformations,
            similarity_top_k=similarity_top_k,
            include_no_content=include_no_content,
            include_unhandled_content=include_unhandled_content,
            raise_on_error=raise_on_error,
            metadata_fn=metadata_fn,
            callback_manager=callback_manager,
            object_map=object_map,
            objects=objects,
            verbose=verbose,
        )
        self.sites = sites

    def _build_query(self, query: str) -> str:
        normalized_query = re.sub(r"\s+", " ", query).strip()
        if not normalized_query:
            raise ValueError("query must not be empty")

        afts_query = f'TEXT:"{self._escape_afts_phrase(normalized_query)}"'
        if self.sites:
            site_filters = [f'SITE:"{site}"' for site in self.sites]
            afts_query += " AND (" + " OR ".join(site_filters) + ")"

        return afts_query

    def _escape_afts_phrase(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
