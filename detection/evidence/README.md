# Validation evidence (2026-10-05)

Everything here comes from running the Docker build of the lab on 2026-10-05.

## 1. Baseline: zero false positives
`pcaps/baseline-normal-modbus.pcap` (119 s, 715 packets, captured on the PLC interface) replayed through Suricata 7.0.17 with `modbus-ot.rules`:

```
13 signatures processed ... 10 inspect application layer
alerts: 0
```

## 2. Unauthorised Modbus client: detected
`suricata-fast-validation.log`, `suricata-eve-alerts.json`. Read-only FC3 request from 10.30.30.66:

```
[1:9000001:1] OT Modbus traffic from unauthorised client {TCP} 10.30.30.66:55056 -> 10.30.30.10:502
```

## 3. IT → OT Modbus: blocked
iptables counters on the conduit firewall after a connection attempt from 10.10.10.66:

```
 pkts bytes target  source          destination     
    4   240 LOG     10.10.10.0/24   10.30.30.0/24   tcp dpt:502 prefix "FW-DENY-MODBUS-IT2OT: "
    4   240 DROP    10.10.10.0/24   10.30.30.0/24   tcp dpt:502
```

## 4. Wazuh rules: wazuh-logtest (manager 4.9.2)
Input 1 is the **real** EVE alert from (2). Inputs 2–5 are **synthetic rule-test events** (the real alert with a changed `signature_id`, plus a sample iptables LOG line) used to exercise each rule path.

| Input | Expected | Result |
|---|---|---|
| Real EVE alert, SID 9000001 | 100201 level 10 | ✅ `100201` level 10, groups `mitre_ics_T0886` |
| SID 9000007 (FC43 identification) | 100203 level 7 | ✅ `100203` level 7 |
| SID 9000004 (setpoint write), same src, after recon | 100204 level 15 (correlation) | ✅ `100204` level 15 |
| iptables `FW-DENY-MODBUS-IT2OT` | 100211 level 10 | ✅ `100211` level 10 |
| SID 9000010 (OT egress) | 100205 level 12 | ✅ `100205` level 12 |

## 5. Control logic: unit tests
```
$ python -m pytest -q tests/
7 passed
```
