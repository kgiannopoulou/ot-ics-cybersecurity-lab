# Full VM build (VirtualBox / VMware)

The Docker build reproduces the process, zones and detection logic on one machine. The VM build is the "realistic" version with real ICS software and a real firewall appliance.

## Resources

| VM | OS | vCPU | RAM | Disk | NICs |
|---|---|---|---|---|---|
| fw01 | pfSense CE 2.7 | 1 | 1 GB | 8 GB | WAN (NAT), `LAN_IT`, `DMZ`, `OT` |
| kali-eng | Kali Linux | 2 | 4 GB | 40 GB | `LAN_IT` |
| wazuh | Ubuntu 22.04 + Wazuh 4.9 all-in-one | 4 | 8 GB | 50 GB | `LAN_IT` |
| jump01 | Ubuntu 22.04 | 1 | 1 GB | 10 GB | `DMZ` |
| plc01 | Ubuntu 22.04 + OpenPLC v3 | 1 | 1 GB | 10 GB | `OT` |
| hmi01 | Ubuntu 22.04 + ScadaBR 1.2 | 2 | 2 GB | 15 GB | `OT` |
| ids01 | Ubuntu 22.04 + Suricata 7 (+ Zeek) | 2 | 2 GB | 20 GB | `OT` (mgmt) + `OT` (promiscuous) |

VirtualBox: create three **Internal Networks** (`it`, `dmz`, `ot`). Only fw01 has a NAT adapter. For ids01's sniffing NIC, set *Promiscuous Mode: Allow All*.

## Build order
Get each stage working before moving to the next.

1. **PLC**: install OpenPLC v3 on plc01 (`./install.sh linux`), upload `plc/water-tank-program/water_tank.st`, start the runtime, change the default credentials.
2. **Process**: run `simulator/water_tank_plc.py` (or wire OpenPLC's slave-device feature to it) so the tank level actually moves.
3. **HMI**: install ScadaBR on hmi01 and configure it as in `scada/README.md`. Confirm the level trend moves and the pump cycles 30 % ↔ 80 %.
4. **Firewall**: configure pfSense interfaces and the rule set from `firewall/rules.md`, plus the ufw allow-list on plc01. Test: an IT host must **not** reach 10.30.30.10:502.
5. **Monitoring**: install Suricata on ids01 with `detection/suricata-rules/`, the Wazuh agent on ids01/plc01/hmi01 with `ossec-agent-ot.conf`, the manager rules from `local_rules.xml`, and pfSense remote syslog to Wazuh.
6. **Baseline**: capture at least 30 min of normal traffic and confirm zero OT alerts.
7. **Scenarios**: run the scenarios in `attack-scenarios/` **only inside this isolated lab**, record detections, and apply the mitigations.
8. **Document**: screenshots (see `screenshots/README.md`), findings in `docs/security-assessment.md`.

## Safety and isolation
- The `ot` internal network has no route to the internet or your home LAN.
- Snapshot every VM before running scenarios.
- Never point lab tooling at real PLCs or industrial equipment you don't own.
