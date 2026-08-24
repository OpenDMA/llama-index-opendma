"""OpenDMA tool specs for LlamaIndex."""

from llama_index.core.tools.tool_spec.base import SPEC_FUNCTION_TYPE, BaseToolSpec


class OpenDMAToolSpec(BaseToolSpec):
    """No-op OpenDMA tool spec."""

    spec_functions: list[SPEC_FUNCTION_TYPE] = []
