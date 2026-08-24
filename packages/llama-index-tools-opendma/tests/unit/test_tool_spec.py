from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from llama_index.core.schema import Document
from llama_index.tools.opendma import OpenDMAToolSpec
from llama_index.tools.opendma.base import OpenDMASearchInput, _SearchToolSpec
from opendma.api import OdmaType


class FakePropertyInfo:
    def __init__(self, qname: str) -> None:
        self.qname = qname

    def get_qname(self) -> str:
        return self.qname


class FakeClass:
    def __init__(self, property_names: list[str]) -> None:
        self.property_names = property_names

    def get_properties(self) -> list[FakePropertyInfo]:
        return [FakePropertyInfo(property_name) for property_name in self.property_names]


class FakeReference:
    def __init__(self, object_id: str | None) -> None:
        self.object_id = object_id

    def get_id(self) -> str | None:
        return self.object_id


class FakeProperty:
    def __init__(
        self,
        prop_type: OdmaType,
        value: Any = None,
        *,
        multi_value: bool = False,
        reference_id: str | None = None,
        id_values: list[str] | None = None,
        guid_values: list[str] | None = None,
        reference_values: list[FakeReference] | None = None,
    ) -> None:
        self.prop_type = prop_type
        self.value = value
        self.multi_value = multi_value
        self.reference_id = reference_id
        self.id_values = id_values or []
        self.guid_values = guid_values or []
        self.reference_values = reference_values or []

    def get_type(self) -> OdmaType:
        return self.prop_type

    def is_multi_value(self) -> bool:
        return self.multi_value

    def get_value(self) -> Any:
        return self.value

    def get_reference_id(self) -> str | None:
        return self.reference_id

    def get_id_list(self) -> list[str]:
        return self.id_values

    def get_guid_list(self) -> list[str]:
        return self.guid_values

    def get_reference_iterable(self) -> list[FakeReference]:
        return self.reference_values


class FakeObject:
    def __init__(self, properties: dict[str, FakeProperty]) -> None:
        self.properties = properties

    def get_odma_class(self) -> FakeClass:
        return FakeClass(list(self.properties))

    def get_property(self, qname: str) -> FakeProperty:
        return self.properties[qname]


class RecordingOpenDMAToolSpec(OpenDMAToolSpec):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            **kwargs,
        )
        self.load_read_text_calls: list[str] = []

    def _load_read_text_documents(self, object_id: str) -> list[Document]:
        self.load_read_text_calls.append(object_id)
        return [
            Document(text="first chunk", metadata={"opendma:Title": "Spec"}),
            Document(text="second chunk", metadata={"opendma:Title": "Spec"}),
            Document(text="third chunk", metadata={"opendma:Title": "Spec"}),
        ]


class RecordingSearchToolSpec(_SearchToolSpec):
    query_language = "opendma:test"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            **kwargs,
        )
        self.run_search_calls: list[dict[str, Any]] = []

    def _build_search_query(
        self,
        full_text: str | None,
        in_folder: str | None,
        include_subfolder_in_folder: bool | None,
    ) -> str:
        return "|".join(
            [
                full_text or "",
                in_folder or "",
                str(include_subfolder_in_folder),
            ]
        )

    def _run_search(
        self,
        query_language: str,
        query: str,
        included_metadata: list[str] | None,
        search_result_limit: int,
    ) -> dict[str, Any]:
        self.run_search_calls.append(
            {
                "query_language": query_language,
                "query": query,
                "included_metadata": included_metadata,
                "search_result_limit": search_result_limit,
            }
        )
        return {
            "items": [],
            "has_more": False,
            "continuation_token": None,
        }


def test_open_dma_tool_spec_builds_core_tools() -> None:
    tool_spec = RecordingOpenDMAToolSpec()

    tools = tool_spec.to_tool_list()

    assert [tool.metadata.name for tool in tools] == [
        "opendma_get_metadata",
        "opendma_list_children",
        "opendma_read_text",
        "opendma_describe_class",
    ]


def test_open_dma_tool_spec_uses_explicit_schemas() -> None:
    tool_spec = RecordingOpenDMAToolSpec()

    tools_by_name = {tool.metadata.name: tool for tool in tool_spec.to_tool_list()}

    assert (
        "object_id"
        in tools_by_name["opendma_get_metadata"].metadata.get_parameters_dict()["properties"]
    )
    list_children_schema = tools_by_name["opendma_list_children"].metadata.fn_schema
    with pytest.raises(ValueError, match="include_folders and include_files"):
        list_children_schema(
            object_id="folder",
            include_folders=False,
            include_files=False,
        )


def test_read_text_pages_and_caches_documents() -> None:
    tool_spec = RecordingOpenDMAToolSpec(read_chunk_page_size=2)

    first_page = tool_spec.opendma_read_text("spec")
    second_page = tool_spec.opendma_read_text(
        "spec",
        chunk_continuation_token=first_page["chunk_continuation_token"],
    )

    assert [chunk["text"] for chunk in first_page["chunks"]] == ["first chunk", "second chunk"]
    assert first_page["has_more"] is True
    assert [chunk["text"] for chunk in second_page["chunks"]] == ["third chunk"]
    assert second_page["has_more"] is False
    assert tool_spec.load_read_text_calls == ["spec"]


def test_read_text_cache_can_be_disabled() -> None:
    tool_spec = RecordingOpenDMAToolSpec(read_text_cache_enabled=False)

    tool_spec.opendma_read_text("spec")
    tool_spec.opendma_read_text("spec")

    assert tool_spec.load_read_text_calls == ["spec", "spec"]


def test_read_text_cache_evicts_least_recently_used_entry() -> None:
    tool_spec = RecordingOpenDMAToolSpec(read_text_cache_max_objects=1)

    tool_spec.opendma_read_text("first")
    tool_spec.opendma_read_text("second")
    tool_spec.opendma_read_text("first")

    assert tool_spec.load_read_text_calls == ["first", "second", "first"]


def test_read_text_cache_expires_entries() -> None:
    tool_spec = RecordingOpenDMAToolSpec(read_text_cache_ttl_seconds=1)

    tool_spec.opendma_read_text("spec")
    tool_spec._read_text_cache["spec"].created_at -= 2
    tool_spec.opendma_read_text("spec")

    assert tool_spec.load_read_text_calls == ["spec", "spec"]


def test_constructor_validates_page_sizes() -> None:
    with pytest.raises(ValueError, match="child_page_size"):
        RecordingOpenDMAToolSpec(child_page_size=0)

    with pytest.raises(ValueError, match="read_chunk_page_size"):
        RecordingOpenDMAToolSpec(read_chunk_page_size=0)

    with pytest.raises(ValueError, match="read_text_cache_max_objects"):
        RecordingOpenDMAToolSpec(read_text_cache_max_objects=0)


def test_tool_error_matches_open_dma_tool_contract() -> None:
    tool_spec = RecordingOpenDMAToolSpec()

    result = tool_spec._tool_error("opendma_read_text", ValueError("invalid document"))

    assert result == {
        "error": True,
        "tool": "opendma_read_text",
        "error_type": "ValueError",
        "message": "invalid document",
    }


def test_tool_methods_return_input_error_for_missing_required_parameter() -> None:
    tool_spec = RecordingOpenDMAToolSpec()

    result = tool_spec.opendma_get_metadata()

    assert result == {
        "error": True,
        "tool": "opendma_get_metadata",
        "error_type": "ToolInputError",
        "message": "Missing required string parameter(s): object_id.",
    }


def test_tool_methods_return_input_error_for_unexpected_parameter() -> None:
    tool_spec = RecordingOpenDMAToolSpec()

    result = tool_spec.opendma_read_text(object_id="spec", unexpected="value")

    assert result == {
        "error": True,
        "tool": "opendma_read_text",
        "error_type": "ToolInputError",
        "message": (
            "Unexpected parameter(s): unexpected. "
            "Allowed parameters: chunk_continuation_token, object_id."
        ),
    }
    assert tool_spec.load_read_text_calls == []


def test_list_children_validates_include_options_before_repository_call() -> None:
    tool_spec = RecordingOpenDMAToolSpec()

    result = tool_spec.opendma_list_children(
        object_id="sample-folder-a",
        include_folders=False,
        include_files=False,
    )

    assert result == {
        "error": True,
        "tool": "opendma_list_children",
        "error_type": "ValueError",
        "message": "include_folders and include_files cannot both be false",
    }


def test_extract_metadata_matches_open_dma_tool_value_semantics() -> None:
    tool_spec = RecordingOpenDMAToolSpec()
    created_at = datetime(2026, 8, 24, 12, 30, tzinfo=timezone.utc)
    obj = FakeObject(
        {
            "opendma:Title": FakeProperty(OdmaType.STRING, "Spec"),
            "opendma:Content": FakeProperty(OdmaType.CONTENT, "ignored"),
            "opendma:CreatedAt": FakeProperty(OdmaType.DATETIME, created_at),
            "opendma:Repository": FakeProperty(
                OdmaType.REFERENCE,
                reference_id="sample-repo-object",
            ),
            "opendma:ContainedIn": FakeProperty(
                OdmaType.REFERENCE,
                multi_value=True,
                reference_values=[
                    FakeReference("sample-folder-root"),
                    FakeReference(None),
                    FakeReference("sample-folder-a"),
                ],
            ),
            "opendma:IdList": FakeProperty(
                OdmaType.ID,
                multi_value=True,
                id_values=["id-1", "id-2"],
            ),
            "opendma:GuidList": FakeProperty(
                OdmaType.GUID,
                multi_value=True,
                guid_values=["guid-1", "guid-2"],
            ),
            "opendma:Tags": FakeProperty(
                OdmaType.STRING,
                ["alpha", "beta"],
                multi_value=True,
            ),
        }
    )

    metadata = tool_spec._extract_metadata(obj)

    assert metadata == {
        "opendma:Title": "Spec",
        "opendma:CreatedAt": "2026-08-24T12:30:00+00:00",
        "opendma:Repository": "sample-repo-object",
        "opendma:ContainedIn": ["sample-folder-root", "sample-folder-a"],
        "opendma:IdList": ["id-1", "id-2"],
        "opendma:GuidList": ["guid-1", "guid-2"],
        "opendma:Tags": ["alpha", "beta"],
    }


def test_search_tool_spec_builds_core_tools_plus_search() -> None:
    tool_spec = RecordingSearchToolSpec()

    tools = tool_spec.to_tool_list()

    assert [tool.metadata.name for tool in tools] == [
        "opendma_get_metadata",
        "opendma_list_children",
        "opendma_read_text",
        "opendma_describe_class",
        "opendma_search",
    ]
    assert tools[-1].metadata.fn_schema is OpenDMASearchInput


def test_search_delegates_to_query_builder_and_runner() -> None:
    tool_spec = RecordingSearchToolSpec(search_result_limit=7)

    result = tool_spec.opendma_search(
        full_text="contract",
        in_folder="folder-a",
        include_subfolder_in_folder=True,
        included_metadata=["opendma:Title"],
    )

    assert result == {
        "items": [],
        "has_more": False,
        "continuation_token": None,
    }
    assert tool_spec.run_search_calls == [
        {
            "query_language": "opendma:test",
            "query": "contract|folder-a|True",
            "included_metadata": ["opendma:Title"],
            "search_result_limit": 7,
        }
    ]


def test_function_tool_call_returns_input_error_instead_of_raising() -> None:
    tool_spec = RecordingOpenDMAToolSpec()
    tools_by_name = {tool.metadata.name: tool for tool in tool_spec.to_tool_list()}

    missing_output = tools_by_name["opendma_get_metadata"].call()
    unexpected_output = tools_by_name["opendma_get_metadata"].call(
        object_id="spec",
        unknown="value",
    )

    assert missing_output.raw_output == {
        "error": True,
        "tool": "opendma_get_metadata",
        "error_type": "ToolInputError",
        "message": "Missing required string parameter(s): object_id.",
    }
    assert unexpected_output.raw_output == {
        "error": True,
        "tool": "opendma_get_metadata",
        "error_type": "ToolInputError",
        "message": ("Unexpected parameter(s): unknown. Allowed parameters: object_id."),
    }


def test_search_result_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="search_result_limit"):
        RecordingSearchToolSpec(search_result_limit=0)
