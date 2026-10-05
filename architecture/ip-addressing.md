# IP addressing & asset inventory

An accurate asset inventory is the foundation of OT security (IEC 62443-2-1, CISA "know your assets"): every allow-list rule and every "unauthorised host" detection depends on it.

## Zones

| Zone | VLAN | Subnet | Gateway | Purdue | Description |
|---|---|---|---|---|---|
| IT / SOC | 10 | 10.10.10.0/24 | 10.10.10.254 | L4–L5 | Admin workstation, SIEM, analyst tools |
| DMZ / supervisory | 20 | 10.20.20.0/24 | 10.20.20.254 | L3.5 | Jump host, historian |
| OT / control | 30 | 10.30.30.0/24 | 10.30.30.254 | L1–L2 | PLC, HMI. **No internet egress** |

## Assets

| Hostname | IP | Zone | Role | OS / software | Listening services | Docker equivalent |
|---|---|---|---|---|---|---|
| fw01 | .254 on each VLAN | all | Zone firewall / router | pfSense CE 2.7 | 443 (mgmt, IT only) | `fw` (alpine + iptables) |
| kali-eng | 10.10.10.50 | IT | Engineering / admin workstation | Kali Linux | — | — |
| wazuh | 10.10.10.100 | IT | SIEM manager + indexer + dashboard | Wazuh 4.9 (Ubuntu 22.04) | 1514, 1515, 443 | — |
| jump01 | 10.20.20.10 | DMZ | Jump host for OT access (MFA) | Ubuntu 22.04 | 22 | — |
| hist01 | 10.20.20.20 | DMZ | Process historian | PostgreSQL 16 | 5432 | HMI leg on `sup_net` |
| plc01 | 10.30.30.10 | OT | Water tank controller | OpenPLC Runtime v3 (Ubuntu) | **502 Modbus**, 8080 (programming UI) | `plc` (Python soft PLC) |
| hmi01 | 10.30.30.20 | OT | SCADA / HMI | ScadaBR 1.2 (Ubuntu) | 8080 | `hmi` (Flask HMI) |
| ids01 | tap on OT switch | OT | Network IDS sensor | Suricata 7 + Zeek (optional) | none (passive) | `suricata` (PLC netns) |

## Authorised communication matrix

| From \ To | PLC :502 | PLC :8080 | HMI :8080 | Wazuh :1514 | Internet |
|---|---|---|---|---|---|
| HMI | ✅ read FC1/FC3, write FC5 coil 1 | ❌ | — | ✅ | ❌ |
| Jump host | ❌ | ✅ maintenance window | ✅ | — | ❌ |
| Engineering WS (IT) | ❌ | ❌ | via jump host | — | ✅ |
| Any other IT host | ❌ | ❌ | ❌ | — | ✅ |
| PLC | — | — | — | ✅ (if agent) | ❌ |

Anything not marked ✅ is a policy violation, and the detection rules in `detection/` are written against this matrix.
