# Scenario 03: Unauthorised change to process control values

| | |
|---|---|
| **Zone** | OT (Purdue L1–L2) |
| **ATT&CK for ICS** | T0855 Unauthorized Command Message · T0836 Modify Parameter · T0858 Change Operating Mode · T0831 Manipulation of Control · T0880 Loss of Safety (impact) |
| **IEC 62443-3-3** | SR 3.1 communication integrity, SR 3.5 input validation, SR 3.6 deterministic output, SR 6.2 continuous monitoring |
| **Status** | 📋 Detection logic and in-controller safeguards implemented; live execution left for the VM build (see note) |

## Story
This is the high-impact case: an adversary on the OT network (Scenario 01) or controlling the HMI uses Modbus write function codes to change the process instead of just observing it. In the water tank, the objectives would be:

- **Overflow**: change the high setpoint, force the pump on, or switch to manual mode
- **Run dry**: stop the pump while the outlet valve stays open

Because Modbus has no authentication or integrity protection, the PLC will act on any well-formed write it receives.

## What normal looks like
Per the baseline, the HMI **never writes** during normal polling. The only legitimate write is **FC5 to coil 1 (outlet valve)**, triggered by an operator button and rare (a few per shift).

## Detection design
| Behaviour | Suricata SID | Wazuh rule | Why it's high-fidelity |
|---|---|---|---|
| Any write from a host that isn't the HMI | 9000003 | 100202 (13) | Only the HMI is an authorised master |
| Write to setpoint registers HR1/HR2 | 9000004 | 100202 (13) | Setpoints change only via engineering change control |
| Write to pump coil 0 | 9000005 | 100202 (13) | Pump is PLC-owned output, the HMI never writes it |
| Write to mode coils 2–3 | 9000013 | 100202 (13) | AUTO→MANUAL is an operating-mode change |
| > 10 writes in 10 s | 9000008 | 100200 (8) | Operators don't click that fast |
| Recon (FC8/FC43/sweep) then a write within 10 min | — | **100204 (15)** | Correlated kill-chain: recon → impact |

Process-side detection (independent of the network):
- HMI alarm word: HIGH-HIGH ≥ 95 %, LOW-LOW ≤ 5 %
- Physics check: level rising while the HMI shows pump OFF means sensor or HMI spoofing (T0832 Manipulation of View)

## Built-in safeguards (defence in depth inside the PLC)
`plc/water-tank-program/water_tank.st` and `simulator/water_tank_plc.py`:
1. **Safety interlock**: level ≥ 95 % forces the pump OFF in *any* mode, regardless of coil writes.
2. **Setpoint range validation**: low SP outside 10–50 % or high SP outside 60–90 % is reset to defaults on the next scan (IEC 62443 SR 3.5 input validation).

So even a successful unauthorised write can't push the tank beyond its safe envelope. In a real plant this role belongs to an independent **Safety Instrumented System (SIS)** on a separate network, never to the same controller.

## Investigation playbook
1. Triage Wazuh 100202/100204: source IP, function code, register/coil address, value.
2. Compare against the change-management calendar. Was there an approved maintenance window?
3. Check the HMI for the current values; **verify locally** at the PLC if the HMI could be compromised.
4. Containment: block the source at the switch/host firewall; put the process in a known-safe state (manual, local control) following the operating procedure, **not** by improvising on the live process.
5. Recovery: restore setpoints from the version-controlled program; confirm with operations before returning to AUTO.

## Note on execution
Live validation of the write rules is planned for the full VM build (OpenPLC + ScadaBR), where the tests run against the isolated lab only. All rules were syntax-validated against Suricata 7.0.17 (13/13 loaded) and produce zero alerts on the baseline capture.
