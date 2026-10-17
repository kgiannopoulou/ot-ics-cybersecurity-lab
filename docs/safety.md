# Safety and scope

> **This lab is for an isolated environment you own. Nothing here should ever
> touch a production or safety-related network.**

## Why this matters more for OT than IT

Industrial control systems are fragile and long-lived. A port scan that is
routine on an IT network has crashed PLCs; a single malformed Modbus request
can fault a controller; and the physical process behind it — a pump, a valve, a
motor — can injure people or damage equipment. OT security testing is therefore
done against **simulations, test rigs or maintenance windows with engineering
sign-off**, never casually against live plant.

## What this repository contains

Everything here is **simulated**. There is no real PLC, no real sensor, no real
process:

| Component | In this lab | In a real plant |
|---|---|---|
| PLC | Python soft-PLC (`simulator/water_tank_plc.py`) + an IEC 61131-3 program for OpenPLC | A hardware PLC (Siemens, Allen-Bradley, …) |
| Process | Numbers in a loop (tank physics in software) | Water, pumps, valves, instruments |
| HMI | A small Flask page | SCADA (ScadaBR, Ignition, WinCC, …) |
| Network | Docker bridges / VirtualBox host-only networks | Switches, VLANs, a real firewall |
| "Attacker" | Scripts that speak Modbus to the lab's own container | — |

The [attack scripts](../attack) are ordinary Modbus **clients**. They contain no
exploit code: the whole point of the lab is that *a plain, well-formed Modbus
request is already the attack*, because the protocol authenticates nothing. That
is what the segmentation, host allow-list and monitoring exist to contain.

## Rules for running it

1. **Isolated only.** Run it on a host-only / internal Docker network or an
   air-gapped VM. The OT network in the Docker build is marked `internal: true`
   (no route to the internet); keep it that way.
2. **Point the attack scripts only at this lab.** `--target` must be the lab's
   own simulated PLC (`10.30.30.10`) on a network you own. Running a Modbus
   client against equipment you are not explicitly authorised to test may be
   illegal and is never safe.
3. **Authorisation.** Even for the simulation, if you run it on shared or
   employer infrastructure, get permission first.
4. **No real devices.** Do not substitute a real PLC for the simulator and then
   run the write/overflow scenarios against it outside a sanctioned test rig.

## The defence-in-depth the lab demonstrates

The reason an unauthorised write in this lab cannot overflow the tank is **not**
the monitoring — detection happens after the fact. It is the controls layered
underneath, which `tools/validate.py` and `tests/test_attack_scenarios.py`
exercise:

- **Segmentation + host allow-list** stop the unauthorised client from reaching
  Modbus at all (once applied).
- **In-controller input validation** resets out-of-range setpoints.
- **A safety interlock** forces the pump off at 95 %, independent of any write.

In a real plant the last of these belongs to an **independent Safety
Instrumented System** on a separate network, never to the same controller an
attacker might reach.
