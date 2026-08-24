"""OpenDMA tool specs for LlamaIndex."""

from __future__ import annotations

import base64
import fnmatch
import json
import re
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from time import monotonic
from typing import Any

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from llama_index.core.tools import FunctionTool, ToolMetadata
from llama_index.core.tools.tool_spec.base import SPEC_FUNCTION_TYPE, BaseToolSpec
from llama_index.readers.opendma import OpenDMAReader
from pydantic import BaseModel, Field, model_validator

import opendma.remote
from opendma.api import OdmaDocument, OdmaFolder, OdmaId, OdmaQName, OdmaType

ScalarValue = str | int | float | bool | None
MetadataValue = ScalarValue | list[ScalarValue]


class PropertyDescription(BaseModel):
    """Description of an OpenDMA class or aspect property."""

    name: str
    type: str
    description: str
    required: bool
    multi_value: bool
    queryable: bool | None = None
    possible_values: list[str] | None = None


class OpenDMAObjectItem(BaseModel):
    """Compact OpenDMA object representation returned by list/search tools."""

    object_id: str
    type_name: str
    aspect_names: list[str]
    name: str
    metadata: dict[str, MetadataValue]


class OpenDMAListResult(BaseModel):
    """Paged list/search result."""

    items: list[OpenDMAObjectItem]
    has_more: bool
    continuation_token: str | None = None


class OpenDMAReadChunk(BaseModel):
    """Text chunk returned by opendma_read_text."""

    text: str
    metadata: dict[str, MetadataValue]
    chunk_index: int


class OpenDMAReadTextResult(BaseModel):
    """Paged text extraction result."""

    chunks: list[OpenDMAReadChunk]
    has_more: bool
    chunk_continuation_token: str | None = None


class OpenDMAGetMetadataInput(BaseModel):
    """Input for opendma_get_metadata."""

    object_id: str = Field(description="OpenDMA object ID.")


class OpenDMAListChildrenInput(BaseModel):
    """Input for opendma_list_children."""

    object_id: str = Field(description="OpenDMA folder object ID.")
    include_folders: bool = Field(default=True, description="Include child folders.")
    include_files: bool = Field(default=True, description="Include child documents.")
    name_pattern: str | None = Field(
        default=None,
        description="Optional glob-style name pattern applied to child names.",
    )
    continuation_token: str | None = Field(
        default=None,
        description="Opaque continuation token returned by a previous call.",
    )
    included_metadata: list[str] | None = Field(
        default=None,
        description="Qualified OpenDMA property names to include for each item.",
    )

    @model_validator(mode="after")
    def _validate_includes(self) -> OpenDMAListChildrenInput:
        if not self.include_folders and not self.include_files:
            raise ValueError("include_folders and include_files cannot both be false")
        return self


class OpenDMASearchInput(BaseModel):
    """Input for opendma_search."""

    full_text: str | None = Field(default=None, description="Optional full-text query.")
    in_folder: str | None = Field(default=None, description="Optional folder restriction.")
    include_subfolder_in_folder: bool | None = Field(
        default=None,
        description="Whether to include subfolders when in_folder is set.",
    )
    included_metadata: list[str] | None = Field(
        default=None,
        description="Qualified OpenDMA property names to include for each item.",
    )


class OpenDMAReadTextInput(BaseModel):
    """Input for opendma_read_text."""

    object_id: str = Field(description="OpenDMA document object ID.")
    chunk_continuation_token: str | None = Field(
        default=None,
        description="Opaque continuation token returned by a previous call.",
    )


class OpenDMADescribeClassInput(BaseModel):
    """Input for opendma_describe_class."""

    type_or_aspect_name: str = Field(description="Qualified OpenDMA type or aspect name.")


@dataclass
class _ReadTextCacheEntry:
    created_at: float
    documents: list[Document]


class OpenDMAToolSpec(BaseToolSpec):
    """Create read-only LlamaIndex tools for a fixed OpenDMA repository."""

    spec_functions: list[SPEC_FUNCTION_TYPE] = []

    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        repository_id: str,
        file_extractor_per_mimetype: dict[str, BaseReader] | None = None,
        child_page_size: int = 50,
        read_chunk_page_size: int = 3,
        read_text_cache_enabled: bool = True,
        read_text_cache_max_objects: int = 32,
        read_text_cache_ttl_seconds: int | None = 21600,
    ) -> None:
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.repository_id = repository_id
        self.file_extractor_per_mimetype = file_extractor_per_mimetype
        self.child_page_size = child_page_size
        self.read_chunk_page_size = read_chunk_page_size
        self.read_text_cache_enabled = read_text_cache_enabled
        self.read_text_cache_max_objects = read_text_cache_max_objects
        self.read_text_cache_ttl_seconds = read_text_cache_ttl_seconds
        self._read_text_cache: OrderedDict[str, _ReadTextCacheEntry] = OrderedDict()

        if self.child_page_size <= 0:
            raise ValueError("child_page_size must be greater than 0")
        if self.read_chunk_page_size <= 0:
            raise ValueError("read_chunk_page_size must be greater than 0")
        if self.read_text_cache_max_objects <= 0:
            raise ValueError("read_text_cache_max_objects must be greater than 0")
        if self.read_text_cache_ttl_seconds is not None and self.read_text_cache_ttl_seconds <= 0:
            raise ValueError("read_text_cache_ttl_seconds must be greater than 0")

    def to_tool_list(
        self,
        spec_functions: list[SPEC_FUNCTION_TYPE] | None = None,
        func_to_metadata_mapping: dict[str, ToolMetadata] | None = None,
    ) -> list[FunctionTool]:
        """Return the OpenDMA tools exposed by this tool spec."""
        if spec_functions is not None or func_to_metadata_mapping is not None:
            return super().to_tool_list(spec_functions, func_to_metadata_mapping)

        return [
            self._function_tool(
                name="opendma_get_metadata",
                description="Get class, aspect, and scalar metadata for one OpenDMA object.",
                fn=self.opendma_get_metadata,
                fn_schema=OpenDMAGetMetadataInput,
            ),
            self._function_tool(
                name="opendma_list_children",
                description=(
                    "List child folders and documents of an OpenDMA folder. "
                    "Use continuation_token when has_more is true."
                ),
                fn=self.opendma_list_children,
                fn_schema=OpenDMAListChildrenInput,
            ),
            self._function_tool(
                name="opendma_read_text",
                description=(
                    "Read transformed text chunks from one OpenDMA document. "
                    "Use chunk_continuation_token when has_more is true."
                ),
                fn=self.opendma_read_text,
                fn_schema=OpenDMAReadTextInput,
            ),
            self._function_tool(
                name="opendma_describe_class",
                description="Describe an OpenDMA type or aspect and its properties.",
                fn=self.opendma_describe_class,
                fn_schema=OpenDMADescribeClassInput,
            ),
        ]

    def _function_tool(
        self,
        name: str,
        description: str,
        fn: Any,
        fn_schema: type[BaseModel],
    ) -> FunctionTool:
        return FunctionTool.from_defaults(
            fn=fn,
            tool_metadata=ToolMetadata(
                name=name,
                description=description,
                fn_schema=fn_schema,
            ),
        )

    def opendma_get_metadata(
        self,
        object_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Implementation for opendma_get_metadata."""
        try:
            input_error = self._validate_tool_input(
                tool_name="opendma_get_metadata",
                provided=kwargs,
                required={"object_id": object_id},
                allowed={"object_id"},
            )
            if input_error is not None:
                return input_error

            assert object_id is not None
            session = self._create_session()
            try:
                obj = self._get_object(session, object_id)
                metadata = self._extract_metadata(obj)
                return {
                    "type_name": str(obj.get_odma_class().get_qname()),
                    "aspect_names": [str(aspect.get_qname()) for aspect in obj.get_aspects()],
                    "metadata": metadata,
                }
            finally:
                session.close()
        except Exception as exc:
            return self._tool_error("opendma_get_metadata", exc)

    def opendma_list_children(
        self,
        object_id: str | None = None,
        include_folders: bool = True,
        include_files: bool = True,
        name_pattern: str | None = None,
        continuation_token: str | None = None,
        included_metadata: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Implementation for opendma_list_children."""
        try:
            input_error = self._validate_tool_input(
                tool_name="opendma_list_children",
                provided=kwargs,
                required={"object_id": object_id},
                allowed={
                    "object_id",
                    "include_folders",
                    "include_files",
                    "name_pattern",
                    "continuation_token",
                    "included_metadata",
                },
            )
            if input_error is not None:
                return input_error

            if not include_folders and not include_files:
                raise ValueError("include_folders and include_files cannot both be false")

            assert object_id is not None
            session = self._create_session()
            try:
                folder = self._get_object(session, object_id)
                if not isinstance(folder, OdmaFolder):
                    raise ValueError(f"Object {object_id} is not an OpenDMA folder")

                children: list[Any] = []
                if include_folders:
                    children.extend(folder.get_sub_folders())
                if include_files:
                    children.extend(folder.get_containees())

                if name_pattern:
                    children = [
                        child
                        for child in children
                        if fnmatch.fnmatchcase(self._object_name(child), name_pattern)
                    ]

                children = [
                    child
                    for child in children
                    if (include_folders and isinstance(child, OdmaFolder))
                    or (include_files and isinstance(child, OdmaDocument))
                ]

                offset = self._decode_offset_token(continuation_token)
                page = children[offset : offset + self.child_page_size]
                next_offset = offset + len(page)
                has_more = next_offset < len(children)

                result = OpenDMAListResult(
                    items=[
                        self._object_item(child, included_metadata=included_metadata)
                        for child in page
                    ],
                    has_more=has_more,
                    continuation_token=self._encode_offset_token(next_offset) if has_more else None,
                )
                return result.model_dump()
            finally:
                session.close()
        except Exception as exc:
            return self._tool_error("opendma_list_children", exc)

    def opendma_read_text(
        self,
        object_id: str | None = None,
        chunk_continuation_token: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Implementation for opendma_read_text."""
        try:
            input_error = self._validate_tool_input(
                tool_name="opendma_read_text",
                provided=kwargs,
                required={"object_id": object_id},
                allowed={"object_id", "chunk_continuation_token"},
            )
            if input_error is not None:
                return input_error

            assert object_id is not None
            documents = self._read_text_documents(object_id)

            offset = self._decode_offset_token(chunk_continuation_token)
            page = documents[offset : offset + self.read_chunk_page_size]
            next_offset = offset + len(page)
            has_more = next_offset < len(documents)

            result = OpenDMAReadTextResult(
                chunks=[
                    OpenDMAReadChunk(
                        text=document.text,
                        metadata=self._filter_metadata(document.metadata, None),
                        chunk_index=offset + index,
                    )
                    for index, document in enumerate(page)
                ],
                has_more=has_more,
                chunk_continuation_token=self._encode_offset_token(next_offset)
                if has_more
                else None,
            )
            return result.model_dump()
        except Exception as exc:
            return self._tool_error("opendma_read_text", exc)

    def opendma_describe_class(
        self,
        type_or_aspect_name: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Implementation for opendma_describe_class."""
        try:
            input_error = self._validate_tool_input(
                tool_name="opendma_describe_class",
                provided=kwargs,
                required={"type_or_aspect_name": type_or_aspect_name},
                allowed={"type_or_aspect_name"},
            )
            if input_error is not None:
                return input_error

            assert type_or_aspect_name is not None
            session = self._create_session()
            try:
                repository = session.get_repository(self._repository_id())
                odma_class = self._find_class(repository, type_or_aspect_name)
                if odma_class is None:
                    raise ValueError(f"OpenDMA type or aspect not found: {type_or_aspect_name}")

                declared = list(odma_class.get_declared_properties())
                declared_names = {str(prop.get_qname()) for prop in declared}
                inherited = [
                    prop
                    for prop in odma_class.get_properties()
                    if str(prop.get_qname()) not in declared_names
                ]
                parent = odma_class.get_super_class()

                return {
                    "name": str(odma_class.get_qname()),
                    "kind": "aspect" if odma_class.get_aspect() else "type",
                    "parent": str(parent.get_qname()) if parent is not None else None,
                    "inherited_properties": [
                        self._property_description(prop).model_dump() for prop in inherited
                    ],
                    "declared_properties": [
                        self._property_description(prop).model_dump() for prop in declared
                    ],
                }
            finally:
                session.close()
        except Exception as exc:
            return self._tool_error("opendma_describe_class", exc)

    def _read_text_documents(self, object_id: str) -> list[Document]:
        if not self.read_text_cache_enabled:
            return self._load_read_text_documents(object_id)

        cache_entry = self._read_text_cache.get(object_id)
        if cache_entry is not None:
            if not self._read_text_cache_entry_expired(cache_entry):
                self._read_text_cache.move_to_end(object_id)
                return cache_entry.documents
            del self._read_text_cache[object_id]

        documents = self._load_read_text_documents(object_id)
        self._read_text_cache[object_id] = _ReadTextCacheEntry(
            created_at=monotonic(),
            documents=documents,
        )
        self._read_text_cache.move_to_end(object_id)

        while len(self._read_text_cache) > self.read_text_cache_max_objects:
            self._read_text_cache.popitem(last=False)

        return documents

    def _load_read_text_documents(self, object_id: str) -> list[Document]:
        reader = OpenDMAReader(
            endpoint=self.endpoint,
            username=self.username,
            password=self.password,
            repository_id=self.repository_id,
            document_ids=[object_id],
            file_extractor_per_mimetype=self.file_extractor_per_mimetype,
            raise_on_error=True,
        )
        documents = reader.load_data()
        if not documents:
            raise ValueError(
                f"No readable text content was returned for document {object_id}. "
                "The document may not exist, may have no primary content, may have "
                "empty content, or may use content that no configured reader can convert."
            )
        return documents

    def _read_text_cache_entry_expired(self, entry: _ReadTextCacheEntry) -> bool:
        if self.read_text_cache_ttl_seconds is None:
            return False
        return monotonic() - entry.created_at > self.read_text_cache_ttl_seconds

    def _tool_error(self, tool_name: str, exc: Exception) -> dict[str, Any]:
        message = str(exc) or exc.__class__.__name__
        return {
            "error": True,
            "tool": tool_name,
            "error_type": exc.__class__.__name__,
            "message": message,
        }

    def _tool_input_error(self, tool_name: str, message: str) -> dict[str, Any]:
        return {
            "error": True,
            "tool": tool_name,
            "error_type": "ToolInputError",
            "message": message,
        }

    def _validate_tool_input(
        self,
        tool_name: str,
        provided: dict[str, Any],
        required: dict[str, Any],
        allowed: set[str],
    ) -> dict[str, Any] | None:
        unexpected = sorted(set(provided) - allowed)
        if unexpected:
            allowed_message = ", ".join(sorted(allowed)) if allowed else "none"
            return self._tool_input_error(
                tool_name,
                "Unexpected parameter(s): "
                + ", ".join(unexpected)
                + ". Allowed parameters: "
                + allowed_message
                + ".",
            )

        missing = [
            name
            for name, value in required.items()
            if value is None or not isinstance(value, str) or not value.strip()
        ]
        if missing:
            return self._tool_input_error(
                tool_name,
                "Missing required string parameter(s): " + ", ".join(missing) + ".",
            )

        return None

    def _create_session(self) -> Any:
        return opendma.remote.connect(
            endpoint=self.endpoint,
            username=self.username,
            password=self.password,
        )

    def _repository_id(self) -> OdmaId:
        return OdmaId(self.repository_id)

    def _get_object(self, session: Any, object_id: str) -> Any:
        return session.get_object(self._repository_id(), OdmaId(object_id), None)

    def _run_search(
        self,
        query_language: str,
        query: str,
        included_metadata: list[str] | None,
        search_result_limit: int,
    ) -> dict[str, Any]:
        session = self._create_session()
        try:
            search_result = session.search(
                self._repository_id(),
                OdmaQName.from_string(query_language),
                query,
            )

            items = []
            for obj in search_result.get_objects():
                items.append(self._object_item(obj, included_metadata=included_metadata))
                if len(items) >= search_result_limit:
                    break

            return OpenDMAListResult(
                items=items,
                has_more=False,
                continuation_token=None,
            ).model_dump()
        finally:
            session.close()

    def _extract_metadata(self, obj: Any) -> dict[str, MetadataValue]:
        metadata: dict[str, MetadataValue] = {}
        for property_info in obj.get_odma_class().get_properties():
            property_name = property_info.get_qname()
            prop = obj.get_property(property_name)
            value = self._property_value(prop)
            if value is not None:
                metadata[str(property_name)] = value
        return metadata

    def _property_value(self, prop: Any) -> MetadataValue:
        prop_type = prop.get_type()
        if prop_type == OdmaType.CONTENT:
            return None

        if prop.is_multi_value():
            raw_values = self._multi_property_values(prop, prop_type)
            return [self._scalar_value(value) for value in raw_values]

        if prop_type == OdmaType.REFERENCE:
            reference_id = prop.get_reference_id()
            return str(reference_id) if reference_id is not None else None

        return self._scalar_value(prop.get_value())

    def _multi_property_values(self, prop: Any, prop_type: Any) -> list[Any]:
        if prop_type == OdmaType.ID:
            return list(prop.get_id_list())
        if prop_type == OdmaType.GUID:
            return list(prop.get_guid_list())
        if prop_type == OdmaType.REFERENCE:
            return [
                ref_obj.get_id()
                for ref_obj in prop.get_reference_iterable()
                if ref_obj.get_id() is not None
            ]
        value = prop.get_value()
        if isinstance(value, list):
            return value
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return list(value)
        return []

    def _scalar_value(self, value: Any) -> ScalarValue:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)

    def _object_item(
        self,
        obj: Any,
        included_metadata: list[str] | None,
    ) -> OpenDMAObjectItem:
        return OpenDMAObjectItem(
            object_id=str(obj.get_id()),
            type_name=str(obj.get_odma_class().get_qname()),
            aspect_names=[str(aspect.get_qname()) for aspect in obj.get_aspects()],
            name=self._object_name(obj),
            metadata=self._filter_metadata(self._extract_metadata(obj), included_metadata),
        )

    def _object_name(self, obj: Any) -> str:
        metadata = self._extract_metadata(obj)
        for key in ("opendma:Name", "opendma:Title"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                return value
        return str(obj.get_id())

    def _filter_metadata(
        self,
        metadata: dict[str, Any],
        included_metadata: list[str] | None,
    ) -> dict[str, MetadataValue]:
        if included_metadata is None:
            return {key: self._metadata_value(value) for key, value in metadata.items()}
        return {
            key: self._metadata_value(value)
            for key, value in metadata.items()
            if key in included_metadata
        }

    def _metadata_value(self, value: Any) -> MetadataValue:
        if isinstance(value, list):
            return [self._scalar_value(item) for item in value]
        return self._scalar_value(value)

    def _property_description(self, property_info: Any) -> PropertyDescription:
        choices = [
            choice.get_display_name()
            for choice in property_info.get_choices()
            if choice.get_display_name()
        ]
        return PropertyDescription(
            name=str(property_info.get_qname()),
            type=str(property_info.get_data_type()),
            description=property_info.get_display_name(),
            required=property_info.get_required(),
            multi_value=property_info.get_multi_value(),
            queryable=None,
            possible_values=choices or None,
        )

    def _find_class(self, repository: Any, qname: str) -> Any | None:
        roots = [repository.get_root_class(), *list(repository.get_root_aspects())]
        for root in roots:
            found = self._find_class_in_tree(root, qname)
            if found is not None:
                return found
        return None

    def _find_class_in_tree(self, odma_class: Any, qname: str) -> Any | None:
        if str(odma_class.get_qname()) == qname:
            return odma_class
        for aspect in odma_class.get_aspects():
            if str(aspect.get_qname()) == qname:
                return aspect
        for included_aspect in odma_class.get_included_aspects():
            if str(included_aspect.get_qname()) == qname:
                return included_aspect
        for sub_class in odma_class.get_sub_classes():
            found = self._find_class_in_tree(sub_class, qname)
            if found is not None:
                return found
        return None

    def _encode_offset_token(self, offset: int) -> str:
        payload = json.dumps({"offset": offset}, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii")

    def _decode_offset_token(self, token: str | None) -> int:
        if not token:
            return 0
        try:
            payload = json.loads(base64.urlsafe_b64decode(token.encode("ascii")))
            offset = payload.get("offset")
        except Exception as exc:
            raise ValueError("Invalid continuation token") from exc
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("Invalid continuation token")
        return offset


class _SearchToolSpec(OpenDMAToolSpec):
    query_language: str

    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        repository_id: str,
        file_extractor_per_mimetype: dict[str, BaseReader] | None = None,
        child_page_size: int = 50,
        read_chunk_page_size: int = 3,
        search_result_limit: int = 20,
        read_text_cache_enabled: bool = True,
        read_text_cache_max_objects: int = 32,
        read_text_cache_ttl_seconds: int | None = 21600,
    ) -> None:
        super().__init__(
            endpoint=endpoint,
            username=username,
            password=password,
            repository_id=repository_id,
            file_extractor_per_mimetype=file_extractor_per_mimetype,
            child_page_size=child_page_size,
            read_chunk_page_size=read_chunk_page_size,
            read_text_cache_enabled=read_text_cache_enabled,
            read_text_cache_max_objects=read_text_cache_max_objects,
            read_text_cache_ttl_seconds=read_text_cache_ttl_seconds,
        )
        self.search_result_limit = search_result_limit
        if self.search_result_limit <= 0:
            raise ValueError("search_result_limit must be greater than 0")

    def to_tool_list(
        self,
        spec_functions: list[SPEC_FUNCTION_TYPE] | None = None,
        func_to_metadata_mapping: dict[str, ToolMetadata] | None = None,
    ) -> list[FunctionTool]:
        """Return OpenDMA tools plus a platform-specific search tool."""
        if spec_functions is not None or func_to_metadata_mapping is not None:
            return super().to_tool_list(spec_functions, func_to_metadata_mapping)

        return [
            *super().to_tool_list(),
            self._search_tool(),
        ]

    def opendma_search(
        self,
        full_text: str | None = None,
        in_folder: str | None = None,
        include_subfolder_in_folder: bool | None = None,
        included_metadata: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Implementation for opendma_search using a platform query language."""
        try:
            input_error = self._validate_tool_input(
                tool_name="opendma_search",
                provided=kwargs,
                required={},
                allowed={
                    "full_text",
                    "in_folder",
                    "include_subfolder_in_folder",
                    "included_metadata",
                },
            )
            if input_error is not None:
                return input_error

            query = self._build_search_query(
                full_text=full_text,
                in_folder=in_folder,
                include_subfolder_in_folder=include_subfolder_in_folder,
            )
            return self._run_search(
                query_language=self.query_language,
                query=query,
                included_metadata=included_metadata,
                search_result_limit=self.search_result_limit,
            )
        except Exception as exc:
            return self._tool_error("opendma_search", exc)

    def _search_tool(self) -> FunctionTool:
        return self._function_tool(
            name="opendma_search",
            description=self._search_tool_description(),
            fn=self.opendma_search,
            fn_schema=self._search_tool_args_schema(),
        )

    def _search_tool_description(self) -> str:
        return (
            "Search documents via OpenDMA using full text. "
            "Use in_folder to restrict the search to a folder."
        )

    def _search_tool_args_schema(self) -> type[BaseModel]:
        return OpenDMASearchInput

    def _build_search_query(
        self,
        full_text: str | None,
        in_folder: str | None,
        include_subfolder_in_folder: bool | None,
    ) -> str:
        raise NotImplementedError

    def _split_words(self, full_text: str | None) -> list[str]:
        if full_text is None:
            return []
        return re.sub(r"\s+", " ", full_text).strip().split()
