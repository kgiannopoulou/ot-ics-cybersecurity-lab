# Contributing

Thanks for taking a look. This is a personal portfolio lab, but issues and pull
requests are welcome — new detection scenarios are the most useful.

## Setup

Requirements: Docker (Compose v2) and Python 3.11+.

```sh
git clone https://github.com/kgiannopoulou/ot-ics-cybersecurity-lab.git
cd ot-ics-cybersecurity-lab
pip install -r requirements.txt pytest
python -m pytest tests/                 # control logic + attack scenarios against the soft PLC
docker compose up -d --build            # the live lab
python tools/validate.py                # red/blue validation against the live lab
```

## Adding a scenario

1. Write the attack as a script under `attack/` (it must only target the lab's own addresses).
2. Add the detection: a Suricata rule in `detection/suricata-rules/` (next free SID in the
   `9000xxx` range, with the ATT&CK for ICS technique in the message) and, if it needs
   correlation, a Wazuh rule.
3. Prove normal traffic stays clean: the baseline pcap must still produce **zero** alerts
   (CI checks this).
4. Document it in `attack-scenarios/` with the ATT&CK and IEC 62443 mappings, investigation steps
   and mitigation, and add it to `tools/validate.py`.

If you change a committed pcap, update `pcaps/SHA256SUMS`.

## Workflow

* Branch from `main` (`feat/…`, `fix/…`, `docs/…`).
* Conventional Commits: `feat: detect Modbus function 16 to coil range`, `fix: allow HMI polling burst`.
* Open a pull request with what changed, why, and the validation output.

## Safety

Never point the attack scripts at equipment you are not authorised to test. See
[docs/safety.md](docs/safety.md).
