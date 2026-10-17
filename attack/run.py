"""Run one attack scenario against the lab PLC.

    python -m attack.run <scenario> --target 10.30.30.10 [--port 502] [--json]

Isolated-lab use only: point --target at this lab's simulated PLC on a network
you own (attack/README.md, docs/safety.md).
"""

from __future__ import annotations

import argparse
import json
import sys

from .scenarios import SCENARIOS, Probe


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="attack.run", description=__doc__.splitlines()[0])
    ap.add_argument("scenario", choices=sorted(SCENARIOS))
    ap.add_argument("--target", default="10.30.30.10", help="lab PLC IP (default 10.30.30.10)")
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--unit", type=int, default=1, help="Modbus unit/slave id")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    args = ap.parse_args(argv)

    fn = SCENARIOS[args.scenario]
    try:
        with Probe(args.target, args.port, args.unit) as p:
            result = fn(p)
    except Exception as err:  # connection refused, timeout, blocked by a firewall
        from .scenarios import AttackResult

        result = AttackResult(args.scenario, fn.__doc__.split(":")[0].strip() if fn.__doc__ else args.scenario,
                              [], False, f"could not reach {args.target}:{args.port}",
                              reached_plc=False, error=str(err))

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        flag = "OBJECTIVE ACHIEVED" if result.objective_achieved else "contained / blocked"
        print(f"[{args.scenario}] {result.attack}")
        print(f"  ATT&CK: {', '.join(result.mitre) or '-'}")
        print(f"  result: {flag}")
        print(f"  {result.detail}")
        if result.error:
            print(f"  error: {result.error}")
    # Exit 0 when the attack's objective was achieved (vulnerable), 1 when a
    # control stopped it, 2 on a connection error — so CI / validate.py can act on it.
    return 0 if result.objective_achieved else (2 if result.error else 1)


if __name__ == "__main__":
    sys.exit(main())
