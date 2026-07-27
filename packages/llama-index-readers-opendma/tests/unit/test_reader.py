"""Unit tests for OpenDMAReader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from llama_index.readers.opendma import OpenDMAReader


class BinaryReader(BaseReader):
    def load_data(
        self,
        file: Path,
        extra_info: dict[str, Any] | None = None,
        **_: Any,
    ) -> list[Document]:
        return [
            Document(
                text=file.read_bytes().decode("utf-8"),
                metadata={"reader": "binary", **(extra_info or {})},
            )
        ]


class DefaultBinaryReader(BinaryReader):
    pass


class TestOpenDMAReader:
    """Test cases for pure OpenDMAReader behavior."""

    def test_init_requires_source_selector(self) -> None:
        with pytest.raises(ValueError, match="Must provide at least one"):
            OpenDMAReader(
                endpoint="http://localhost:8080/opendma",
                username="admin",
                password="admin",
                repository_id="sample-repo",
            )

    def test_init_with_query_without_language_raises(self) -> None:
        with pytest.raises(ValueError, match="query_language must be specified"):
            OpenDMAReader(
                endpoint="http://localhost:8080/opendma",
                username="admin",
                password="admin",
                repository_id="sample-repo",
                query="SELECT * FROM opendma:Document",
            )

    def test_init_normalizes_file_extractor_mime_types(self) -> None:
        extractor = BinaryReader()

        reader = OpenDMAReader(
            endpoint="http://localhost:8080/opendma",
            username="admin",
            password="admin",
            repository_id="sample-repo",
            document_ids=["document"],
            file_extractor_per_mimetype={" Application/PDF ; charset=binary ": extractor},
        )

        assert reader.file_extractor_per_mimetype == {"application/pdf": extractor}

    def test_content_suffix_prefers_file_name_extension(self) -> None:
        assert OpenDMAReader._content_suffix("application/pdf", "contract.custom") == ".custom"

    def test_content_suffix_falls_back_to_mime_type(self) -> None:
        assert OpenDMAReader._content_suffix("application/pdf", None) == ".pdf"

    def test_document_id_uses_repository_and_document_id(self) -> None:
        document_id = OpenDMAReader._document_id(
            {"repository_id": "sample-repo", "opendma_id": "hello-world-document"}
        )

        assert document_id == "opendma://sample-repo/hello-world-document"

    @pytest.mark.parametrize(
        "mime_type",
        [
            "text/plain",
            "text/custom",
            "application/json",
            "application/xml",
        ],
    )
    def test_is_text_mime_type_accepts_textual_types(self, mime_type: str) -> None:
        assert OpenDMAReader._is_text_mime_type(mime_type) is True

    def test_is_text_mime_type_rejects_binary_types(self) -> None:
        assert OpenDMAReader._is_text_mime_type("application/pdf") is False

    def test_has_file_extractor_uses_user_mapping(self) -> None:
        reader = OpenDMAReader(
            endpoint="http://localhost:8080/opendma",
            username="admin",
            password="admin",
            repository_id="sample-repo",
            document_ids=["document"],
            file_extractor_per_mimetype={"application/pdf": BinaryReader()},
        )

        assert reader._has_file_extractor("application/pdf") is True

    def test_get_file_extractor_lazily_instantiates_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            OpenDMAReader,
            "supported_mimetype_fn",
            staticmethod(lambda: {"application/pdf": DefaultBinaryReader}),
        )
        reader = OpenDMAReader(
            endpoint="http://localhost:8080/opendma",
            username="admin",
            password="admin",
            repository_id="sample-repo",
            document_ids=["document"],
        )

        extractor = reader._get_file_extractor("application/pdf")

        assert isinstance(extractor, DefaultBinaryReader)
        assert reader.file_extractor_per_mimetype["application/pdf"] is extractor

    def test_user_extractor_overrides_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            OpenDMAReader,
            "supported_mimetype_fn",
            staticmethod(lambda: {"application/pdf": DefaultBinaryReader}),
        )
        user_extractor = BinaryReader()
        reader = OpenDMAReader(
            endpoint="http://localhost:8080/opendma",
            username="admin",
            password="admin",
            repository_id="sample-repo",
            document_ids=["document"],
            file_extractor_per_mimetype={"application/pdf": user_extractor},
        )

        extractor = reader._get_file_extractor("application/pdf")

        assert extractor is user_extractor
