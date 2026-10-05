"""
Water tank process simulator + soft PLC (Modbus/TCP server).

Stands in for OpenPLC + a physical process when running the lab in Docker.
The control logic mirrors plc/water-tank-program/water_tank.st exactly.

Modbus map (device id 1, zero-based addresses)
------------------------------------------------
Coils
  0  pump_running        (PLC output, read-only by convention)
  1  valve_open          (outlet valve, operator-controlled from HMI)
  2  auto_mode           (1 = PLC controls the pump, 0 = manual)
  3  manual_pump_cmd     (used only when auto_mode = 0)
Holding registers
  0  tank_level          (0-1000 = 0.0-100.0 %)
  1  low_setpoint        (default 300 = 30.0 %)
  2  high_setpoint       (default 800 = 80.0 %)
  3  inflow_rate         (pump flow, tenths of % per tick)
  4  outflow_rate        (drain flow, tenths of % per tick)
  5  alarm_word          (bit0 = HIGH-HIGH >95 %, bit1 = LOW-LOW <5 %)
"""

import argparse
import asyncio
import logging

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartAsyncTcpServer

log = logging.getLogger("water-tank")

# Function codes used by pymodbus' getValues/setValues
FC_COILS = 1
FC_HR = 3

# Coil addresses
PUMP, VALVE, AUTO, MANUAL_PUMP = 0, 1, 2, 3
# Holding register addresses
LEVEL, LOW_SP, HIGH_SP, INFLOW, OUTFLOW, ALARMS = 0, 1, 2, 3, 4, 5

HH_LIMIT = 950
LL_LIMIT = 50


def build_context() -> ModbusServerContext:
    # pymodbus data blocks are offset by 1 relative to the protocol address
    coils = ModbusSequentialDataBlock(1, [0, 1, 1, 0] + [0] * 12)
    hr = ModbusSequentialDataBlock(1, [500, 300, 800, 25, 12, 0] + [0] * 10)
    # pymodbus 3.9 only honours co/hr when di is supplied as well
    device = ModbusSlaveContext(di=ModbusSequentialDataBlock(1, [0] * 16),
                                co=coils,
                                ir=ModbusSequentialDataBlock(1, [0] * 16),
                                hr=hr)
    return ModbusServerContext(slaves=device, single=True)


def scan(ctx: ModbusServerContext) -> None:
    """One PLC scan cycle: read inputs, run logic, update process + outputs."""
    dev = ctx[0]
    level, low_sp, high_sp, inflow, outflow, _ = dev.getValues(FC_HR, LEVEL, 6)
    pump, valve, auto, manual = dev.getValues(FC_COILS, PUMP, 4)

    # --- control logic (same as the IEC 61131-3 program) ---
    # Setpoint sanity: out-of-range values are reset so a tampered
    # setpoint can't disable the hysteresis
    if not 100 <= low_sp <= 500:
        low_sp = 300
        dev.setValues(FC_HR, LOW_SP, [low_sp])
    if not 600 <= high_sp <= 900:
        high_sp = 800
        dev.setValues(FC_HR, HIGH_SP, [high_sp])

    if auto:
        if level < low_sp:
            pump = 1
        elif level > high_sp:
            pump = 0
    else:
        pump = manual

    # Safety interlock: independent of mode or setpoints
    if level >= HH_LIMIT:
        pump = 0

    # --- process physics ---
    level += inflow if pump else 0
    level -= outflow if valve else 0
    level = max(0, min(1000, level))

    alarms = (1 if level >= HH_LIMIT else 0) | (2 if level <= LL_LIMIT else 0)

    dev.setValues(FC_HR, LEVEL, [level])
    dev.setValues(FC_HR, ALARMS, [alarms])
    dev.setValues(FC_COILS, PUMP, [pump])


async def process_loop(ctx: ModbusServerContext, period: float) -> None:
    while True:
        scan(ctx)
        dev = ctx[0]
        level = dev.getValues(FC_HR, LEVEL, 1)[0]
        pump, valve = dev.getValues(FC_COILS, PUMP, 2)
        log.info("level=%5.1f%% pump=%s valve=%s",
                 level / 10, "ON" if pump else "OFF", "OPEN" if valve else "CLOSED")
        await asyncio.sleep(period)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--period", type=float, default=1.0, help="scan time (s)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(message)s")
    ctx = build_context()
    asyncio.create_task(process_loop(ctx, args.period))
    log.info("Modbus/TCP server listening on %s:%d", args.host, args.port)
    await StartAsyncTcpServer(context=ctx, address=(args.host, args.port))


if __name__ == "__main__":
    asyncio.run(main())
