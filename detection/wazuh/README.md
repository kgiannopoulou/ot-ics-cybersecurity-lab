# Wazuh configuration

| File | Install to | Purpose |
|---|---|---|
| `local_rules.xml` | manager: `/var/ossec/etc/rules/local_rules.xml` | OT detection and correlation rules (100200–100299) |
| `ossec-agent-ot.conf` | agents on OT hosts: merge into `/var/ossec/etc/ossec.conf` | Suricata EVE ingestion, OpenPLC logs, FIM on PLC logic / HMI project |

## Rules

| ID | Level | Trigger | ICS technique group |
|---|---|---|---|
| 100200 | 8 | Any Suricata alert in the lab SID range | — |
| 100201 | 10 | Unauthorised Modbus client / IT-sourced Modbus | `mitre_ics_T0886` |
| 100202 | 13 | Process-impacting write (setpoints, pump/mode coils, non-HMI writer) | `T0855`, `T0836` |
| 100203 | 7 | Recon: FC8, FC43, port sweep | `T0846`, `T0888` |
| **100204** | **15** | **Recon followed by a process write from the same source within 10 min** | `T0846`, `T0855` |
| 100205 | 12 | OT asset connecting to an external network | `T0884` |
| 100210 | 10 | pfSense block of IT→OT Modbus | `T0886` |
| 100211 | 10 | iptables `FW-DENY-MODBUS-IT2OT` (Docker build) | `T0886` |
| 100220 | 12 | OpenPLC program upload / runtime stop | `T0843`, `T0881` |
| 100221 | 12 | FIM change on PLC program or HMI project files | `T0839` |

Wazuh's built-in MITRE module only knows Enterprise ATT&CK, so ICS technique IDs are attached as **groups** (`mitre_ics_Txxxx`). Filter in the dashboard with `rule.groups: mitre_ics_T0855`.

## Testing
```sh
/var/ossec/bin/wazuh-logtest < sample-events.log
```
Results for the lab are in `../evidence/README.md`. All five rule paths tested on Wazuh 4.9.2 fired at the expected level, including the 100204 correlation.

## Suggested dashboard
- Alerts over time, `rule.groups: ot_ics`, split by `rule.id`
- Top `data.src_ip` for `rule.groups: ot_ics_policy_violation`
- Table of `rule.level >= 13` for the shift handover
