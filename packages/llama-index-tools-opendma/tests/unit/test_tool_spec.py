from llama_index.tools.opendma import OpenDMAToolSpec


def test_open_dma_tool_spec_is_empty() -> None:
    tool_spec = OpenDMAToolSpec()

    assert tool_spec.to_tool_list() == []
