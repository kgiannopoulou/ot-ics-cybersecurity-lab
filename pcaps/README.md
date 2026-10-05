# Packet captures

| File | Description |
|---|---|
| `baseline-normal-modbus.pcap` | 119 s of normal operation captured on the PLC interface (Docker build, 2026-10-05). 715 packets. |

## Baseline profile
```
tshark -r baseline-normal-modbus.pcap -Y modbus -T fields -e ip.src -e ip.dst -e modbus.func_code
```
| Direction | Function | Frames |
|---|---|---|
| HMI 10.30.30.20 → PLC 10.30.30.10 | FC1 Read Coils | 119 |
| HMI 10.30.30.20 → PLC 10.30.30.10 | FC3 Read Holding Registers | 119 |
| PLC → HMI | FC1 / FC3 responses | 119 / 119 |

One master, two read-only function codes, 1 Hz polling. This is what the Suricata allow-list rules are built from.

## Useful Wireshark filters
| Filter | Purpose |
|---|---|
| `mbtcp` | All Modbus/TCP |
| `modbus.func_code in {5 6 15 16}` | Any write |
| `mbtcp && ip.src != 10.30.30.20` | Modbus from anything but the HMI |
| `modbus.func_code == 43 \|\| modbus.func_code == 8` | Identification / diagnostics |
| `tcp.flags.syn==1 && tcp.flags.ack==0 && tcp.dstport==502` | New sessions to port 502 |

## Capturing your own
```sh
docker run --rm --network container:plc-water-tank -v "$PWD/pcaps:/out" \
  nicolaka/netshoot tcpdump -i eth0 -w /out/capture.pcap tcp port 502
```
