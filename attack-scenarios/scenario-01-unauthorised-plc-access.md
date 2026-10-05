# Scenario 01: Unauthorised workstation communicates with the PLC

| | |
|---|---|
| **Zone** | OT (Purdue L1–L2) |
| **ATT&CK for ICS** | T0886 Remote Services · T0801 Monitor Process State · T0861 Point & Tag Identification |
| **IEC 62443-3-3** | SR 1.1 (human user identification & authentication), SR 2.1 (authorization enforcement), SR 5.1 (network segmentation), SR 6.2 (continuous monitoring) |
| **Status** | ✅ Executed and validated in the Docker build on 2026-10-05 |

## Story
A contractor plugs a laptop into a spare port on the OT switch and gets an address in 10.30.30.0/24. Modbus/TCP has no authentication, so any host that can reach TCP 502 can read, and in principle write, the PLC's coils and registers. Reading alone already exposes the full process state (tank level, setpoints, pump status) that an attacker needs before attempting any manipulation.

## Normal behaviour (baseline)
From `pcaps/baseline-normal-modbus.pcap` (119 s, captured on the PLC interface):

| Client | Server | Function | Count |
|---|---|---|---|
| 10.30.30.20 (HMI) | 10.30.30.10 (PLC) | FC1 Read Coils | 119 |
| 10.30.30.20 (HMI) | 10.30.30.10 (PLC) | FC3 Read Holding Registers | 119 |

Exactly **one** Modbus client, two read function codes, ~1 Hz. Replaying the baseline through Suricata produced **0 alerts**.

## Anomaly (executed)
A container representing the rogue laptop (`10.30.30.66`) opened a Modbus session to the PLC and performed a **single read-only** FC3 request for HR0–5. The PLC answered: `[366, 300, 800, 25, 12, 0]`, revealing the level (36.6 %) and both setpoints.

## Detection
Suricata on the PLC tap fired immediately:

```
10/05/2026-16:36:34.022989 [**] [1:9000001:1] OT Modbus traffic from unauthorised client [**]
[Classification: Potential Corporate Privacy Violation] [Priority: 1] {TCP} 10.30.30.66:55056 -> 10.30.30.10:502
```
Full EVE record: `detection/evidence/suricata-eve-alerts.json`.
In Wazuh this maps to rule **100201** (level 10, MITRE T0886).

## Investigation checklist
1. Is the source IP in the asset inventory? (`architecture/ip-addressing.md`) → **No**
2. Which switch port / MAC? (managed-switch CAM table, DHCP logs)
3. Which function codes were used? Reads only, or writes? (EVE `modbus` fields or Wireshark `modbus.func_code`)
4. Did the process deviate? Compare HMI trend and alarm history for the time window.
5. Any other OT assets contacted? (Suricata flow events from the same `src_ip`)

## Finding
**F-01 (High):** the detection works, but the PLC still **served the request**. Monitoring alone doesn't prevent access. Nothing on the controller restricts Modbus clients.

## Mitigation
| Control | Where | Effect |
|---|---|---|
| Host allow-list: only 10.30.30.20 → TCP 502 | OpenPLC VM (`ufw`, see `firewall/rules.md`) | Rogue reads/writes are dropped |
| Switch port security / 802.1X, disable unused ports | OT switch | Laptop doesn't get on the network |
| Static ARP / DHCP snooping on the OT VLAN | OT switch | Limits spoofing of the HMI address |
| Keep SID 9000001 → Wazuh 100201 at level ≥10 | SOC | Any bypass is still seen |

**Residual risk:** an attacker who compromises the HMI itself inherits its allow-listed access. That's covered by Scenario 03 (write-pattern detection) and by the PLC's internal interlocks.
