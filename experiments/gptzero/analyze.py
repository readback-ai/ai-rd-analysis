"""Analysis for the GPTZero calibration: per-arm score tables, the
within-author paired contrast, and the caveats that bound what any of
it licenses."""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

ARMS = (("Q2-AI", lambda r: r["arm"] == "P" and r["ai"]),
        ("Q2-nonAI", lambda r: r["arm"] == "P" and not r["ai"]),
        ("Q1-persistent", lambda r: r["arm"] == "B1"),
        ("Q1-independent", lambda r: r["arm"] == "B2"))

CAVEATS = """\
Caveats (they bound every number above):
- Paired authors are by construction AI ADOPTERS; the non-AI arm is
  adopters' UNMARKED PRs. This measures "does GPTZero separate the same
  adopter's marked vs unmarked code" — not a population detection rate,
  and not AI vs verified-human.
- Unmarked != human everywhere; undisclosed AI in the unmarked arm
  biases the separation DOWN (estimates are conservative).
- Q1-2024 rates are DESCRIPTIVE: near-human-era text, not verified
  human, and any AI present is early-model output.
- The paired arm is A-and-C-heavy: layer-B (bot-login agent) PRs cannot
  anchor a human-paired design and are absent.
- Truncated documents measure a diff's head only (share reported above).
- Near-uniform scores in ALL arms would itself be the answer: no signal
  on bare added-lines code."""


def load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines()
            if ln.strip()]


def ai_prob(row: dict) -> float | None:
    probs = row.get("class_probabilities") or {}
    p = probs.get("ai")
    if p is None:
        p = row.get("completely_generated_prob")
    return p


def arm_stats(rows: list[dict]) -> dict | None:
    ps = sorted(p for p in (ai_prob(r) for r in rows) if p is not None)
    if not ps:
        return None
    q = statistics.quantiles(ps, n=4) if len(ps) >= 2 else [ps[0]] * 3
    flagged = sum(1 for r in rows if r.get("predicted_class") == "ai")
    mixed = sum(1 for r in rows if r.get("predicted_class") == "mixed")
    return {"n": len(ps), "mean": statistics.fmean(ps),
            "median": statistics.median(ps), "q1": q[0], "q3": q[2],
            "flag_ai": flagged / len(ps), "flag_mixed": mixed / len(ps),
            "truncated": sum(1 for r in rows if r.get("truncated"))
            / len(rows)}


def paired(rows: list[dict]) -> dict | None:
    """Within-author contrast over Arm-P authors with BOTH slots scored:
    wins = pairs where the AI-marked PR scores strictly higher; exact
    one-sided binomial sign test (ties dropped)."""
    by_author: dict = {}
    for r in rows:
        if r["arm"] == "P" and ai_prob(r) is not None:
            by_author.setdefault(r["author"], {})[
                "ai" if r["ai"] else "nonai"] = ai_prob(r)
    gaps = [v["ai"] - v["nonai"] for v in by_author.values()
            if "ai" in v and "nonai" in v]
    if not gaps:
        return None
    wins = sum(1 for g in gaps if g > 0)
    losses = sum(1 for g in gaps if g < 0)
    n = wins + losses
    p = (sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n
         if n else float("nan"))
    return {"pairs": len(gaps), "wins": wins, "losses": losses,
            "ties": len(gaps) - n, "mean_gap": statistics.fmean(gaps),
            "sign_p": p}


def report(results_path: Path) -> None:
    rows = load_rows(results_path)
    if not rows:
        print(f"no results at {results_path} — run --score first")
        return
    print(f"{'arm':16}{'n':>4}{'mean':>7}{'median':>8}{'q1':>6}{'q3':>6}"
          f"{'ai%':>7}{'mixed%':>8}{'trunc%':>8}")
    for name, pred in ARMS:
        s = arm_stats([r for r in rows if pred(r)])
        if s is None:
            print(f"{name:16}   —")
            continue
        print(f"{name:16}{s['n']:>4}{s['mean']:>7.2f}{s['median']:>8.2f}"
              f"{s['q1']:>6.2f}{s['q3']:>6.2f}{100 * s['flag_ai']:>6.0f}%"
              f"{100 * s['flag_mixed']:>7.0f}%"
              f"{100 * s['truncated']:>7.0f}%")
    pr = paired(rows)
    if pr:
        print(f"\npaired (n={pr['pairs']}): AI PR scores higher in "
              f"{pr['wins']}/{pr['wins'] + pr['losses']} decided pairs "
              f"({pr['ties']} ties); mean gap {pr['mean_gap']:+.2f}; "
              f"one-sided sign test p={pr['sign_p']:.3f}")
    versions = sorted({r.get("model_version") for r in rows
                       if r.get("model_version")})
    print(f"\nGPTZero model version(s): {versions or 'unknown'}")
    print()
    print(CAVEATS)
