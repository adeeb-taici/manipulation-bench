"""Tests for ConsoleBridge."""
import pytest

from manipulation_bench.bridges.console import ConsoleBridge
from manipulation_bench.network import Channel, ChannelType


@pytest.fixture
def bridge():
    return ConsoleBridge(interactive=False)


@pytest.fixture
def channels():
    return {
        "general": Channel(
            id="general", name="#general",
            channel_type=ChannelType.PUBLIC, members={"node_0", "node_1"},
        )
    }


@pytest.mark.asyncio
async def test_setup_teardown(bridge, channels, capsys):
    await bridge.setup(channels)
    captured = capsys.readouterr()
    assert "Simulation started" in captured.out

    await bridge.teardown()
    captured = capsys.readouterr()
    assert "Simulation ended" in captured.out


@pytest.mark.asyncio
async def test_post_message(bridge, channels, capsys):
    await bridge.setup(channels)
    capsys.readouterr()

    await bridge.post_message("general", "Alice", "hello world", 0)
    captured = capsys.readouterr()
    assert "Alice" in captured.out
    assert "hello world" in captured.out


@pytest.mark.asyncio
async def test_collect_human_messages_non_interactive(bridge, channels):
    await bridge.setup(channels)
    msgs = await bridge.collect_human_messages(0, 10.0)
    assert msgs == []


@pytest.mark.asyncio
async def test_mark_round(bridge, channels, capsys):
    await bridge.setup(channels)
    capsys.readouterr()

    await bridge.mark_round(0)
    captured = capsys.readouterr()
    assert "Round 0" in captured.out
