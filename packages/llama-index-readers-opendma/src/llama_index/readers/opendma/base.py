"""OpenDMA reader for LlamaIndex."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import tempfile
import warnings
from collections.abc import Callable, Generator, Iterable
from pathlib import Path
from typing import Any

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from llama_index.core.utils import get_tqdm_iterable

logger = logging.getLogger(__name__)
_missing_readers_file_warning_emitted = False


def _try_loading_included_mimetype_formats() -> dict[str, type[BaseReader]]:  # pragma: no cover
    global _missing_readers_file_warning_emitted

    try:
        from llama_index.readers.file import (
            DocxReader,
            EpubReader,
            HWPReader,
            ImageReader,
            IPYNBReader,
            MboxReader,
            PandasCSVReader,
            PandasExcelReader,
            PDFReader,
            PptxReader,
            VideoAudioReader,
        )  # pants: no-infer-dep
    except ImportError:
        if not _missing_readers_file_warning_emitted:
            logger.warning(
                "`llama-index-readers-file` package not found, some file readers will not be "
                "available if not provided by the `file_extractor_per_mimetype` parameter."
            )
            _missing_readers_file_warning_emitted = True
        return {}

    return {
        "application/epub+zip": EpubReader,
        "application/hwp": HWPReader,
        "application/pdf": PDFReader,
        "application/vnd.hancom.hwp": HWPReader,
        "application/vnd.ms-excel": PandasExcelReader,
        "application/vnd.ms-powerpoint": PptxReader,
        "application/vnd.ms-powerpoint.presentation.macroenabled.12": PptxReader,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": PptxReader,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": PandasExcelReader,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxReader,
        "audio/mpeg": VideoAudioReader,
        "image/gif": ImageReader,
        "image/jpeg": ImageReader,
        "image/png": ImageReader,
        "image/webp": ImageReader,
        "text/csv": PandasCSVReader,
        "application/mbox": MboxReader,
        "application/vnd.jupyter": IPYNBReader,
        "application/x-ipynb+json": IPYNBReader,
        "video/mp4": VideoAudioReader,
    }


class OpenDMAReader(BaseReader):
    """Load documents from OpenDMA repositories.

    The reader follows LlamaIndex's reader model: it returns LlamaIndex
    ``Document`` objects and delegates rich content parsing to MIME-type mapped
    ``BaseReader`` instances. Plain text content is decoded directly.

    All returned documents include a ``content_state`` metadata field:
    - ``Processed``: content was decoded directly or transformed by a file reader
    - ``Missing``: no content was available and ``include_no_content=True``
    - ``Unsupported``: no reader accepted the MIME type and
      ``include_unhandled_content=True``
    """

    _TEXT_MIME_TYPES = frozenset(
        {
            "application/json",
            "application/ld+json",
            "application/xml",
            "application/yaml",
            "application/x-yaml",
            "application/x-ndjson",
            "text/csv",
            "text/html",
            "text/markdown",
            "text/plain",
            "text/tsv",
            "text/xml",
            "text/x-markdown",
            "text/yaml",
            "text/x-yaml",
        }
    )

    _EXCLUDED_METADATA_KEYS = [
        "repository_id",
        "opendma_id",
        "opendma_class",
        "mime_type",
    ]
    _DROPPED_EXTRACTOR_METADATA_KEYS = {"file_name", "file_size"}

    supported_mimetype_fn: Callable[[], dict[str, type[BaseReader]]] = staticmethod(
        _try_loading_included_mimetype_formats
    )

    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        repository_id: str,
        document_ids: list[str] | None = None,
        folder_ids: list[str] | None = None,
        recursive: bool = False,
        query: str | None = None,
        query_language: str | None = None,
        file_extractor_per_mimetype: dict[str, BaseReader] | None = None,
        encoding: str = "utf-8",
        errors: str = "ignore",
        include_no_content: bool = False,
        include_unhandled_content: bool = False,
        raise_on_error: bool = False,
        metadata_fn: Callable[[Any], dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the OpenDMA reader.

        Args:
            endpoint: OpenDMA REST service endpoint.
            username: Username for authentication.
            password: Password for authentication.
            repository_id: ID of the OpenDMA repository.
            document_ids: Optional document IDs to load.
            folder_ids: Optional folder IDs to load documents from.
            recursive: Whether folder loading should include subfolders.
            query: Optional repository query.
            query_language: Query language for ``query``.
            file_extractor_per_mimetype: Mapping from MIME type to LlamaIndex
                ``BaseReader`` used to parse binary content.
            encoding: Text encoding used for direct text content decoding.
            errors: Text decoding error handling.
            include_no_content: Include documents without content as empty
                documents with ``content_state="Missing"``.
            include_unhandled_content: Include documents with unsupported MIME
                types as empty documents with ``content_state="Unsupported"``.
            raise_on_error: Whether to raise when a document cannot be loaded.
            metadata_fn: Optional callable for adding custom document metadata.
        """
        super().__init__()

        if not document_ids and not folder_ids and not query:
            raise ValueError("Must provide at least one of document_ids, folder_ids, or query.")
        if query and not query_language:
            raise ValueError("query_language must be specified when query is provided.")

        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.repository_id = repository_id
        self.document_ids = document_ids
        self.folder_ids = folder_ids
        self.recursive = recursive
        self.query = query
        self.query_language = query_language
        self.file_extractor_per_mimetype = {
            self._normalize_mime_type(mime_type): reader
            for mime_type, reader in (file_extractor_per_mimetype or {}).items()
        }
        self._default_file_extractor_cls_per_mimetype: dict[str, type[BaseReader]] | None = None
        self.encoding = encoding
        self.errors = errors
        self.include_no_content = include_no_content
        self.include_unhandled_content = include_unhandled_content
        self.raise_on_error = raise_on_error
        self.metadata_fn = metadata_fn

    def _create_session(self) -> Any:
        try:
            import opendma.remote
        except ImportError as exc:
            raise ImportError(
                "OpenDMA packages not found. Install with: pip install opendma-api opendma-remote"
            ) from exc

        return opendma.remote.connect(
            endpoint=self.endpoint,
            username=self.username,
            password=self.password,
        )

    @staticmethod
    def _normalize_mime_type(mime_type: str | None) -> str | None:
        if mime_type is None:
            return None
        return mime_type.split(";", 1)[0].strip().lower() or None

    @classmethod
    def _is_text_mime_type(cls, mime_type: str) -> bool:
        return mime_type.startswith("text/") or mime_type in cls._TEXT_MIME_TYPES

    @staticmethod
    def _content_suffix(mime_type: str, file_name: str | None) -> str:
        if file_name:
            suffix = Path(file_name).suffix
            if suffix:
                return suffix
        return mimetypes.guess_extension(mime_type) or ".bin"

    def _handle_error(self, message: str, exc: Exception) -> None:
        if self.raise_on_error:
            raise exc
        warnings.warn(f"{message}: {exc}", RuntimeWarning, stacklevel=3)

    def _extract_metadata(self, document: Any, mime_type: str | None = None) -> dict[str, Any]:
        try:
            from opendma.api import OdmaType
        except ImportError as exc:
            raise ImportError("opendma-api package not found") from exc

        document_id = str(document.get_id())
        document_class = document.get_odma_class()

        metadata: dict[str, Any] = {
            "repository_id": self.repository_id,
            "opendma_id": document_id,
            "opendma_class": str(document_class.get_qname()),
        }
        if mime_type is not None:
            metadata["mime_type"] = mime_type

        for property_info in document_class.get_properties():
            property_qname = property_info.get_qname()
            prop = document.get_property(property_qname)
            metadata_key = str(property_qname)

            prop_type = prop.get_type()
            if prop_type in (
                OdmaType.STRING,
                OdmaType.INTEGER,
                OdmaType.SHORT,
                OdmaType.LONG,
                OdmaType.FLOAT,
                OdmaType.DOUBLE,
                OdmaType.BOOLEAN,
                OdmaType.DATETIME,
            ):
                metadata[metadata_key] = prop.get_value()
            elif prop_type == OdmaType.ID:
                if prop.is_multi_value():
                    metadata[metadata_key] = [str(value) for value in prop.get_value()]
                else:
                    metadata[metadata_key] = str(prop.get_value())
            elif prop_type == OdmaType.REFERENCE:
                if prop.is_multi_value():
                    referenced_ids = []
                    for ref_obj in prop.get_reference_iterable():
                        ref_id = ref_obj.get_id()
                        if ref_id is not None:
                            referenced_ids.append(str(ref_id))
                    metadata[metadata_key] = referenced_ids
                else:
                    ref_id = prop.get_reference_id()
                    if ref_id is not None:
                        metadata[metadata_key] = str(ref_id)

        if self.metadata_fn is not None:
            metadata.update(self.metadata_fn(document))

        return metadata

    @staticmethod
    def _document_id(metadata: dict[str, Any]) -> str:
        return f"opendma://{metadata['repository_id']}/{metadata['opendma_id']}"

    def _exclude_metadata(self, documents: list[Document]) -> list[Document]:
        for document in documents:
            for key in self._EXCLUDED_METADATA_KEYS:
                if key not in document.excluded_embed_metadata_keys:
                    document.excluded_embed_metadata_keys.append(key)
                if key not in document.excluded_llm_metadata_keys:
                    document.excluded_llm_metadata_keys.append(key)
        return documents

    def _documents_from_extractor(
        self,
        content_bytes: bytes,
        mime_type: str,
        metadata: dict[str, Any],
        file_name: str | None,
    ) -> list[Document]:
        reader = self._get_file_extractor(mime_type)
        suffix = self._content_suffix(mime_type, file_name)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = Path(temp_dir, f"opendma-content{suffix}")
            temp_file_path.write_bytes(content_bytes)
            documents = reader.load_data(temp_file_path, extra_info=metadata)

        for document in documents:
            document.metadata = {**document.metadata, **metadata}
            for key in self._DROPPED_EXTRACTOR_METADATA_KEYS:
                document.metadata.pop(key, None)
            document.metadata["content_state"] = "Processed"
            document.id_ = self._document_id(metadata)
        return self._exclude_metadata(documents)

    def _get_file_extractor(self, mime_type: str) -> BaseReader:
        if mime_type not in self.file_extractor_per_mimetype:
            reader_cls = self._get_default_file_extractor_cls_per_mimetype()[mime_type]
            self.file_extractor_per_mimetype[mime_type] = reader_cls()
        return self.file_extractor_per_mimetype[mime_type]

    def _get_default_file_extractor_cls_per_mimetype(self) -> dict[str, type[BaseReader]]:
        if self._default_file_extractor_cls_per_mimetype is None:
            self._default_file_extractor_cls_per_mimetype = self.supported_mimetype_fn()
        return self._default_file_extractor_cls_per_mimetype

    def _has_file_extractor(self, mime_type: str) -> bool:
        return (
            mime_type in self.file_extractor_per_mimetype
            or mime_type in self._get_default_file_extractor_cls_per_mimetype()
        )

    def _documents_from_text(
        self,
        content_bytes: bytes,
        metadata: dict[str, Any],
    ) -> list[Document]:
        metadata["content_state"] = "Processed"
        text = content_bytes.decode(self.encoding, errors=self.errors)
        return self._exclude_metadata(
            [Document(text=text, metadata=metadata, id_=self._document_id(metadata))]
        )

    def _empty_document(self, metadata: dict[str, Any], content_state: str) -> list[Document]:
        metadata["content_state"] = content_state
        return self._exclude_metadata(
            [Document(text="", metadata=metadata, id_=self._document_id(metadata))]
        )

    def _missing_content_documents(self, metadata: dict[str, Any]) -> list[Document]:
        if self.include_no_content:
            return self._empty_document(metadata, "Missing")
        return []

    def _unsupported_content_documents(self, metadata: dict[str, Any]) -> list[Document]:
        if self.include_unhandled_content:
            return self._empty_document(metadata, "Unsupported")
        return []

    def _transform_document(self, document: Any) -> list[Document]:
        try:
            from opendma.api import OdmaDataContentElement
        except ImportError as exc:
            raise ImportError("opendma-api package not found") from exc

        content_element = document.get_primary_content_element()
        if content_element is None:
            metadata = self._extract_metadata(document)
            return self._missing_content_documents(metadata)

        mime_type = self._normalize_mime_type(content_element.get_content_type())
        metadata = self._extract_metadata(document, mime_type)

        if not isinstance(content_element, OdmaDataContentElement):
            if mime_type is None:
                return self._missing_content_documents(metadata)
            return self._unsupported_content_documents(metadata)

        file_name = content_element.get_file_name()

        if mime_type is None:
            return self._missing_content_documents(metadata)

        if self._is_text_mime_type(mime_type):
            content = content_element.get_content()
            if content is None:
                return self._missing_content_documents(metadata)

            stream = content.get_stream()
            if stream is None:
                return self._missing_content_documents(metadata)

            return self._documents_from_text(stream.read(), metadata)

        if not self._has_file_extractor(mime_type):
            return self._unsupported_content_documents(metadata)

        content = content_element.get_content()
        if content is None:
            return self._missing_content_documents(metadata)

        stream = content.get_stream()
        if stream is None:
            return self._missing_content_documents(metadata)

        content_bytes = stream.read()

        return self._documents_from_extractor(content_bytes, mime_type, metadata, file_name)

    def _iter_opendma_documents(self, session: Any) -> Iterable[Any]:
        yield from self._load_from_document_ids(session)
        yield from self._load_from_folder_ids(session)
        yield from self._load_from_query(session)

    def _load_from_document_ids(self, session: Any) -> Generator[Any, None, None]:
        if not self.document_ids:
            return

        try:
            from opendma.api import OdmaDocument, OdmaId
        except ImportError as exc:
            raise ImportError("opendma-api package not found") from exc

        repo_id = OdmaId(self.repository_id)

        for document_id in self.document_ids:
            try:
                obj = session.get_object(repo_id, OdmaId(document_id), None)
                if isinstance(obj, OdmaDocument):
                    yield obj
            except Exception as exc:
                self._handle_error(f"Failed to resolve OpenDMA document {document_id}", exc)

    def _load_from_folder_ids(self, session: Any) -> Generator[Any, None, None]:
        if not self.folder_ids:
            return

        try:
            from opendma.api import OdmaFolder, OdmaId
        except ImportError as exc:
            raise ImportError("opendma-api package not found") from exc

        repo_id = OdmaId(self.repository_id)

        for folder_id in self.folder_ids:
            try:
                obj = session.get_object(repo_id, OdmaId(folder_id), None)
                if isinstance(obj, OdmaFolder):
                    yield from self._iter_folder_documents(obj)
            except Exception as exc:
                self._handle_error(f"Failed to resolve OpenDMA folder {folder_id}", exc)

    def _iter_folder_documents(self, folder: Any) -> Generator[Any, None, None]:
        try:
            from opendma.api import OdmaDocument
        except ImportError as exc:
            raise ImportError("opendma-api package not found") from exc

        folders_to_process = [folder]
        while folders_to_process:
            current_folder = folders_to_process.pop()
            for containee in current_folder.get_containees():
                if isinstance(containee, OdmaDocument):
                    yield containee
            if self.recursive or current_folder is folder:
                folders_to_process.extend(current_folder.get_sub_folders())
            if not self.recursive:
                break

    def _load_from_query(self, session: Any) -> Generator[Any, None, None]:
        if not self.query or not self.query_language:
            return

        try:
            from opendma.api import OdmaDocument, OdmaId, OdmaQName
        except ImportError as exc:
            raise ImportError("opendma-api package not found") from exc

        repo_id = OdmaId(self.repository_id)
        query_language = OdmaQName.from_string(self.query_language)
        try:
            search_result = session.search(repo_id, query_language, self.query)
        except Exception as exc:
            self._handle_error("Failed to execute OpenDMA query", exc)
            return

        for obj in search_result.get_objects():
            if isinstance(obj, OdmaDocument):
                yield obj

    def lazy_load_data(self, show_progress: bool = False) -> Iterable[Document]:
        """Load OpenDMA documents lazily.

        Args:
            show_progress: Whether to show a progress bar while transforming
                resolved OpenDMA documents.

        Yields:
            Loaded LlamaIndex documents.
        """
        for documents in self.iter_data(show_progress=show_progress):
            yield from documents

    def load_data(self, show_progress: bool = False) -> list[Document]:
        """Load OpenDMA documents.

        Args:
            show_progress: Whether to show a progress bar while transforming
                resolved OpenDMA documents.

        Returns:
            Loaded LlamaIndex documents.
        """
        return list(self.lazy_load_data(show_progress=show_progress))

    async def aload_data(self, show_progress: bool = False) -> list[Document]:
        """Load OpenDMA documents asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.load_data(show_progress))

    def iter_data(self, show_progress: bool = False) -> Generator[list[Document], Any, Any]:
        """Load OpenDMA documents iteratively."""
        session = self._create_session()

        try:
            opendma_documents = list(self._iter_opendma_documents(session))
            iterable = get_tqdm_iterable(
                opendma_documents,
                show_progress=show_progress,
                desc="Loading OpenDMA documents",
            )
            for opendma_document in iterable:
                try:
                    documents = self._transform_document(opendma_document)
                except Exception as exc:
                    self._handle_error(
                        f"Failed to load OpenDMA document {opendma_document.get_id()}",
                        exc,
                    )
                    continue
                if documents:
                    yield documents
        finally:
            session.close()
