# Suricata OT rules

| SID | Detects | ATT&CK for ICS |
|---|---|---|
| 9000001 | Modbus session to the PLC from any host other than the HMI | T0886 Remote Services |
| 9000002 | Modbus SYN from the IT zone (only possible if the firewall fails) | T0886 |
| 9000003 | Modbus write from a non-HMI host | T0855 Unauthorized Command Message |
| 9000004 | Write to holding registers 0–2 (level / setpoints) | T0836 Modify Parameter |
| 9000005 | Write to the PLC-owned pump coil | T0855 |
| 9000013 | Write to mode coils (AUTO / manual command) | T0858 Change Operating Mode |
| 9000006 | FC8 diagnostics | T0888 Remote System Information Discovery |
| 9000007 | FC43 encapsulated interface / device identification | T0888 |
| 9000008 | More than 10 writes in 10 s from one source | T0806 Brute Force I/O |
| 9000009 | Port 502 sweep across the OT subnet | T0846 Remote System Discovery |
| 9000010 | OT host connecting to an external network | T0884 Connection Proxy |
| 9000011/12 | Modbus parser anomalies (bad protocol id / function code) | protocol misuse |

## Approach
The rules are **allow-list based**. The baseline (`pcaps/README.md`) shows one Modbus master, two read function codes, and a single legitimate write target, so anything outside that is a high-fidelity signal with no tuning against noisy signatures. Re-baseline after any legitimate change to the HMI or PLC program.

## Sensor placement
In the Docker build, Suricata shares the PLC container's network namespace, which is equivalent to a SPAN/tap port on the switch port facing the PLC. Traffic between two hosts on the same OT subnet never crosses the firewall, so a sensor only on the firewall would miss HMI↔PLC traffic entirely.

## Validation
```sh
# syntax / config test
docker run --rm -v "$PWD:/r" jasonish/suricata:7.0 -T -c /r/suricata-ot.yaml -S /r/modbus-ot.rules
# -> 13 rules successfully loaded, 0 rules failed

# replay the baseline: expect 0 alerts
docker run --rm -v "$PWD/../..:/r" jasonish/suricata:7.0 -c /r/detection/suricata-rules/suricata-ot.yaml \
  -S /r/detection/suricata-rules/modbus-ot.rules -r /r/pcaps/baseline-normal-modbus.pcap -k none -l /tmp
```
