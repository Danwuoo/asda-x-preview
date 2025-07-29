import asyncio

import pytest

from src.inference.feedback_router import (
    FeedbackEvent,
    FeedbackRouter,
    FeedbackType,
)


@pytest.mark.asyncio
async def test_route_event_calls_registered_handler():
    router = FeedbackRouter()
    called = []

    async def handler(event: FeedbackEvent) -> None:
        called.append(event)

    router.register_handler(FeedbackType.CIT_FAIL, handler)
    event = FeedbackEvent(
        event_type=FeedbackType.CIT_FAIL,
        task_id="t1",
        trace_id="x1",
        source_module="test",
    )
    await router.route_event(event)
    assert called and called[0] == event


@pytest.mark.asyncio
async def test_unregistered_event_has_no_effect():
    router = FeedbackRouter()
    called = False

    def handler(event: FeedbackEvent) -> None:  # sync handler
        nonlocal called
        called = True

    router.register_handler(FeedbackType.DRIFT_DETECTED, handler)
    event = FeedbackEvent(
        event_type=FeedbackType.CIT_FAIL,
        task_id="t1",
        trace_id="x1",
        source_module="test",
    )
    await router.route_event(event)
    assert not called
