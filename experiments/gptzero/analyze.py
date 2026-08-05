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
        ("Q2-26-nonAI", _p("Q2-2026", False)),
        ("known-AI", lambda r: r["arm"] == "PC"))

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
- Q2-2026 is NOT a full quarter: w8 maturity at AS_OF 2026-08-01
  admits PRs created 2026-04-01..2026-06-06; June 7-30 stays
  unmeasured until a later AS_OF matures it. Do not read Q2-2026
  numbers as quarter-complete.
- Draws are whole-pool shuffles, so an AS_OF advance redraws cohorts
  almost completely (the August Q2-2026 draw shares 3/90 authors with
  July's): July-vs-August contrasts are two nearly-independent
  samples, consistent with frame bias but NOT a within-cohort
  correction. Stable per-author ranks are a v3 design item.
- The paired arm is A-and-C-heavy: layer-B (bot-login agent) PRs cannot
  anchor a human-paired design and are absent.
- Truncated documents measure a diff's head only (share reported above).
- Documents span 100-600 words and GPTZero's accuracy rises with
  length; the length-matched sensitivity bounds that confound — trust
  the headline pairing only where the two agree.
- Q3-2022-era predates ChatGPT: its positives are near-pure FALSE
  positives (early-Codex/Copilot-autocomplete volume was tiny) — the
  cleanest false-positive calibration in the design.
- The known-AI arm is canonical agent-authored (layer-B) PRs,
  Q4-2025..Q2-2026: as close to pure machine-written code as the study
  can sample. cursor/claude are pool-limited (21 and 9 eligible PRs
  exist); copilot/devin carry the arm. Its LOW scores mean the paired
  arms' elevation is NOT agent-style detection — document-level
  verdicts largely miss agent code.
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


RETEST_GROUPS = (("paired-AI", lambda r: r["arm"] == "P" and r["ai"]),
                 ("paired-nonAI",
                  lambda r: r["arm"] == "P" and not r["ai"]),
                 ("baselines",
                  lambda r: r["arm"] in ("B1", "B2", "B3")))


def _sign_p(wins: int, n: int) -> float:
    return (sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n
            if n else float("nan"))


def retest_stats(rows: list[dict], retest_rows: list[dict],
                 pred) -> dict | None:
    """Dose-response over slots scored at BOTH caps: delta = long-cap
    score minus design-cap score per document, one-sided sign test for
    'longer scores higher', and predicted-class flips. Pairs bind by
    slot AND the design-cap doc_sha the retest row was built from, so a
    redrawn document never pairs across assemblies."""
    v1 = {r["slot"]: r for r in rows if pred(r)}
    pairs = []
    for rt in retest_rows:
        v = v1.get(rt["slot"])
        if v is None or v["doc_sha"] != rt.get("sha600"):
            continue
        p0, p1 = ai_prob(v), ai_prob(rt)
        if p0 is None or p1 is None:
            continue
        pairs.append((p0, p1, v.get("predicted_class"),
                      rt.get("predicted_class")))
    if not pairs:
        return None
    deltas = [p1 - p0 for p0, p1, _c0, _c1 in pairs]
    wins = sum(1 for d in deltas if d > 0)
    losses = sum(1 for d in deltas if d < 0)
    flips: dict[str, int] = {}
    for _p0, _p1, c0, c1 in pairs:
        if c0 != c1:
            key = f"{c0}->{c1}"
            flips[key] = flips.get(key, 0) + 1
    return {"n": len(pairs),
            "mean0": statistics.fmean(p for p, _1, _c0, _c1 in pairs),
            "mean1": statistics.fmean(p for _0, p, _c0, _c1 in pairs),
            "mean_delta": statistics.fmean(deltas),
            "wins": wins, "losses": losses,
            "sign_p": _sign_p(wins, wins + losses), "flips": flips}


def report_retest(rows: list[dict], retest_rows: list[dict]) -> None:
    cap = max((r.get("word_cap", 0) for r in retest_rows), default=0)
    v1 = {r["slot"]: r for r in rows}
    bound = [rt for rt in retest_rows
             if v1.get(rt["slot"], {}).get("doc_sha") == rt.get("sha600")]
    truncated_now = sum(1 for r in rows if r.get("truncated"))
    print(f"\nretest @{cap} (documents truncated at the design cap; "
          f"delta = score@{cap} - score@design-cap):")
    print(f"coverage: {len(bound)}/{truncated_now} currently-truncated "
          f"scored documents — the stage-1 sensitivity subset (every "
          f"document truncated when the retest ran; rows detached by "
          f"later redraws are excluded)")
    print(f"{'group':14}{'n':>4}{'mean@600':>10}{'mean@'+str(cap):>11}"
          f"{'Δmean':>8}{'higher':>9}{'sign_p':>8}  flips")
    for name, pred in RETEST_GROUPS:
        s = retest_stats(rows, retest_rows, pred)
        if s is None:
            print(f"{name:14}   —")
            continue
        flips = ", ".join(f"{k} {v}" for k, v in
                          sorted(s["flips"].items())) or "none"
        print(f"{name:14}{s['n']:>4}{s['mean0']:>10.2f}{s['mean1']:>11.2f}"
              f"{s['mean_delta']:>+8.2f}"
              f"{s['wins']:>6}/{s['wins'] + s['losses']:<2}"
              f"{s['sign_p']:>8.3f}  {flips}")
    still = sum(1 for r in bound if r.get("truncated"))
    print(f"still truncated at {cap}: {still}/{len(bound)}")


def paired_metric(rows: list[dict], period: str, key: str) \
        -> dict | None:
    """Within-author paired contrast on an arbitrary per-document
    metric (the pre-specified secondary outcomes: max_paragraph_prob,
    share_paragraphs_gt50). Same wins/sign-test convention as
    paired()."""
    by_author: dict = {}
    for r in rows:
        if r.get("arm") == "P" and r.get("period") == period \
                and r.get("author") and r.get(key) is not None:
            by_author.setdefault(r["author"], {})[
                "ai" if r["ai"] else "nonai"] = r[key]
    gaps = [v["ai"] - v["nonai"] for v in by_author.values()
            if "ai" in v and "nonai" in v]
    if not gaps:
        return None
    wins = sum(1 for g in gaps if g > 0)
    losses = sum(1 for g in gaps if g < 0)
    return {"pairs": len(gaps), "wins": wins, "losses": losses,
            "mean_gap": statistics.fmean(gaps),
            "sign_p": _sign_p(wins, wins + losses)}


def mixture_stats(rows: list[dict]) -> dict | None:
    """RELATIVE score level per paired arm: where each arm's mean sits
    between the baseline mean (0) and the Q4-2025 marked-arm mean (1),
    clamped. These are anchor-relative units, NOT identifiable
    prevalence — the anchor is itself a mixture of unknown purity, and
    an impure anchor shrinks the denominator, INFLATING the ratio
    relative to a pure-AI endpoint. Read as 'how saturated is this arm
    against the Q4-2025 marked level', nothing more."""
    def mean_of(pred):
        ps = [ai_prob(r) for r in rows
              if pred(r) and ai_prob(r) is not None]
        return statistics.fmean(ps) if ps else None
    anchor = mean_of(lambda r: r["arm"] == "P"
                     and r["period"] == "Q4-2025" and r["ai"])
    human = mean_of(lambda r: r["arm"] in ("B1", "B2", "B3"))
    if anchor is None or human is None or anchor <= human:
        return None
    arms = []
    for q in PAIRED_QUARTERS:
        for ai in (True, False):
            m = mean_of(lambda r, q=q, ai=ai: r["arm"] == "P"
                        and r["period"] == q and r["ai"] == ai)
            if m is None:
                continue
            pi = min(max((m - human) / (anchor - human), 0.0), 1.0)
            arms.append({"arm": f"{q} {'AI' if ai else 'nonAI'}",
                         "mean": m, "pi": pi})
    return {"anchor": anchor, "human": human, "arms": arms}


def report_mixture(rows: list[dict]) -> None:
    s = mixture_stats(rows)
    if s is None:
        return
    print(f"\nrelative score level (0 = baselines mean {s['human']:.2f},"
          f" 1 = Q4-2025 marked mean {s['anchor']:.2f}; anchor-relative"
          f" units, NOT identifiable prevalence):")
    for a in s["arms"]:
        print(f"  {a['arm']:14} mean {a['mean']:.2f}  "
              f"level {a['pi']:.2f}")


def report_paragraph_paired(para_rows: list[dict]) -> None:
    lines = []
    for q in PAIRED_QUARTERS:
        for key, label in (("max_paragraph_prob", "max-para"),
                           ("share_paragraphs_gt50", "share>0.5")):
            pr = paired_metric(para_rows, q, key)
            if pr:
                lines.append(
                    f"  {q} {label:10} n={pr['pairs']:<3} "
                    f"{pr['wins']}/{pr['wins'] + pr['losses']} higher, "
                    f"mean gap {pr['mean_gap']:+.2f}, "
                    f"p={pr['sign_p']:.3f}")
    if lines:
        print("\nparagraph-metric paired contrasts (pre-specified "
              "secondary outcomes):")
        print("\n".join(lines))


def report_languages(para_rows: list[dict], top: int = 6) -> None:
    from collections import Counter
    p_rows = [r for r in para_rows
              if r["arm"] == "P" and r.get("dominant_ext")
              and r.get("ai_prob") is not None]
    if not p_rows:
        return
    exts = [e for e, _n in Counter(
        r["dominant_ext"] for r in p_rows).most_common(top)]
    print("\nby dominant extension (paired arms pooled over quarters):")
    print(f"{'ext':10}{'n-AI':>6}{'mean-AI':>9}{'n-non':>7}"
          f"{'mean-non':>10}")
    for ext in exts:
        ai_ps = [r["ai_prob"] for r in p_rows
                 if r["dominant_ext"] == ext and r["ai"]]
        no_ps = [r["ai_prob"] for r in p_rows
                 if r["dominant_ext"] == ext and not r["ai"]]
        print(f"{ext:10}{len(ai_ps):>6}"
              f"{statistics.fmean(ai_ps) if ai_ps else float('nan'):>9.2f}"
              f"{len(no_ps):>7}"
              f"{statistics.fmean(no_ps) if no_ps else float('nan'):>10.2f}")


def paragraph_stats(para_rows: list[dict]) -> dict | None:
    """Aggregates over per-document paragraph summaries (frozen beside
    the scores): the document verdict discards within-document
    heterogeneity, so 'some but not all paragraphs above 0.5' is the
    auditable footprint of possible mixed authorship."""
    rows = [r for r in para_rows
            if r.get("n_paragraphs") and r.get("mixed_prob") is not None]
    if not rows:
        return None
    any_hi = sum(1 for r in rows if r["share_paragraphs_gt50"] > 0)
    partial = sum(1 for r in rows
                  if 0 < r["share_paragraphs_gt50"] < 1)
    return {"n": len(rows), "any_hi": any_hi, "partial": partial,
            "mean_mixed_prob":
                statistics.fmean(r["mixed_prob"] for r in rows)}


def report_paragraphs(para_rows: list[dict]) -> None:
    s = paragraph_stats(para_rows)
    if s is None:
        return
    print("\nparagraph-level (from cached responses; the document "
          "verdict discards this):")
    print(f"docs {s['n']}; any paragraph >0.5: {s['any_hi']} "
          f"({100 * s['any_hi'] / s['n']:.0f}%); some-but-not-all "
          f"paragraphs >0.5: {s['partial']} "
          f"({100 * s['partial'] / s['n']:.0f}%); mean mixed-class "
          f"prob {s['mean_mixed_prob']:.3f}")
    print(f"{'group':14}{'n':>4}{'mean max-para':>15}"
          f"{'mean share>0.5':>16}")
    for name, pred in RETEST_GROUPS:
        rs = [r for r in para_rows if r.get("n_paragraphs") and pred(r)]
        if not rs:
            continue
        print(f"{name:14}{len(rs):>4}"
              f"{statistics.fmean(r['max_paragraph_prob'] for r in rs):>15.2f}"
              f"{statistics.fmean(r['share_paragraphs_gt50'] for r in rs):>16.2f}")


def report(results_path: Path,
           retest_path: Path | None = None,
           paragraphs_path: Path | None = None) -> None:
    rows = load_rows(results_path)
    if not rows:
        print(f"no results at {results_path} — run --score first")
        return
    retest_rows = (load_rows(retest_path) if retest_path is not None
                   else [])
    versions = sorted({r.get("model_version") or "unknown"
                       for r in rows + retest_rows})
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
    report_mixture(rows)
    if retest_rows:
        report_retest(rows, retest_rows)
    if paragraphs_path is not None:
        para_rows = load_rows(paragraphs_path)
        report_paragraphs(para_rows)
        report_paragraph_paired(para_rows)
        report_languages(para_rows)
    print(f"\nGPTZero model version(s): {versions or 'unknown'}")
    print()
    print(CAVEATS)
