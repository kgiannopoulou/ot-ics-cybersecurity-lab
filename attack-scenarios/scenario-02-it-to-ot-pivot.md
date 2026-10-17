# Scenario 02: IT host attempts to reach the PLC across the zone boundary

| | |
|---|---|
| **Zone** | Conduit IT (L4) ↔ OT (L1–L2) |
| **ATT&CK for ICS** | T0886 Remote Services · T0866 Exploitation of Remote Services (precondition) · T0822 External Remote Services |
| **IEC 62443-3-3** | SR 5.1 network segmentation, SR 5.2 zone boundary protection, SR 2.8 auditable events |
| **Difficulty** | 🟢 Low — a compromised IT host probing toward OT |
| **Status** | ✅ Executed and validated in the Docker build on 2026-10-05 |

## Story
Most real OT incidents start in IT: phishing → foothold on an office PC → lateral movement towards the control network. The Purdue model and IEC 62443 zones exist so that a compromised IT host **has no path** to Level 1 devices.

## Expected policy
`firewall/rules.md` rules 6, 7 and 9: no IT → OT flow, and Modbus from IT is explicitly logged and blocked.

## Test (executed)
A container on the IT network (`10.10.10.66`) was given a route to 10.30.30.0/24 via the conduit firewall and tried a plain TCP connection to `10.30.30.10:502`.

Result:
```
nc: connect to 10.30.30.10 port 502 (tcp) timed out: Operation in progress

iptables -L FORWARD -v -n
 pkts bytes target  prot  source          destination     
    4   240 LOG     6     10.10.10.0/24   10.30.30.0/24   tcp dpt:502 LOG prefix "FW-DENY-MODBUS-IT2OT: "
    4   240 DROP    6     10.10.10.0/24   10.30.30.0/24   tcp dpt:502
```
All 4 SYN attempts were logged and dropped. The PLC never saw a packet, so Suricata SID 9000002 (which watches for IT-sourced Modbus *inside* OT) correctly stayed silent. If it ever fires, the firewall has been bypassed or misconfigured.

## Detection
| Source | Signal | Wazuh rule |
|---|---|---|
| pfSense filterlog / iptables LOG | block on rule 6 | 100210 / 100211 (level 10) |
| Suricata (inside OT) | SID 9000002 → only if the firewall fails | 100201 (level 10) |

Repeated hits from one IT host should start an **IT-side investigation** of that host (EDR, user, recent logins): it's a symptom of compromise or of a misconfigured tool.

## Finding
**F-02 (Informational / pass):** zone boundary enforced as designed.

## Hardening still recommended
- Engineering access only via the DMZ jump host with MFA (rule 1 → 2/3); record sessions.
- Time-limit rule 3 (PLC programming UI) to approved maintenance windows.
- Quarterly firewall rule review; alert on any rule change (pfSense config history → Wazuh FIM).
