# Screenshots

| File | What it shows | Source |
|---|---|---|
| `hmi-water-tank.png` | HMI with live process values (level 38 %, pump OFF, valve OPEN, AUTO) | Docker build, 2026-10-05 |
| `../architecture/network-diagram.png` | Zone/conduit architecture | rendered from `network-diagram.svg` |

To add from the VM build (see `docs/vm-build.md`):
- [ ] OpenPLC runtime: program running, Modbus enabled
- [ ] ScadaBR watch list and alarm list
- [ ] pfSense rule set and firewall log showing rule 6 blocks
- [ ] Wazuh dashboard: `rule.groups: ot_ics` with alerts 100201/100202/100204
- [ ] Wireshark: baseline vs. unauthorised client, filter `mbtcp && ip.src != 10.30.30.20`
