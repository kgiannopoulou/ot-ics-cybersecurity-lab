# Threat model: Water Tank T-101 control system

Method: asset → zone/conduit → threat actor → attack path → impact → control. Aligned with IEC 62443-3-2 (security risk assessment for system design) and mapped to MITRE ATT&CK for ICS.

## 1. System under consideration
A single water storage tank whose level is kept between 30 % and 80 % by a PLC switching a fill pump, with an operator-controlled outlet valve. Supervised from an HMI and monitored by a SOC in the IT zone.

**Safety/business consequence of compromise**
| Consequence | Cause | Severity |
|---|---|---|
| Tank overflow (spill, flooding, equipment damage) | Pump forced ON / interlock defeated | High |
| Tank runs dry (pump cavitation, loss of supply downstream) | Pump forced OFF with valve open | High |
| Operators blinded (wrong values on HMI) | HMI / communication manipulation | Medium–High |
| Loss of view / control (DoS) | Network flood, PLC stop | Medium |

## 2. Zones & conduits (IEC 62443-3-2 ZCR 3)

| Zone | Assets | SL-T | Rationale |
|---|---|---|---|
| Z1 Enterprise/SOC | Workstations, Wazuh | SL-1 | Internet-connected, high exposure, low process impact |
| Z2 DMZ | Jump host, historian | SL-2 | Brokers all IT↔OT interaction |
| Z3 Control | PLC, HMI | SL-2 | Direct process impact; protocols lack authentication |

| Conduit | Allowed flows | Enforcement |
|---|---|---|
| C1 Z1↔Z2 | RDP/SSH to jump host from engineering WS only | pfSense |
| C2 Z2↔Z3 | Jump→HMI 8080, Jump→PLC 8080 (maintenance), HMI→historian 5432 | pfSense |
| C3 Z3→Z1 | Wazuh agent 1514/1515 | pfSense |

## 3. Threat actors

| Actor | Capability | Likely entry |
|---|---|---|
| Opportunistic external (ransomware) | Medium | Phishing → IT foothold → pivot attempts |
| Malicious/careless insider or contractor | Low–Medium | Laptop on OT switch, USB, misuse of HMI |
| Targeted ICS actor | High | Supply chain, remote access, custom Modbus tooling |

## 4. Attack paths → ATT&CK for ICS

| # | Path | Techniques | Lab scenario |
|---|---|---|---|
| AP1 | Rogue device on OT network reads/writes PLC | T0886, T0861, T0855 | [Scenario 01](../attack-scenarios/scenario-01-unauthorised-plc-access.md) |
| AP2 | Compromised IT host pivots to OT | T0866, T0886, T0822 | [Scenario 02](../attack-scenarios/scenario-02-it-to-ot-pivot.md) |
| AP3 | Unauthorised writes to setpoints / coils / mode | T0855, T0836, T0858, T0831 | [Scenario 03](../attack-scenarios/scenario-03-process-manipulation.md) |
| AP4 | PLC program modified via programming UI (default creds) | T0812 Default Credentials, T0843 Program Download, T0839 Module Firmware | FIM rule 100221, runtime rule 100220 |
| AP5 | Discovery of OT assets | T0846, T0888 | SIDs 9000006/7/9 |
| AP6 | OT host beacons to the internet | T0884, T0869 | SID 9000010 |

## 5. Why Modbus/TCP is the core risk
- **No authentication**: any host that reaches TCP 502 is a valid master.
- **No integrity/confidentiality**: values are cleartext and can be modified in transit.
- **No authorization granularity**: no per-register permissions.

The controls therefore have to come from the **network** (segmentation, allow-lists), **monitoring** (protocol-aware IDS) and the **controller logic** (interlocks, input validation).

## 6. Control set

| Layer | Control | IEC 62443-3-3 SR | Implemented in |
|---|---|---|---|
| Network | Zone firewall, default deny, no IT→OT | SR 5.1, 5.2 | `firewall/rules.md`, `iptables-it-ot.sh` |
| Network | Modbus allow-list on PLC host | SR 2.1, 5.1 | `firewall/rules.md` (ufw) |
| Network | No internet egress from OT | SR 5.2 | rule 8 |
| Access | Jump host + MFA, time-boxed PLC programming | SR 1.1, 1.13, 2.1 | rules 1–3 |
| Device | Change OpenPLC default credentials; disable unused protocols | SR 1.5, 7.7 | `plc/water-tank-program/README.md` |
| Logic | Safety interlock + setpoint validation | SR 3.5, 3.6 | `water_tank.st`, simulator |
| Monitoring | Protocol-aware IDS with allow-list rules | SR 6.2 | `detection/suricata-rules/` |
| Monitoring | SIEM correlation (recon → write), FIM on logic | SR 6.1, 3.4 | `detection/wazuh/` |
| Response | Investigation playbooks | SR 6.1 | scenario docs |

## 7. Residual risks
- A compromised **HMI** is an authorised Modbus master. Write-pattern rules and in-PLC interlocks reduce but don't remove this risk.
- Single PLC acts as both control and protection. A real plant needs an independent **SIS**.
- The lab doesn't cover wireless, remote vendor access or supply-chain integrity of PLC firmware.
