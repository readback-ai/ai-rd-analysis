"""Characterization dump of every plot-feeding study function.

The generated reports cover the report-wired studies; the figure scripts
additionally import these functions directly, so their outputs are captured
here as sorted JSON. Diffing this dump before/after a refactor is the
regression gate for the plot data (study-frame refactor, 2026-07).

Usage: PYTHONPATH=src python scripts/dump_plot_data.py > dump.json
"""
import json
import sys

sys.path.insert(0, "src")
from pipeline.studies.attention import attention_by_ai              # noqa: E402
from pipeline.studies.paper_tables import core_rows, usage_rows     # noqa: E402
from pipeline.studies.productivity import (adoption_event,          # noqa: E402
                                           adoption_monthly,
                                           event_by_adoption_month,
                                           fleet_logins, review_mix)
from pipeline.studies.review_action import lane_rows                # noqa: E402


def norm(x):
    """JSON-safe deep copy: tuple keys become their repr, tuples become
    lists, floats round to 12 significant digits (bit-identical math is
    the goal; the rounding only guards against platform repr noise)."""
    if isinstance(x, dict):
        return {repr(k): norm(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [norm(v) for v in x]
    if isinstance(x, float):
        return float(f"{x:.12g}")
    return x


def main() -> None:
    out = {
        "usage_rows": usage_rows(),
        "core_rows": core_rows(),
        "adoption_monthly": adoption_monthly(),
        "adoption_event": adoption_event(),
        "event_by_adoption_month": event_by_adoption_month(),
        "review_mix": review_mix(),
        "review_mix_ai": review_mix("ai"),
        "review_mix_ai_fleetslice": review_mix(by="ai", fleet_slice=True),
        "attention_by_ai": attention_by_ai(),
        "attention_by_ai_fleetslice": attention_by_ai(fleet_slice=True),
        "lane_rows": lane_rows(),
        "fleet_logins": sorted(fleet_logins()),
    }
    json.dump(norm(out), sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
