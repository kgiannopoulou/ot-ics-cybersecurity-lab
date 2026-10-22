# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- README: design decisions, limitations and "from lab to a real plant".
- MIT licence, `CONTRIBUTING.md` and this changelog.

## [1.1.0] - 2026-10-17

### Added
- Repeatable attack scripts (`python -m attack.run …`) and a red-team container profile.
- Automated red/blue harness (`tools/validate.py`): every scenario proves attack → detected → blocked.
- Host allow-list on the PLC (mitigation for F-01), validated live.

## [1.0.0] - 2026-10-05

### Added
- Water tank process: IEC 61131-3 program for OpenPLC and an identical Python soft PLC with unit tests.
- IT / DMZ / OT zones with a default-deny conduit firewall (pfSense rule set + iptables).
- 13 allow-list Suricata rules for Modbus/TCP built from a baseline capture, and 10 Wazuh rules with correlation.
- Three detection scenarios mapped to ATT&CK for ICS and IEC 62443, threat model and security assessment.
- Docker Compose build, VM build guide, HMI, baseline pcaps with checksums, and CI.

[Unreleased]: https://github.com/kgiannopoulou/ot-ics-cybersecurity-lab/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/kgiannopoulou/ot-ics-cybersecurity-lab/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/kgiannopoulou/ot-ics-cybersecurity-lab/releases/tag/v1.0.0
