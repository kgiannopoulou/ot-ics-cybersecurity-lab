"""Unit tests for the soft-PLC scan cycle. Run: python -m pytest tests/"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "simulator"))

import water_tank_plc as plc  # noqa: E402


def make(level, pump=0, valve=1, auto=1, manual=0, low=300, high=800):
    ctx = plc.build_context()
    dev = ctx[0]
    dev.setValues(plc.FC_HR, plc.LEVEL, [level, low, high])
    dev.setValues(plc.FC_COILS, plc.PUMP, [pump, valve, auto, manual])
    return ctx, dev


def pump(dev):
    return dev.getValues(plc.FC_COILS, plc.PUMP, 1)[0]


def hr(dev, addr):
    return dev.getValues(plc.FC_HR, addr, 1)[0]


def test_pump_starts_below_low_setpoint():
    ctx, dev = make(level=250)
    plc.scan(ctx)
    assert pump(dev)


def test_pump_stops_above_high_setpoint():
    ctx, dev = make(level=850, pump=1)
    plc.scan(ctx)
    assert not pump(dev)


def test_hysteresis_keeps_state_between_setpoints():
    ctx, dev = make(level=500, pump=1)
    plc.scan(ctx)
    assert pump(dev)
    ctx, dev = make(level=500, pump=0)
    plc.scan(ctx)
    assert not pump(dev)


def test_interlock_overrides_manual_mode():
    ctx, dev = make(level=960, valve=0, auto=0, manual=1)
    plc.scan(ctx)
    assert not pump(dev)
    assert hr(dev, plc.ALARMS) & 1  # HIGH-HIGH


def test_out_of_range_setpoints_are_reset():
    ctx, dev = make(level=500, low=0, high=1000)
    plc.scan(ctx)
    assert hr(dev, plc.LOW_SP) == 300
    assert hr(dev, plc.HIGH_SP) == 800


def test_low_low_alarm():
    ctx, dev = make(level=20, valve=1, auto=0, manual=0)
    plc.scan(ctx)
    assert hr(dev, plc.ALARMS) & 2


def test_level_is_clamped():
    ctx, dev = make(level=0, valve=1, auto=0, manual=0)
    for _ in range(5):
        plc.scan(ctx)
    assert hr(dev, plc.LEVEL) == 0
