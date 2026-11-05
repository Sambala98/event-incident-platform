import pytest
from pydantic import ValidationError

from schemas import DeviceCreate


def test_device_defaults_and_name_trimming():
    device = DeviceCreate(name="  Router A  ")

    assert device.name == "Router A"
    assert device.heartbeat_interval_seconds == 30


@pytest.mark.parametrize("interval", [5, 3600])
def test_device_accepts_interval_boundaries(interval):
    device = DeviceCreate(
        name="Router A",
        heartbeat_interval_seconds=interval,
    )

    assert device.heartbeat_interval_seconds == interval


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {"name": "A" * 101},
        {"name": "Router A", "heartbeat_interval_seconds": 4},
        {"name": "Router A", "heartbeat_interval_seconds": 3601},
        {"name": "Router A", "heartbeat_interval_seconds": "30"},
        {"name": "Router A", "heartbeat_interval_seconds": True},
        {"name": "Router A", "unexpected_field": "value"},
        {},
    ],
)
def test_device_rejects_invalid_input(payload):
    with pytest.raises(ValidationError):
        DeviceCreate(**payload)