"""Analysis for the GPTZero calibration: per-arm score tables, the
within-author paired contrast, and the caveats that bound what any of
it licenses."""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

def _p(period, ai):
    return lambda r: (r["arm"] == "P" and r["period"] == period
                      and r["ai"] == ai)


PAIRED_QUARTERS = ("Q4-2025", "Q1-2026", "Q2-2026")

ARMS = (("Q3-22-era", lambda r: r["arm"] == "B3"),
        ("Q1-24-persist", lambda r: r["arm"] == "B1"),
        ("Q1-24-indep", lambda r: r["arm"] == "B2"),
        ("Q4-25-AI", _p("Q4-2025", True)),
        ("Q4-25-nonAI", _p("Q4-2025", False)),
        ("Q1-26-AI", _p("Q1-2026", True)),
        ("Q1-26-nonAI", _p("Q1-2026", False)),
        ("Q2-26-AI", _p("Q2-2026", True)),
        ("Q2-26-nonAI", _p("Q2-2026", False)))

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
- The Q4-2025/Q1-2026 paired arms mirror the Q2-2026 design at the same
  depth, but marker/agent conventions were younger then: their AI arms
  capture a thinner (possibly different) slice of AI use, and their
  author sets overlap each other's and Q2-2026's, so quarters are not
  independent samples.
- The paired arm is A-and-C-heavy: layer-B (bot-login agent) PRs cannot
  anchor a human-paired design and are absent.
- Truncated documents measure a diff's head only (share reported above).
- Documents span 100-600 words and GPTZero's accuracy rises with
  length; the length-matched sensitivity bounds that confound — trust
  the headline pairing only where the two agree.
- Q3-2022-era predates ChatGPT: its positives are near-pure FALSE
  positives (early-Codex/Copilot-autocomplete volume was tiny) — the
  cleanest false-positive calibration in the design.
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
    cls = {c: sum(1 for r in rows if r.get("predicted_class") == c)
           for c in ("ai", "human", "mixed")}
    return {"n": len(ps), "mean": statistics.fmean(ps),
            "median": statistics.median(ps), "q1": q[0], "q3": q[2],
            "flag_ai": cls["ai"] / len(ps),
            "flag_human": cls["human"] / len(ps),
            "flag_mixed": cls["mixed"] / len(ps),
            "truncated": sum(1 for r in rows if r.get("truncated"))
            / len(rows),
            "mean_words": statistics.fmean(r.get("words", 0)
                                           for r in rows)}


LENGTH_MATCH_WORDS = 150   # pre-specified |Δwords| band for the
                           # length-matched sensitivity


def paired(rows: list[dict], period: str = "Q2-2026",
           max_word_gap: int | None = None) -> dict | None:
    """Within-author contrast over one quarter's Arm-P authors with BOTH
    slots scored: wins = pairs where the AI-marked PR scores strictly
    higher; exact one-sided binomial sign test (ties dropped). GPTZero
    accuracy rises with document length, so max_word_gap restricts to
    length-matched pairs — the pre-specified sensitivity that bounds the
    length confound."""
    by_author: dict = {}
    for r in rows:
        if r["arm"] == "P" and r["period"] == period \
                and ai_prob(r) is not None:
            by_author.setdefault(r["author"], {})[
                "ai" if r["ai"] else "nonai"] = \
                (ai_prob(r), r.get("words", 0))
    pairs = [v for v in by_author.values()
             if "ai" in v and "nonai" in v]
    if max_word_gap is not None:
        pairs = [v for v in pairs
                 if abs(v["ai"][1] - v["nonai"][1]) <= max_word_gap]
    gaps = [v["ai"][0] - v["nonai"][0] for v in pairs]
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
    versions = sorted({r.get("model_version") or "unknown"
                       for r in rows})
    if len(versions) > 1:
        print(f"REFUSING pooled analysis: results mix detector versions "
              f"{versions} — pin gptzero_client.PINNED_VERSION and "
              f"re-score so every document is judged by one model.")
        return
    print(f"{'arm':14}{'n':>4}{'mean':>7}{'median':>8}{'q1':>6}{'q3':>6}"
          f"{'ai%':>7}{'human%':>8}{'mixed%':>8}{'trunc%':>8}{'words':>7}")
    for name, pred in ARMS:
        s = arm_stats([r for r in rows if pred(r)])
        if s is None:
            print(f"{name:14}   —")
            continue
        print(f"{name:14}{s['n']:>4}{s['mean']:>7.2f}{s['median']:>8.2f}"
              f"{s['q1']:>6.2f}{s['q3']:>6.2f}{100 * s['flag_ai']:>6.0f}%"
              f"{100 * s['flag_human']:>7.0f}%"
              f"{100 * s['flag_mixed']:>7.0f}%"
              f"{100 * s['truncated']:>7.0f}%{s['mean_words']:>7.0f}")
    for q in PAIRED_QUARTERS:
        pr = paired(rows, period=q)
        if not pr:
            continue
        print(f"\npaired {q} (n={pr['pairs']}): AI PR scores higher in "
              f"{pr['wins']}/{pr['wins'] + pr['losses']} decided pairs "
              f"({pr['ties']} ties); mean gap {pr['mean_gap']:+.2f}; "
              f"one-sided sign test p={pr['sign_p']:.3f}")
        lm = paired(rows, period=q, max_word_gap=LENGTH_MATCH_WORDS)
        if lm:
            print(f"length-matched sensitivity (|Δwords| <= "
                  f"{LENGTH_MATCH_WORDS}): n={lm['pairs']}, "
                  f"{lm['wins']}/{lm['wins'] + lm['losses']} decided, "
                  f"mean gap {lm['mean_gap']:+.2f}, p={lm['sign_p']:.3f}")
    print(f"\nGPTZero model version(s): {versions or 'unknown'}")
    print()
    print(CAVEATS)
