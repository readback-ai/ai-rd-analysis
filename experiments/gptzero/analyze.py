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
- ENDPOINT (measured 2026-08-20). Scores here come from
  /v2/predict/FILES, which normalises uploads before scoring: only 4 of
  898 documents (0.4%) reached the model as sent, mean byte loss 13.6%,
  and just 15.9% of leading whitespace survives. /v2/predict/text is
  byte-faithful (96/96 exact) and is what the dashboard's Advanced Scan
  runs. Under THIS report's pinned model (2026-07-04-base) that
  normalisation is inert: a stratified 96-document re-score through the
  text endpoint produced 0/96 verdict flips, 89/96 bit-identical
  probabilities, and a maximum delta of 0.03 — so the numbers here are
  endpoint-independent. It is NOT inert on the newer 2026-08-09-base:
  openinference#3156 scores ai=0.096 on both endpoints under the
  pinned model but splits to files ai=0.023 vs text ai=0.596 under the
  newer one, i.e. the newer model is far more sensitive to indentation
  and the files endpoint destroys it. Any future run should use
  /v2/predict/text.
- The known-AI arm is canonical agent-authored (layer-B) PRs,
  Q4-2025..Q2-2026: as close to pure machine-written code as the study
  can sample. cursor/claude are pool-limited (21 and 9 eligible PRs
  exist); copilot/devin carry the arm. Its LOW scores mean the paired
  arms' elevation is NOT agent-style detection — document-level
  verdicts largely miss agent code.
- Near-uniform scores in ALL arms would itself be the answer: no signal
  on bare added-lines code.
- sem13c is the RELEASED LINEAR MIL COMPONENT of the T13c 1st-place
  system (paper: ~0.5906 macro-F1 standalone; 0.6331 with its
  unreleased CatBoost head; 0.7855 for the full unreleased ensemble)
  — transfer conclusions bind to the component alone. On this corpus
  it does not transfer: high false-positive rates on pre-ChatGPT
  code, an inverted era trend, null paired contrasts, and scores
  uncorrelated with GPTZero's; treat its verdicts here as
  uninformative."""


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


def sem_bound(rows: list[dict], sem_rows: list[dict],
              inference: str | None = None,
              revision: str | None = None) -> list[dict]:
    """sem13c rows bound to the CURRENT document per slot (append-only
    scoring log ages out redrawn docs here), one row per slot; rows
    scored under any other preprocessing (inference) or checkpoint
    (revision) are excluded when those identities are given — an older
    row must never mask the current one."""
    current = {r["slot"]: r["doc_sha"] for r in rows}
    out, seen = [], set()
    for r in sem_rows:
        if r["slot"] in seen:
            continue
        if inference is not None and r.get("inference") != inference:
            continue
        if revision is not None \
                and r.get("model_revision") != revision:
            continue
        if current.get(r["slot"]) == r["doc_sha"]:
            out.append(r)
            seen.add(r["slot"])
    return out


def report_sem(rows: list[dict], sem_rows: list[dict]) -> None:
    import sem13c
    bound = sem_bound(rows, sem_rows, inference=sem13c.INFERENCE,
                      revision=sem13c.HF_REVISION)
    if not bound:
        return
    for r in bound:
        r["aihyb"] = r["sem_probs"]["ai"] + r["sem_probs"]["hybrid"]
    print(f"\nsem13c (released linear MIL component of the T13c "
          f"1st-place system, ~0.59 standalone in-domain; 4-way code "
          f"classifier; {len(bound)}/{len(rows)} docs bound):")
    print(f"{'arm':14}{'n':>4}{'p_ai':>7}{'p_hyb':>7}{'p_adv':>7}"
          f"{'ai%':>6}{'hyb%':>6}{'adv%':>6}{'hum%':>6}")
    for name, pred in ARMS:
        rs = [r for r in bound if pred(r)]
        if not rs:
            continue
        n = len(rs)
        share = {c: sum(1 for r in rs if r["sem_pred"] == c) / n
                 for c in ("ai", "hybrid", "adversarial", "human")}
        print(f"{name:14}{n:>4}"
              f"{statistics.fmean(r['sem_probs']['ai'] for r in rs):>7.2f}"
              f"{statistics.fmean(r['sem_probs']['hybrid'] for r in rs):>7.2f}"
              f"{statistics.fmean(r['sem_probs']['adversarial'] for r in rs):>7.2f}"
              f"{100 * share['ai']:>5.0f}%{100 * share['hybrid']:>5.0f}%"
              f"{100 * share['adversarial']:>5.0f}%"
              f"{100 * share['human']:>5.0f}%")
    for q in PAIRED_QUARTERS:
        pr = paired_metric(bound, q, "aihyb")
        if pr:
            print(f"  paired {q} on p(ai)+p(hybrid): n={pr['pairs']}, "
                  f"{pr['wins']}/{pr['wins'] + pr['losses']} higher, "
                  f"mean gap {pr['mean_gap']:+.2f}, "
                  f"p={pr['sign_p']:.3f}")
    gz_by_slot = {r["slot"]: ai_prob(r) for r in rows
                  if ai_prob(r) is not None}
    pairs = [(gz_by_slot[r["slot"]], r["aihyb"]) for r in bound
             if r["slot"] in gz_by_slot]
    if len(pairs) >= 10:
        xs, ys = zip(*pairs)
        print(f"  agreement with GPTZero: corr(p_gz, p_ai+hyb) = "
              f"{statistics.correlation(xs, ys):+.2f} over "
              f"{len(pairs)} docs")


def report_newfile(nf_rows: list[dict], sem_cap: list[dict],
                   sem_full: list[dict],
                   gz_rows: list[dict]) -> None:
    """Created-file arm: whole-file documents under sem13c (capped and
    full variants — the domain-repair probe) and, when scored, GPTZero
    on the capped variant."""
    if not nf_rows:
        print("no newfile rows — run --newfile first")
        return
    by_cap = {r["slot"]: r for r in sem_cap}
    by_full = {r["slot"]: r for r in sem_full}
    by_gz = {r["slot"]: r for r in gz_rows}
    valid = {r["slot"]: r for r in nf_rows}
    print(f"created-file arm ({len(nf_rows)} whole-file documents, "
          f"largest created file per scored slot):")
    print(f"{'arm':14}{'n':>4}"
          f"{'sem-ai%':>9}{'semF-ai%':>10}{'semF-hyb%':>10}"
          f"{'gz-ai%':>8}{'gz-mean':>9}")
    for name, pred in ARMS:
        rs = [r for r in nf_rows if pred(r)]
        if not rs:
            continue
        n = len(rs)

        def share(scored, cls_key, pred_key):
            hits = [scored[r["slot"]] for r in rs
                    if r["slot"] in scored]
            if not hits:
                return None
            return (sum(1 for h in hits
                        if h[pred_key] == cls_key) / len(hits))

        sa = share(by_cap, "ai", "sem_pred")
        fa = share(by_full, "ai", "sem_pred")
        fh = share(by_full, "hybrid", "sem_pred")
        ga = share(by_gz, "ai", "predicted_class")
        gz_ps = [ai_prob(by_gz[r["slot"]]) for r in rs
                 if r["slot"] in by_gz
                 and ai_prob(by_gz[r["slot"]]) is not None]
        gm = statistics.fmean(gz_ps) if gz_ps else None

        def pct(v):
            return f"{100 * v:>.0f}%" if v is not None else "—"
        print(f"{name:14}{n:>4}{pct(sa):>9}{pct(fa):>10}{pct(fh):>10}"
              f"{pct(ga):>8}"
              f"{'—' if gm is None else format(gm, '.2f'):>9}")
    for label, sem in (("capped", sem_cap), ("full", sem_full)):
        rows = [{**valid[r["slot"]],
                 "aihyb": r["sem_probs"]["ai"] + r["sem_probs"]["hybrid"]}
                for r in sem if r["slot"] in valid]
        for q in PAIRED_QUARTERS:
            pr = paired_metric(rows, q, "aihyb")
            if pr:
                print(f"  sem13c-{label} paired {q}: n={pr['pairs']}, "
                      f"{pr['wins']}/{pr['wins'] + pr['losses']} "
                      f"higher, gap {pr['mean_gap']:+.2f}, "
                      f"p={pr['sign_p']:.3f}")


def endpoint_pairs(rows: list[dict], ep_rows: list[dict]) -> list[dict]:
    """Documents scored through BOTH endpoints under the same pinned
    model, paired on (slot, doc_sha) so only the endpoint differs."""
    files = {(r["slot"], r["doc_sha"]): r for r in rows}
    out = []
    for t in ep_rows:
        f = files.get((t["slot"], t["doc_sha"]))
        if f is None:
            continue
        pf, pt = ai_prob(f), ai_prob(t)
        if pf is None or pt is None:
            continue
        out.append({"stratum": t.get("stratum"), "slot": t["slot"],
                    "files_p": pf, "text_p": pt,
                    "files_class": f.get("predicted_class"),
                    "text_class": t.get("predicted_class")})
    return out


def report_endpoint(rows: list[dict], ep_rows: list[dict]) -> None:
    pairs = endpoint_pairs(rows, ep_rows)
    if not pairs:
        print("no endpoint rows — run --rescore-text first")
        return
    print(f"endpoint comparison, /v2/predict/files vs /v2/predict/text "
          f"(same pinned model; {len(pairs)} documents):")
    print(f"{'stratum':16}{'n':>4}{'files p':>9}{'text p':>9}{'Δ':>8}"
          f"{'flips':>8}{'→ai':>6}{'→human':>8}")
    order = sorted({p["stratum"] for p in pairs})
    for s in order + ["ALL"]:
        ps = pairs if s == "ALL" else [p for p in pairs
                                       if p["stratum"] == s]
        if not ps:
            continue
        d = [p["text_p"] - p["files_p"] for p in ps]
        flips = [p for p in ps
                 if p["files_class"] != p["text_class"]]
        to_ai = sum(1 for p in flips if p["text_class"] == "ai")
        to_hu = sum(1 for p in flips if p["text_class"] == "human")
        print(f"{s:16}{len(ps):>4}"
              f"{statistics.fmean(p['files_p'] for p in ps):>9.2f}"
              f"{statistics.fmean(p['text_p'] for p in ps):>9.2f}"
              f"{statistics.fmean(d):>+8.2f}"
              f"{len(flips):>5}/{len(ps):<2}{to_ai:>6}{to_hu:>8}")
    d = [p["text_p"] - p["files_p"] for p in pairs]
    wins = sum(1 for x in d if x > 0)
    losses = sum(1 for x in d if x < 0)
    print(f"  text scores higher in {wins}/{wins + losses} decided "
          f"documents; sign p={_sign_p(wins, wins + losses):.4f}")
    big = [p for p in pairs if abs(p["text_p"] - p["files_p"]) >= 0.5]
    print(f"  |Δ| >= 0.50 on {len(big)}/{len(pairs)} documents")


def ablation_stats(rows: list[dict], abl_rows: list[dict]) -> dict:
    """Within-document comment/code decomposition: each selected
    document's ORIGINAL score against its code-only and comments-only
    variants, grouped by era. Deltas are paired (same document), so
    the sign test needs no length matching."""
    orig = {r["slot"]: r for r in rows}
    by_slot: dict[str, dict] = {}
    for r in abl_rows:
        parent = orig.get(r["slot"])
        if parent is None or parent["doc_sha"] != r["parent_doc_sha"]:
            continue
        p = ai_prob(r)
        if p is None:
            continue
        e = by_slot.setdefault(r["slot"], {"group": r["group"],
                                           "orig": ai_prob(parent)})
        e[r["variant"]] = p
    out: dict[str, list] = {}
    for slot, e in by_slot.items():
        if "code" in e and "comment" in e and e["orig"] is not None:
            out.setdefault(e["group"], []).append(e)
    return out


def report_ablation(rows: list[dict], abl_rows: list[dict]) -> None:
    groups = ablation_stats(rows, abl_rows)
    if not groups:
        print("no ablation rows — run --ablate first")
        return
    print("comment/code ablation (within document; does prose carry "
          "the signal?):")
    print(f"{'group':12}{'n':>4}{'original':>10}{'code-only':>11}"
          f"{'comment-only':>14}{'Δ code':>9}{'p':>8}")
    for g in sorted(groups):
        es = groups[g]
        n = len(es)
        d = [e["code"] - e["orig"] for e in es]
        wins = sum(1 for x in d if x < 0)     # code-only scores LOWER
        losses = sum(1 for x in d if x > 0)
        print(f"{g:12}{n:>4}"
              f"{statistics.fmean(e['orig'] for e in es):>10.2f}"
              f"{statistics.fmean(e['code'] for e in es):>11.2f}"
              f"{statistics.fmean(e['comment'] for e in es):>14.2f}"
              f"{statistics.fmean(d):>+9.2f}"
              f"{_sign_p(wins, wins + losses):>8.3f}")
    if len(groups) == 2 and "baseline" in groups:
        modern = [g for g in groups if g != "baseline"][0]
        for key, label in (("orig", "original"), ("code", "code-only"),
                           ("comment", "comment-only")):
            b = statistics.fmean(e[key] for e in groups["baseline"])
            m = statistics.fmean(e[key] for e in groups[modern])
            print(f"  era gap ({modern} - baseline) on {label:13}: "
                  f"{m - b:+.2f}")


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
           paragraphs_path: Path | None = None,
           sem_path: Path | None = None) -> None:
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
    if sem_path is not None:
        report_sem(rows, load_rows(sem_path))
    print(f"\nGPTZero model version(s): {versions or 'unknown'}")
    print()
    print(CAVEATS)
