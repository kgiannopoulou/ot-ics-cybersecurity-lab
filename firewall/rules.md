# IT/OT firewall policy (pfSense / OPNsense)

Design principle (IEC 62443-3-3 SR 5.1 / SR 5.2, *zones and conduits*): **default deny between zones**. A flow crosses a conduit only if it has a documented business need, and nothing in IT talks to the PLC directly.

## Interfaces

| Interface | Zone | Subnet | Purdue level | Target security level |
|---|---|---|---|---|
| `LAN_IT` | Enterprise / SOC | 10.10.10.0/24 | L4–L5 | SL-1 |
| `DMZ`    | IT/OT DMZ        | 10.20.20.0/24 | L3.5  | SL-2 |
| `OT`     | Control          | 10.30.30.0/24 | L1–L2 | SL-2 |

## Rule set (evaluated top-down, first match wins)

| # | Iface | Source | Destination | Port/Proto | Action | Justification |
|---|---|---|---|---|---|---|
| 1 | LAN_IT | ENG_WS 10.10.10.50 | JUMP 10.20.20.10 | TCP 3389, 22 | Pass + log | Engineering access goes through a jump host only |
| 2 | DMZ | JUMP 10.20.20.10 | HMI 10.30.30.20 | TCP 8080 | Pass + log | Engineers reach the HMI from the jump host |
| 3 | DMZ | JUMP 10.20.20.10 | PLC 10.30.30.10 | TCP 8080 | Pass + log, **maintenance-window schedule** | OpenPLC programming UI, time-limited |
| 4 | OT  | HMI 10.30.30.20 | HIST 10.20.20.20 | TCP 5432 | Pass | Process data pushed *up* to the historian (OT initiates) |
| 5 | OT  | OT net | WAZUH 10.10.10.100 | TCP 1514–1515 | Pass | Security telemetry leaves OT |
| 6 | LAN_IT | any | OT net | TCP 502 | **Block + log** | No Modbus from IT, ever (alert source for Wazuh) |
| 7 | LAN_IT | any | OT net | any | Block + log | No direct IT→OT path |
| 8 | OT  | OT net | any (internet) | any | Block + log | Control network has no internet egress |
| 9 | any | any | any | any | Block + log | Default deny |

Inside the OT zone, **Modbus/TCP 502 to the PLC is allowed only from the HMI (10.30.30.20)**. Traffic within one subnet never crosses the firewall, so this is enforced by the OpenPLC host firewall and monitored by Suricata (SID 9000001):

```sh
# on the OpenPLC VM
ufw default deny incoming
ufw allow from 10.30.30.20 to any port 502 proto tcp
ufw allow from 10.20.20.10 to any port 8080 proto tcp
ufw enable
```

## Docker equivalent
`iptables-it-ot.sh` loads the same policy into the `fw` container, which is the only container connected to both `it_net` and `ot_net`.

## Logging
- pfSense sends remote syslog to Wazuh (`10.10.10.100:514/udp`), parsed by the built-in `pf` decoder.
- Hits on rule 6 trigger Wazuh rule **100210** (level 10). See `detection/wazuh/local_rules.xml`.

## Review checklist
- [ ] No `any → OT` pass rules
- [ ] Rule 3 disabled outside maintenance windows
- [ ] Logging enabled on every pass rule
- [ ] Each change references a change ticket in the rule description
