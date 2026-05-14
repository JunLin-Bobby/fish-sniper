"""POC: LangGraph 0.6.x accepts async nodes and ``ainvoke`` (async strategy pipeline spec §5)."""

from __future__ import annotations

import asyncio
from typing import Any, TypedDict

import pytest
from langgraph.graph import END, StateGraph


class _PocState(TypedDict, total=False):
    step: str
    counter: int


async def _node_sleep_increment(_state: _PocState) -> dict[str, Any]:
    await asyncio.sleep(0)
    return {"step": "after_sleep", "counter": 1}


async def _node_merge(_state: _PocState) -> dict[str, Any]:
    return {"step": "done"}


@pytest.mark.asyncio
async def test_langgraph_async_ainvoke_minimal_graph_merges_state() -> None:
    graph_builder = StateGraph(_PocState)
    graph_builder.add_node("sleep_inc", _node_sleep_increment)
    graph_builder.add_node("merge", _node_merge)
    graph_builder.set_entry_point("sleep_inc")
    graph_builder.add_edge("sleep_inc", "merge")
    graph_builder.add_edge("merge", END)
    compiled = graph_builder.compile()

    final_state = await compiled.ainvoke({})

    assert final_state["step"] == "done"
    assert final_state["counter"] == 1
