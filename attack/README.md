# Attack scripts (lab validation)

Repeatable scripts that execute the documented attack scenarios against **the
lab's own PLC** (`10.30.30.10` in the Docker build, or a local soft-PLC), so
each scenario is a script you can run — not only prose — and so the
detection and mitigation claims can be checked automatically.

> ⚠️ **Isolated lab use only.** These scripts speak Modbus/TCP to a target you
> pass on the command line. Point them **only** at this lab's simulated PLC on a
> network you own. Modbus has no authentication: never run them against
> equipment you are not explicitly authorised to test. See
> [`../docs/safety.md`](../docs/safety.md).

Everything here is an ordinary Modbus **client** (the same `pymodbus` the HMI
uses). There are no exploits: the point of the lab is that a plain, well-formed
Modbus client is already "the attack", because the protocol trusts any master —
which is exactly what the segmentation, allow-list and monitoring exist to
contain.

## Scenarios

| Key | Scenario | ATT&CK for ICS | What the script does |
|---|---|---|---|
| `recon` | [01](../attack-scenarios/scenario-01-unauthorised-plc-access.md) | T0886, T0861 | Read HR0–5 and the coils: the full process state |
| `sweep` | [01](../attack-scenarios/scenario-01-unauthorised-plc-access.md) | T0846 | TCP-connect sweep of 502 across the OT subnet |
| `setpoint` | [03](../attack-scenarios/scenario-03-process-manipulation.md) | T0836 | Write a dangerous high setpoint (overflow attempt) |
| `pump` | [03](../attack-scenarios/scenario-03-process-manipulation.md) | T0855 | Write the PLC-owned pump coil directly |
| `mode` | [03](../attack-scenarios/scenario-03-process-manipulation.md) | T0858 | Flip AUTO→MANUAL, then force the pump |
| `overflow` | [03](../attack-scenarios/scenario-03-process-manipulation.md) | T0831, T0880 | Full sequence that tries to drive the tank past 95 % |

## Running

```sh
# Against the Docker lab (run from a container on the OT net, or the host if routable)
python -m attack.run recon    --target 10.30.30.10
python -m attack.run overflow --target 10.30.30.10 --json

# Against a local soft-PLC for a quick try (no Docker):
python simulator/water_tank_plc.py --port 5020 &
python -m attack.run setpoint --target 127.0.0.1 --port 5020
```

Each run prints what it attempted and what the PLC answered, and (with
`--json`) a machine-readable result the validation harness consumes. Exit code
is `0` when the attack's **objective** was achieved (e.g. the dangerous value
was accepted and stuck), non-zero when a control stopped it — so the same
script demonstrates both the vulnerability and, after mitigation, the fix.

## Automated red/blue validation

`tools/validate.py` runs each scenario **before and after** the mitigation and
asserts the expected change — the attack succeeds and is detected on the
unprotected lab, and is blocked once the control is in place. See
[`../docs/validation.md`](../docs/validation.md).
