"""Unit tests for OpenDMA LlamaIndex tools."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any, cast

import llama_index.tools.opendma.base as tools_module
import pytest
from llama_index.core.schema import Document
from llama_index.tools.opendma import (
    AlfrescoToolSpec,
    DocumentumToolSpec,
    FileNetP8ToolSpec,
    OnBaseToolSpec,
    OpenDMAToolSpec,
)
from llama_index.tools.opendma.base import OpenDMASearchInput, _SearchToolSpec
from opendma.api import (
    CLASS_CLASS,
    CLASS_DOCUMENT,
    CLASS_FOLDER,
    CLASS_PROPERTYINFO,
    PROPERTY_ASPECTS,
    PROPERTY_CLASS,
    PROPERTY_DATATYPE,
    PROPERTY_DISPLAYNAME,
    PROPERTY_HIDDEN,
    PROPERTY_MULTIVALUE,
    PROPERTY_NAME,
    PROPERTY_NAMESPACE,
    PROPERTY_PROPERTIES,
    PROPERTY_READONLY,
    PROPERTY_REFERENCECLASS,
    PROPERTY_REQUIRED,
    PROPERTY_SYSTEM,
    OdmaClass,
    OdmaCoreObject,
    OdmaId,
    OdmaObject,
    OdmaProperty,
    OdmaPropertyImpl,
    OdmaPropertyNotFoundException,
    OdmaQName,
    OdmaRepository,
    OdmaSearchResult,
    OdmaServiceException,
    OdmaSession,
    OdmaType,
    odma_create_proxy,
)


class FakeCoreObject(OdmaCoreObject):
    """OpenDMA core object test double used by generated object proxies."""

    def __init__(
        self,
        properties: dict[OdmaQName, OdmaProperty],
        complete: bool = True,
    ) -> None:
        self.properties = properties
        self.complete = complete

    def get_property(self, property_name: OdmaQName) -> OdmaProperty:
        try:
            return self.properties[property_name]
        except KeyError:
            if self.complete:
                raise OdmaPropertyNotFoundException(propertyName=property_name) from None
            self.prepare_properties([property_name], False)
            try:
                return self.properties[property_name]
            except KeyError:
                raise OdmaPropertyNotFoundException(propertyName=property_name) from None

    def prepare_properties(
        self,
        property_names: list[OdmaQName] | None,
        refresh: bool,
    ) -> None:
        pass

    def set_property(self, property_name: OdmaQName, new_value: Any) -> None:
        prop = self.get_property(property_name)
        prop.set_value(new_value)

    def is_dirty(self) -> bool:
        return any(prop.is_dirty() for prop in self.properties.values())

    def save(self) -> None:
        pass

    def instance_of(self, class_or_aspect_name: OdmaQName) -> bool:
        test = self._internal_get_odma_class()
        while test is not None:
            if test.get_qname() == class_or_aspect_name:
                return True
            aspects = test.get_included_aspects()
            if aspects is not None:
                for aspect in aspects:
                    if aspect.get_qname() == class_or_aspect_name:
                        return True
            test = test.get_super_class()
        for aspect in self._internal_get_odma_aspects():
            while aspect is not None:
                if aspect.get_qname() == class_or_aspect_name:
                    return True
                aspect = aspect.get_super_class()
        return False

    def _internal_get_odma_class(self) -> Any:
        clazz = self.get_property(PROPERTY_CLASS).get_reference()
        if isinstance(clazz, OdmaClass):
            return clazz
        raise OdmaServiceException("Invalid class of object")

    def _internal_get_odma_aspects(self) -> Iterable[OdmaClass]:
        return cast(
            Iterable[OdmaClass],
            self.get_property(PROPERTY_ASPECTS).get_reference_iterable(),
        )


def create_fake_document(props: list[OdmaProperty]) -> OdmaObject:
    fake_class = create_fake_class(OdmaQName("fake", "Document"), props)
    properties: dict[OdmaQName, OdmaProperty] = {
        PROPERTY_CLASS: OdmaPropertyImpl(
            PROPERTY_CLASS,
            fake_class,
            None,
            OdmaType.REFERENCE,
            False,
            False,
        ),
        PROPERTY_ASPECTS: OdmaPropertyImpl(
            PROPERTY_ASPECTS,
            [],
            None,
            OdmaType.REFERENCE,
            True,
            False,
        ),
    }
    properties.update({prop.get_name(): prop for prop in props})
    return odma_create_proxy([CLASS_DOCUMENT], FakeCoreObject(properties))


def create_fake_folder(props: list[OdmaProperty]) -> OdmaObject:
    fake_class = create_fake_class(OdmaQName("fake", "Folder"), props)
    properties: dict[OdmaQName, OdmaProperty] = {
        PROPERTY_CLASS: OdmaPropertyImpl(
            PROPERTY_CLASS,
            fake_class,
            None,
            OdmaType.REFERENCE,
            False,
            False,
        ),
        PROPERTY_ASPECTS: OdmaPropertyImpl(
            PROPERTY_ASPECTS,
            [],
            None,
            OdmaType.REFERENCE,
            True,
            False,
        ),
    }
    properties.update({prop.get_name(): prop for prop in props})
    return odma_create_proxy([CLASS_FOLDER], FakeCoreObject(properties))


def create_fake_property_info(prop: OdmaProperty) -> OdmaObject:
    prop_name = prop.get_name()
    properties: dict[OdmaQName, OdmaProperty] = {
        PROPERTY_NAME: OdmaPropertyImpl(
            PROPERTY_NAME,
            prop_name.name,
            None,
            OdmaType.STRING,
            False,
            False,
        ),
        PROPERTY_NAMESPACE: OdmaPropertyImpl(
            PROPERTY_NAMESPACE,
            prop_name.namespace,
            None,
            OdmaType.STRING,
            False,
            False,
        ),
        PROPERTY_DISPLAYNAME: OdmaPropertyImpl(
            PROPERTY_DISPLAYNAME,
            prop_name.name,
            None,
            OdmaType.STRING,
            False,
            False,
        ),
        PROPERTY_DATATYPE: OdmaPropertyImpl(
            PROPERTY_DATATYPE,
            prop.get_type().value,
            None,
            OdmaType.INTEGER,
            False,
            False,
        ),
        PROPERTY_REFERENCECLASS: OdmaPropertyImpl(
            PROPERTY_REFERENCECLASS,
            None,
            None,
            OdmaType.REFERENCE,
            False,
            False,
        ),
        PROPERTY_MULTIVALUE: OdmaPropertyImpl(
            PROPERTY_MULTIVALUE,
            prop.is_multi_value(),
            None,
            OdmaType.BOOLEAN,
            False,
            False,
        ),
        PROPERTY_REQUIRED: OdmaPropertyImpl(
            PROPERTY_REQUIRED,
            False,
            None,
            OdmaType.BOOLEAN,
            False,
            False,
        ),
        PROPERTY_READONLY: OdmaPropertyImpl(
            PROPERTY_READONLY,
            True,
            None,
            OdmaType.BOOLEAN,
            False,
            False,
        ),
        PROPERTY_HIDDEN: OdmaPropertyImpl(
            PROPERTY_HIDDEN,
            False,
            None,
            OdmaType.BOOLEAN,
            False,
            False,
        ),
        PROPERTY_SYSTEM: OdmaPropertyImpl(
            PROPERTY_SYSTEM,
            False,
            None,
            OdmaType.BOOLEAN,
            False,
            False,
        ),
    }
    return odma_create_proxy([CLASS_PROPERTYINFO], FakeCoreObject(properties))


def create_fake_class(class_name: OdmaQName, props: list[OdmaProperty]) -> OdmaObject:
    properties: dict[OdmaQName, OdmaProperty] = {
        PROPERTY_NAME: OdmaPropertyImpl(
            PROPERTY_NAME,
            class_name.name,
            None,
            OdmaType.STRING,
            False,
            False,
        ),
        PROPERTY_NAMESPACE: OdmaPropertyImpl(
            PROPERTY_NAMESPACE,
            class_name.namespace,
            None,
            OdmaType.STRING,
            False,
            False,
        ),
        PROPERTY_PROPERTIES: OdmaPropertyImpl(
            PROPERTY_PROPERTIES,
            [create_fake_property_info(prop) for prop in props],
            None,
            OdmaType.REFERENCE,
            True,
            False,
        ),
    }
    return odma_create_proxy([CLASS_CLASS], FakeCoreObject(properties))


def create_fake_doc_a() -> OdmaObject:
    props = [
        OdmaPropertyImpl(
            OdmaQName("opendma", "Id"),
            OdmaId("doc-a"),
            None,
            OdmaType.ID,
            False,
            False,
        ),
        OdmaPropertyImpl(
            OdmaQName("opendma", "Title"),
            "Hello, doc!",
            None,
            OdmaType.STRING,
            False,
            False,
        ),
        OdmaPropertyImpl(
            OdmaQName("test", "CustomProperty"),
            "custom value",
            None,
            OdmaType.STRING,
            False,
            False,
        ),
    ]
    return create_fake_document(props)


def create_fake_folder_a() -> OdmaObject:
    props = [
        OdmaPropertyImpl(
            OdmaQName("opendma", "Id"),
            OdmaId("folder-a"),
            None,
            OdmaType.ID,
            False,
            False,
        ),
        OdmaPropertyImpl(
            OdmaQName("opendma", "Name"),
            "Hello, Folder!",
            None,
            OdmaType.STRING,
            False,
            False,
        ),
    ]
    return create_fake_folder(props)


def create_fake_site() -> OdmaObject:
    props = [
        OdmaPropertyImpl(
            OdmaQName("opendma", "Id"),
            OdmaId("site-swsdp"),
            None,
            OdmaType.ID,
            False,
            False,
        ),
        OdmaPropertyImpl(
            OdmaQName("alfresco:cm", "name"),
            "swsdp",
            None,
            OdmaType.STRING,
            False,
            False,
        ),
        OdmaPropertyImpl(
            OdmaQName("alfresco:cm", "title"),
            "Sample: Web Site Design Project",
            None,
            OdmaType.STRING,
            False,
            False,
        ),
        OdmaPropertyImpl(
            OdmaQName("alfresco:cm", "description"),
            "This is a Sample Alfresco Team site.",
            None,
            OdmaType.STRING,
            False,
            False,
        ),
    ]
    return create_fake_folder(props)


class FakeSearchResult(OdmaSearchResult):
    """OpenDMA search result test double."""

    _items: list[OdmaObject]

    def __init__(self, items: list[OdmaObject]) -> None:
        self._items = items

    def get_objects(self) -> Iterable[OdmaObject]:
        return iter(self._items)

    def get_size(self) -> int:
        return self._items.__len__()


class FakeOdmaSession(OdmaSession):
    """OpenDMA session test double that records calls."""

    def __init__(self, objects: list[OdmaObject] | None = None) -> None:
        self.objects = objects or [create_fake_doc_a(), create_fake_folder_a()]
        self.query_language: str | None = None
        self.query: str | None = None
        self.closed = False

    def get_repository_ids(self) -> list[OdmaId]:
        raise RuntimeError("get_repository_ids is not implemented for this test")

    def get_repository(self, repository_id: OdmaId) -> OdmaRepository:
        _ = repository_id
        raise RuntimeError("get_repository is not implemented for this test")

    def get_object(
        self,
        repository_id: OdmaId,
        object_id: OdmaId,
        property_names: list[OdmaQName] | None,
    ) -> OdmaObject:
        _ = repository_id, property_names
        for obj in self.objects:
            if obj.get_id() == object_id:
                return obj
        raise OdmaServiceException(f"Object not found: {object_id}")

    def search(
        self,
        repository_id: OdmaId,
        query_language: OdmaQName,
        query: str,
    ) -> OdmaSearchResult:
        _ = repository_id
        self.query_language = str(query_language)
        self.query = query
        return FakeSearchResult(self.objects)

    def get_supported_query_languages(self) -> list[OdmaQName]:
        raise RuntimeError("get_supported_query_languages is not implemented for this test")

    def close(self) -> None:
        self.closed = True


class RecordingSearchToolSpec(_SearchToolSpec):
    query_language = "opendma:test"

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


class TestOpenDMAToolSpec:
    """Test cases for OpenDMAToolSpec public tool contract."""

    def test_open_dma_tool_spec_builds_core_tools(self) -> None:
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )

        tools = tool_spec.to_tool_list()

        assert [tool.metadata.name for tool in tools] == [
            "opendma_get_metadata",
            "opendma_list_children",
            "opendma_read_text",
            "opendma_describe_class",
        ]

    def test_open_dma_tool_spec_uses_explicit_schemas(self) -> None:
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )

        tools_by_name = {tool.metadata.name: tool for tool in tool_spec.to_tool_list()}

        assert (
            "object_id"
            in tools_by_name["opendma_get_metadata"].metadata.get_parameters_dict()["properties"]
        )
        list_children_schema = tools_by_name["opendma_list_children"].metadata.fn_schema
        assert list_children_schema is not None
        with pytest.raises(ValueError, match="include_folders and include_files"):
            list_children_schema(
                object_id="folder",
                include_folders=False,
                include_files=False,
            )

    def test_read_text_uses_cached_documents_for_next_page(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls = []

        class FakeOpenDMAReader:
            def __init__(self, **kwargs: Any) -> None:
                calls.append(kwargs["document_ids"][0])

            def load_data(self) -> list[Document]:
                return [
                    Document(text="chunk one", metadata={"opendma:Title": "Doc"}),
                    Document(text="chunk two", metadata={"opendma:Title": "Doc"}),
                ]

        monkeypatch.setattr(tools_module, "OpenDMAReader", FakeOpenDMAReader)

        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            read_chunk_page_size=1,
        )

        first_page = tool_spec.opendma_read_text("doc-1")
        second_page = tool_spec.opendma_read_text(
            "doc-1",
            chunk_continuation_token=first_page["chunk_continuation_token"],
        )

        assert calls == ["doc-1"]
        assert first_page["chunks"][0]["text"] == "chunk one"
        assert second_page["chunks"][0]["text"] == "chunk two"

    def test_read_text_cache_can_be_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls = []

        class FakeOpenDMAReader:
            def __init__(self, **kwargs: Any) -> None:
                calls.append(kwargs["document_ids"][0])

            def load_data(self) -> list[Document]:
                return [Document(text="chunk", metadata={})]

        monkeypatch.setattr(tools_module, "OpenDMAReader", FakeOpenDMAReader)

        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            read_text_cache_enabled=False,
        )

        tool_spec.opendma_read_text("doc-1")
        tool_spec.opendma_read_text("doc-1")

        assert calls == ["doc-1", "doc-1"]

    def test_read_text_cache_expires_after_ttl(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls = []
        now = 1000.0

        class FakeOpenDMAReader:
            def __init__(self, **kwargs: Any) -> None:
                calls.append(kwargs["document_ids"][0])

            def load_data(self) -> list[Document]:
                return [Document(text="chunk", metadata={})]

        monkeypatch.setattr(tools_module, "OpenDMAReader", FakeOpenDMAReader)
        monkeypatch.setattr(tools_module, "monotonic", lambda: now)

        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            read_text_cache_ttl_seconds=10,
        )

        tool_spec.opendma_read_text("doc-1")
        now = 1011.0
        tool_spec.opendma_read_text("doc-1")

        assert calls == ["doc-1", "doc-1"]

    def test_read_text_cache_evicts_least_recently_used_object(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls = []

        class FakeOpenDMAReader:
            def __init__(self, **kwargs: Any) -> None:
                self.object_id = kwargs["document_ids"][0]
                calls.append(self.object_id)

            def load_data(self) -> list[Document]:
                return [Document(text=f"chunk {self.object_id}", metadata={})]

        monkeypatch.setattr(tools_module, "OpenDMAReader", FakeOpenDMAReader)

        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            read_text_cache_max_objects=2,
        )

        tool_spec.opendma_read_text("doc-1")
        tool_spec.opendma_read_text("doc-2")
        tool_spec.opendma_read_text("doc-1")
        tool_spec.opendma_read_text("doc-3")
        tool_spec.opendma_read_text("doc-2")

        assert calls == ["doc-1", "doc-2", "doc-3", "doc-2"]

    @pytest.mark.parametrize(
        ("child_page_size", "read_chunk_page_size"),
        [(0, 1), (1, 0)],
    )
    def test_init_rejects_non_positive_page_sizes(
        self,
        child_page_size: int,
        read_chunk_page_size: int,
    ) -> None:
        with pytest.raises(ValueError, match="must be greater than 0"):
            OpenDMAToolSpec(
                endpoint="http://localhost:8080/opendma",
                username="ignored",
                password="ignored",
                repository_id="sample-repo",
                child_page_size=child_page_size,
                read_chunk_page_size=read_chunk_page_size,
            )

    @pytest.mark.parametrize(
        ("read_text_cache_max_objects", "read_text_cache_ttl_seconds"),
        [(0, 21600), (32, 0)],
    )
    def test_init_rejects_non_positive_cache_settings(
        self,
        read_text_cache_max_objects: int,
        read_text_cache_ttl_seconds: int,
    ) -> None:
        with pytest.raises(ValueError, match="must be greater than 0"):
            OpenDMAToolSpec(
                endpoint="http://localhost:8080/opendma",
                username="ignored",
                password="ignored",
                repository_id="sample-repo",
                read_text_cache_max_objects=read_text_cache_max_objects,
                read_text_cache_ttl_seconds=read_text_cache_ttl_seconds,
            )

    def test_tool_error_matches_open_dma_tool_contract(self) -> None:
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )

        result = tool_spec._tool_error("opendma_read_text", ValueError("invalid document"))

        assert result == {
            "error": True,
            "tool": "opendma_read_text",
            "error_type": "ValueError",
            "message": "invalid document",
        }

    def test_tool_methods_return_input_error_for_missing_required_parameter(self) -> None:
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )

        result = tool_spec.opendma_get_metadata()

        assert result == {
            "error": True,
            "tool": "opendma_get_metadata",
            "error_type": "ToolInputError",
            "message": "Missing required string parameter(s): object_id.",
        }

    def test_tool_methods_return_input_error_for_unexpected_parameter(self) -> None:
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )

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

    def test_list_children_validates_include_options_before_repository_call(self) -> None:
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )

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

    def test_extract_metadata_matches_open_dma_tool_value_semantics(self) -> None:
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )
        created_at = datetime(2026, 8, 24, 12, 30, tzinfo=timezone.utc)
        obj = create_fake_document(
            [
                OdmaPropertyImpl(
                    OdmaQName("opendma", "Title"),
                    "Spec",
                    None,
                    OdmaType.STRING,
                    False,
                    False,
                ),
                OdmaPropertyImpl(
                    OdmaQName("opendma", "Content"),
                    None,
                    None,
                    OdmaType.CONTENT,
                    False,
                    False,
                ),
                OdmaPropertyImpl(
                    OdmaQName("opendma", "CreatedAt"),
                    created_at,
                    None,
                    OdmaType.DATETIME,
                    False,
                    False,
                ),
                OdmaPropertyImpl(
                    OdmaQName("opendma", "Repository"),
                    create_fake_folder(
                        [
                            OdmaPropertyImpl(
                                OdmaQName("opendma", "Id"),
                                OdmaId("sample-repo-object"),
                                None,
                                OdmaType.ID,
                                False,
                                False,
                            )
                        ]
                    ),
                    None,
                    OdmaType.REFERENCE,
                    False,
                    False,
                ),
                OdmaPropertyImpl(
                    OdmaQName("opendma", "ContainedIn"),
                    [create_fake_folder_a()],
                    None,
                    OdmaType.REFERENCE,
                    True,
                    False,
                ),
                OdmaPropertyImpl(
                    OdmaQName("opendma", "IdList"),
                    [OdmaId("id-1"), OdmaId("id-2")],
                    None,
                    OdmaType.ID,
                    True,
                    False,
                ),
                OdmaPropertyImpl(
                    OdmaQName("opendma", "Tags"),
                    ["alpha", "beta"],
                    None,
                    OdmaType.STRING,
                    True,
                    False,
                ),
            ]
        )

        metadata = tool_spec._extract_metadata(obj)

        assert metadata == {
            "opendma:Title": "Spec",
            "opendma:CreatedAt": "2026-08-24T12:30:00+00:00",
            "opendma:Repository": "sample-repo-object",
            "opendma:ContainedIn": ["folder-a"],
            "opendma:IdList": ["id-1", "id-2"],
            "opendma:Tags": ["alpha", "beta"],
        }

    def test_get_metadata_uses_metadata_result_model(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession(objects=[create_fake_doc_a()])
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_get_metadata("doc-a")

        assert session.closed
        assert result == {
            "object_id": "doc-a",
            "type_name": "fake:Document",
            "aspect_names": [],
            "name": "Hello, doc!",
            "metadata": {
                "opendma:Id": "doc-a",
                "opendma:Title": "Hello, doc!",
                "test:CustomProperty": "custom value",
            },
        }

    def test_function_tool_call_returns_input_error_instead_of_raising(self) -> None:
        tool_spec = OpenDMAToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )
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
            "message": "Unexpected parameter(s): unknown. Allowed parameters: object_id.",
        }


class TestSearchToolSpec:
    """Test cases for _SearchToolSpec public tool contract."""

    def test_search_tool_spec_builds_core_tools_plus_search(self) -> None:
        tool_spec = RecordingSearchToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )

        tools = tool_spec.to_tool_list()

        assert [tool.metadata.name for tool in tools] == [
            "opendma_get_metadata",
            "opendma_list_children",
            "opendma_read_text",
            "opendma_describe_class",
            "opendma_search",
        ]
        assert tools[-1].metadata.fn_schema is OpenDMASearchInput

    def test_search_uses_query_language_and_returns_items(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = RecordingSearchToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
            search_result_limit=7,
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(
            full_text="contract",
            in_folder="folder-a",
            include_subfolder_in_folder=True,
            included_metadata=["opendma:Title"],
        )

        assert session.query_language == "opendma:test"
        assert session.query == "contract|folder-a|True"
        assert session.closed
        assert result["has_more"] is False
        assert result["continuation_token"] is None
        assert result["items"] == [
            {
                "object_id": "doc-a",
                "type_name": "fake:Document",
                "aspect_names": [],
                "name": "Hello, doc!",
                "metadata": {"opendma:Title": "Hello, doc!"},
            },
            {
                "object_id": "folder-a",
                "type_name": "fake:Folder",
                "aspect_names": [],
                "name": "Hello, Folder!",
                "metadata": {},
            },
        ]

    def test_search_includes_all_metadata_by_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = RecordingSearchToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text="website design")

        assert result["items"][0]["metadata"] == {
            "opendma:Id": "doc-a",
            "opendma:Title": "Hello, doc!",
            "test:CustomProperty": "custom value",
        }

    def test_search_returns_error_payload_for_build_query_failure(self) -> None:
        class EmptySearchToolSpec(RecordingSearchToolSpec):
            def _build_search_query(
                self,
                full_text: str | None,
                in_folder: str | None,
                include_subfolder_in_folder: bool | None,
            ) -> str:
                _ = full_text, in_folder, include_subfolder_in_folder
                raise ValueError("Search requires at least one criterion")

        tool_spec = EmptySearchToolSpec(
            endpoint="http://localhost:8080/opendma",
            username="ignored",
            password="ignored",
            repository_id="sample-repo",
        )

        result = tool_spec.opendma_search(full_text=" ")

        assert result["error"] is True
        assert result["tool"] == "opendma_search"

    def test_search_result_limit_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="search_result_limit"):
            RecordingSearchToolSpec(
                endpoint="http://localhost:8080/opendma",
                username="ignored",
                password="ignored",
                repository_id="sample-repo",
                search_result_limit=0,
            )


class TestAlfrescoToolSpec:
    """Test cases for AlfrescoToolSpec public tool contract."""

    def test_search_uses_alfresco_query_language_and_returns_items(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = AlfrescoToolSpec(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text="website design")

        assert tool_spec.repository_id == "Alfresco"
        assert session.query_language == "alfresco:afts"
        assert session.query == 'TEXT:"website design"'
        assert session.closed
        assert result["items"][0]["object_id"] == "doc-a"

    def test_search_escapes_alfresco_phrases(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = AlfrescoToolSpec(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text='site "design"')

        assert "error" not in result
        assert session.query == 'TEXT:"site \\"design\\""'

    def test_search_converts_alfresco_node_folder_ids(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = AlfrescoToolSpec(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(
            in_folder="node:abc",
            include_subfolder_in_folder=True,
        )

        assert "error" not in result
        assert session.query == 'ANCESTOR:"workspace://SpacesStore/abc"'

    def test_search_returns_error_payload_for_empty_alfresco_search(self) -> None:
        tool_spec = AlfrescoToolSpec(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
        )

        result = tool_spec.opendma_search(full_text=" ")

        assert result["error"] is True
        assert result["tool"] == "opendma_search"

    def test_to_tool_list_includes_alfresco_list_sites(self) -> None:
        tool_spec = AlfrescoToolSpec(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
        )

        tools = tool_spec.to_tool_list()

        assert [tool.metadata.name for tool in tools] == [
            "opendma_get_metadata",
            "opendma_list_children",
            "opendma_read_text",
            "opendma_describe_class",
            "opendma_search",
            "alfresco_list_sites",
        ]

    def test_list_sites_returns_site_descriptions(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession(objects=[create_fake_site(), create_fake_doc_a()])
        tool_spec = AlfrescoToolSpec(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.alfresco_list_sites()

        assert session.query_language == "alfresco:afts"
        assert session.query == 'TYPE:"st:site"'
        assert session.closed
        assert result == [
            {
                "short_name": "swsdp",
                "title": "Sample: Web Site Design Project",
                "description": "This is a Sample Alfresco Team site.",
                "root_folder_id": "site-swsdp",
            }
        ]

    def test_list_sites_returns_input_error_for_unexpected_parameter(self) -> None:
        tool_spec = AlfrescoToolSpec(
            endpoint="http://localhost:7070/opendma/alf",
            username="admin",
            password="admin",
        )

        result = tool_spec.alfresco_list_sites(unexpected="value")

        assert result == {
            "error": True,
            "tool": "alfresco_list_sites",
            "error_type": "ToolInputError",
            "message": "Unexpected parameter(s): unexpected. Allowed parameters: none.",
        }


class TestFileNetP8ToolSpec:
    """Test cases for FileNetP8ToolSpec public tool contract."""

    def test_search_uses_filenet_query_language(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = FileNetP8ToolSpec(
            endpoint="http://localhost:8080/opendma/filenet",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text="foo bar")

        assert tool_spec.repository_id == "FileNetP8"
        assert session.query_language == "filenetp8:sql"
        assert session.query == (
            "SELECT d.This FROM Document d"
            " INNER JOIN ContentSearch cs ON d.This = cs.QueriedObject"
            " WHERE CONTAINS(d.*, 'foo OR bar')"
        )
        assert result["items"][0]["object_id"] == "doc-a"

    def test_search_accepts_filenet_special_characters(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = FileNetP8ToolSpec(
            endpoint="http://localhost:8080/opendma/filenet",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text="owner's name?")

        assert "error" not in result
        assert session.query == (
            "SELECT d.This FROM Document d"
            " INNER JOIN ContentSearch cs ON d.This = cs.QueriedObject"
            " WHERE CONTAINS(d.*, 'owner''s OR name\\?')"
        )

    def test_search_restricts_to_filenet_folder(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = FileNetP8ToolSpec(
            endpoint="http://localhost:8080/opendma/filenet",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(
            in_folder="objectstore:Folder:{123}",
            include_subfolder_in_folder=False,
        )

        assert "error" not in result
        assert session.query == "SELECT d.This FROM Document d WHERE d.This INFOLDER {123}"

    def test_search_returns_error_payload_for_invalid_filenet_folder_id(self) -> None:
        tool_spec = FileNetP8ToolSpec(
            endpoint="http://localhost:8080/opendma/filenet",
            username="admin",
            password="admin",
        )

        result = tool_spec.opendma_search(in_folder="bad-folder-id")

        assert result["error"] is True
        assert result["tool"] == "opendma_search"

    def test_search_returns_error_payload_for_empty_filenet_search(self) -> None:
        tool_spec = FileNetP8ToolSpec(
            endpoint="http://localhost:8080/opendma/filenet",
            username="admin",
            password="admin",
        )

        result = tool_spec.opendma_search(full_text="  \n\t  ")

        assert result["error"] is True
        assert result["tool"] == "opendma_search"


class TestDocumentumToolSpec:
    """Test cases for DocumentumToolSpec public tool contract."""

    def test_search_uses_documentum_query_language(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = DocumentumToolSpec(
            endpoint="http://localhost:8080/opendma/documentum",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text="foo bar")

        assert tool_spec.repository_id == "Documentum"
        assert session.query_language == "dctm:dql"
        assert session.query == "SELECT * FROM dm_document SEARCH DOCUMENT CONTAINS 'foo' OR 'bar'"
        assert result["items"][0]["object_id"] == "doc-a"

    def test_search_accepts_documentum_apostrophes(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = DocumentumToolSpec(
            endpoint="http://localhost:8080/opendma/documentum",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text="owner's name")

        assert "error" not in result
        assert session.query == (
            "SELECT * FROM dm_document SEARCH DOCUMENT CONTAINS 'owner''s' OR 'name'"
        )

    def test_search_restricts_to_documentum_folder(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = DocumentumToolSpec(
            endpoint="http://localhost:8080/opendma/documentum",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(
            in_folder="0b00000180000107",
            include_subfolder_in_folder=True,
        )

        assert "error" not in result
        assert session.query == (
            "SELECT * FROM dm_document WHERE FOLDER(ID('0b00000180000107'), DESCEND)"
        )

    def test_search_returns_error_payload_for_empty_documentum_search(self) -> None:
        tool_spec = DocumentumToolSpec(
            endpoint="http://localhost:8080/opendma/documentum",
            username="admin",
            password="admin",
        )

        result = tool_spec.opendma_search(full_text="  \n\t  ")

        assert result["error"] is True
        assert result["tool"] == "opendma_search"


class TestOnBaseToolSpec:
    """Test cases for OnBaseToolSpec public tool contract."""

    def test_search_uses_onbase_query_language(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = OnBaseToolSpec(
            endpoint="http://localhost:8080/opendma/onbase",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text="foo bar")

        assert tool_spec.repository_id == "OnBase"
        assert session.query_language == "onbase:DocumentQuery"
        assert session.query
        assert "<FullTextSearchString>foo OR bar</FullTextSearchString>" in session.query
        assert result["items"][0]["object_id"] == "doc-a"

    def test_search_accepts_onbase_xml_special_characters(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session = FakeOdmaSession()
        tool_spec = OnBaseToolSpec(
            endpoint="http://localhost:8080/opendma/onbase",
            username="admin",
            password="admin",
        )
        monkeypatch.setattr(tool_spec, "_create_session", lambda: session)

        result = tool_spec.opendma_search(full_text="<test foo bar")

        assert "error" not in result
        assert session.query is not None
        assert (
            "<FullTextSearchString>&lt;test OR foo OR bar</FullTextSearchString>" in session.query
        )

    def test_search_returns_error_payload_for_empty_onbase_search(self) -> None:
        tool_spec = OnBaseToolSpec(
            endpoint="http://localhost:8080/opendma/onbase",
            username="admin",
            password="admin",
        )

        result = tool_spec.opendma_search(full_text="  \n\t  ")

        assert result["error"] is True
        assert result["tool"] == "opendma_search"

    def test_search_returns_error_payload_for_onbase_folder_restriction(self) -> None:
        tool_spec = OnBaseToolSpec(
            endpoint="http://localhost:8080/opendma/onbase",
            username="admin",
            password="admin",
        )

        result = tool_spec.opendma_search(in_folder="folder-a")

        assert result["error"] is True
        assert result["tool"] == "opendma_search"

    def test_search_tool_schema_omits_folder_parameters(self) -> None:
        tool_spec = OnBaseToolSpec(
            endpoint="http://localhost:8080/opendma/onbase",
            username="admin",
            password="admin",
        )
        tools_by_name = {tool.metadata.name: tool for tool in tool_spec.to_tool_list()}
        search_schema = tools_by_name["opendma_search"].metadata.get_parameters_dict()

        assert "full_text" in search_schema["properties"]
        assert "included_metadata" in search_schema["properties"]
        assert "in_folder" not in search_schema["properties"]
        assert "include_subfolder_in_folder" not in search_schema["properties"]
