# SCADA / HMI

Two HMI implementations against the same Modbus map:

| Build | HMI | Location |
|---|---|---|
| VM build | **ScadaBR 1.2** on `hmi01` (10.30.30.20) | configured as below |
| Docker build | Flask HMI | `hmi/hmi.py` → http://127.0.0.1:8080 |

![HMI](../screenshots/hmi-water-tank.png)

## ScadaBR configuration

**Data source**: *Modbus IP*
| Setting | Value |
|---|---|
| Host | 10.30.30.10 |
| Port | 502 |
| Transport | TCP (keep-alive) |
| Update period | 1 s |
| Slave id | 1 |

**Data points**
| Name | Range | Offset | Type | Settable | Notes |
|---|---|---|---|---|---|
| T101_Level | Holding register | 0 | 2-byte unsigned, multiplier 0.1, unit % | No | Process value |
| T101_LowSP | Holding register | 1 | 2-byte unsigned, ×0.1 | **No** | Changed only via engineering change |
| T101_HighSP | Holding register | 2 | 2-byte unsigned, ×0.1 | **No** | 〃 |
| T101_Alarms | Holding register | 5 | 2-byte unsigned | No | bit0 HH, bit1 LL |
| P101_Running | Coil | 0 | Binary | **No** | PLC-owned output |
| V101_Open | Coil | 1 | Binary | Yes | The only operator write |
| T101_Auto | Coil | 2 | Binary | No | |

Making only `V101_Open` settable is a security control: it keeps the HMI's write footprint to a single coil, which is what lets Suricata SIDs 9000004/5/13 treat any other write as suspicious, even from the HMI.

**Alarms (event detectors)**
- T101_Level ≥ 95 → *Critical* "Tank HIGH-HIGH"
- T101_Level ≤ 5 → *Urgent* "Tank LOW-LOW"
- Data source communication failure → *Urgent* "PLC comms lost"

**Hardening**
- Change the default `admin/admin` login; create a read-only *operator* user and a separate *engineer* user.
- Bind the web UI to the OT interface only; reach it from IT via the jump host.
- Export the project (`Import/Export`) to version control and watch it with Wazuh FIM (rule 100221).
