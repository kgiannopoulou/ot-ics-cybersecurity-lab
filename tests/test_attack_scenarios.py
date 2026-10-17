"""Red/blue validation that runs in CI without Docker.

Each attack scenario is executed against a real soft-PLC subprocess (the same
simulator/water_tank_plc.py the Docker lab runs), and the in-controller
defences are asserted: reads succeed (the exposure the monitoring exists for),
but the input-validation and safety-interlock safeguards contain the writes.

The network-layer mitigation (the PLC host allow-list) and the Suricata
detections are validated against the live stack by tools/validate.py; this
file proves the controller-side half of "attack succeeds before mitigation,
is contained after" on every push.
"""

import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from attack import scenarios  # noqa: E402
from attack.scenarios import Probe  # noqa: E402


def _free_port() -> int:
    with closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def plc():
    """A soft-PLC subprocess with a fast scan, torn down after the module."""
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "simulator" / "water_tank_plc.py"),
         "--port", str(port), "--period", "0.2"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for the listener.
    for _ in range(50):
        with closing(socket.socket()) as s:
            s.settimeout(0.2)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.2)
    else:
        proc.terminate()
        pytest.fail("soft-PLC did not start")
    yield ("127.0.0.1", port)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def run(plc, name):
    with Probe(plc[0], plc[1]) as p:
        return scenarios.SCENARIOS[name](p)


def test_recon_reads_the_full_process_state(plc):
    """T0861: reconnaissance always succeeds on Modbus — the reason the lab
    relies on segmentation + monitoring, not on the protocol."""
    r = run(plc, "recon")
    assert r.objective_achieved
    assert r.evidence["holding_registers"][scenarios.LOW_SP] == 300  # low setpoint, 30.0 %


def test_setpoint_tamper_is_reset_by_input_validation(plc):
    """T0836 contained: SR 3.5 input validation resets an out-of-range setpoint."""
    r = run(plc, "setpoint")
    assert not r.objective_achieved
    assert r.evidence["readback"][0] == 800  # back to the 80.0 % default


def test_overflow_is_contained_by_the_safety_interlock(plc):
    """T0831/T0880 contained: even with the drain shut, setpoint raised and
    the pump forced on, the level >= 95 % interlock forces the pump off."""
    r = run(plc, "overflow")
    assert not r.objective_achieved, r.detail
    assert r.evidence["peak_level_pct"] <= 98  # overshoots 95 % by at most one scan


def test_unauthorised_writes_are_accepted_without_a_host_control(plc):
    """F-01 / F-06: with no allow-list the PLC serves writes from any client.
    This is the vulnerability the network allow-list (plc_allowlist.sh) and
    Suricata SIDs 9000003/5/13 address; proven here so the 'before' state is
    real, not assumed."""
    pump = run(plc, "pump")
    mode = run(plc, "mode")
    # At least one PLC-owned write holds (pump coil, or the mode flip).
    assert pump.objective_achieved or mode.objective_achieved


def test_every_scenario_reports_mitre_and_a_decision(plc):
    for name in scenarios.SCENARIOS:
        if name == "sweep":
            continue  # needs the subnet; covered against the live stack
        r = run(plc, name)
        assert r.scenario == name
        assert isinstance(r.objective_achieved, bool)
        assert r.mitre, name
