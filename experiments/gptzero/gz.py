"""CLI for the GPTZero code-diff calibration (design v1-50k).

  python experiments/gptzero/gz.py --sample          # manifest + pool sizes
  python experiments/gptzero/gz.py --fetch           # diffs -> documents
  python experiments/gptzero/gz.py --score [--limit N]
  python experiments/gptzero/gz.py                   # analysis report

Everything data-shaped lives under experiments/gptzero/local/
(gitignored): manifest, document metadata, diff/document/response
caches, and the results JSONL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
from pathlib import Path

SCORE_PACE = 4.0   # seconds between billed requests: rapid-fire POSTs
                   # trip the API edge's behavioral bot rules

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE.parents[1] / "src"))

LOCAL = BASE / "local"
MANIFEST = LOCAL / "manifest_v1_50k.json"
MANIFEST_B3 = LOCAL / "manifest_b3.json"
MANIFEST_ERAS = LOCAL / "manifest_eras.json"
MANIFEST_PC = LOCAL / "manifest_pc.json"
B3_PAGES = LOCAL / "cache" / "q3_2022_pages"
DOCS = LOCAL / "docs_v1.jsonl"
DOCS_RETEST = LOCAL / "docs_retest.jsonl"
RESULTS = LOCAL / "results" / "scores_v1.jsonl"
RESULTS_RETEST = LOCAL / "results" / "scores_retest.jsonl"
RESULTS_SEM = LOCAL / "results" / "scores_sem13c.jsonl"
RETEST_CAP = 1200   # dose-response stage: docs truncated at the design
                    # cap are re-assembled and re-scored at this cap
RESERVATIONS = LOCAL / "results" / "reservations_v1.jsonl"
DIFF_CACHE = LOCAL / "cache" / "diffs"
DOC_CACHE = LOCAL / "cache" / "docs"
RESP_CACHE = LOCAL / "cache" / "responses"


def cmd_sample() -> None:
    import sampling
    pools_ = sampling.pools()
    mixed = sorted(a for a, v in pools_["q2"].items()
                   if v["ai"] and v["nonai"])
    manifest, rewrote = sampling.ensure_manifest(pools_, MANIFEST)
    slots = manifest["slots"]
    by_arm = {a: sum(1 for s in slots if s["arm"] == a)
              for a in ("P", "B1", "B2")}
    print(f"pool: {len(pools_['q2'])} eligible Q2-2026 authors, "
          f"{len(mixed)} mixed (both arms); "
          f"{len(pools_['q1'])} eligible Q1-2024 authors")
    if len(mixed) < sampling.PARAMS["n_authors"]:
        print(f"NOTE: only {len(mixed)} mixed authors < "
              f"{sampling.PARAMS['n_authors']} target — using all")
    print(f"manifest {'rewritten' if rewrote else 'unchanged'}: "
          f"{len(slots)} slots (P={by_arm['P']}, B1={by_arm['B1']}, "
          f"B2={by_arm['B2']}), fingerprint {manifest['fingerprint']}")


def cmd_sample_b3() -> None:
    import b3
    pool = b3.repo_pool(BASE.parents[1]
                        / "data" / "derived" / "population_repos.txt")
    print(f"B3 pool: {len(pool)} repos with >= "
          f"{b3.B3_PARAMS['min_repo_prs']} Q3-2022 PRs")
    ranked = b3.draw_repos(pool)
    pages = {}
    for repo in ranked:
        page = b3.fetch_page(repo, B3_PAGES)
        if page is None:
            print(f"PAGE FAIL {repo} (spare will stand in)", flush=True)
            continue
        pages[repo] = page
    manifest, rewrote = b3.ensure_manifest(pool, pages, MANIFEST_B3)
    print(f"B3 manifest {'rewritten' if rewrote else 'unchanged'}: "
          f"{len(manifest['slots'])} slots, "
          f"fingerprint {manifest['fingerprint']}")


def cmd_sample_eras() -> None:
    import eras
    if not MANIFEST.is_file():
        raise SystemExit("v1 manifest required first (--sample): the "
                         "Q2-2026 expansion excludes its authors")
    v1_authors = {s["author"]
                  for s in json.loads(MANIFEST.read_text())["slots"]
                  if s["arm"] == "P"}
    exclude = {"Q2-2026": v1_authors}
    pools_ = eras.pools()
    manifest, rewrote = eras.ensure_manifest(pools_, MANIFEST_ERAS,
                                             exclude)
    slots = manifest["slots"]
    for q in eras.QUARTERS:
        mixed = sum(1 for a, v in pools_[q].items()
                    if v["ai"] and v["nonai"])
        n = sum(1 for s in slots if s["period"] == q)
        print(f"{q}: {len(pools_[q])} eligible authors, {mixed} mixed "
              f"(both arms) -> {n} slots"
              + (f" (+{len(v1_authors)} v1 authors)"
                 if q == "Q2-2026" else ""))
        if mixed < eras.PARAMS["n_authors"]:
            print(f"NOTE: only {mixed} mixed authors < "
                  f"{eras.PARAMS['n_authors']} target — using all")
    print(f"eras manifest {'rewritten' if rewrote else 'unchanged'}: "
          f"{len(slots)} slots, fingerprint {manifest['fingerprint']}")


def cmd_sample_pc() -> None:
    import pc
    pools_ = pc.pools()
    manifest, rewrote = pc.ensure_manifest(pools_, MANIFEST_PC)
    slots = manifest["slots"]
    for q in pc.QUARTERS:
        n = sum(1 for s in slots if s["period"] == q)
        logins = {s["author"] for s in slots if s["period"] == q}
        print(f"{q}: {len(pools_[q])} (agent, repo) groups -> {n} "
              f"slots across {len(logins)} agent logins")
    print(f"pc manifest {'rewritten' if rewrote else 'unchanged'}: "
          f"{len(slots)} slots, fingerprint {manifest['fingerprint']}")


def _manifests() -> list[dict]:
    return [json.loads(p.read_text())
            for p in (MANIFEST, MANIFEST_B3, MANIFEST_ERAS, MANIFEST_PC)
            if p.is_file()]


def _slot_index(manifests: list[dict]) -> tuple[list[dict], dict]:
    """(all slot defs, slot -> (fingerprint, word_cap, word_floor))."""
    slots, meta = [], {}
    for m in manifests:
        for s in m["slots"]:
            slots.append(s)
            meta[s["slot"]] = (m["fingerprint"],
                               m["params"]["word_cap"],
                               m["params"]["word_floor"])
    return slots, meta


def _doc_rows() -> dict[str, dict]:
    if not DOCS.is_file():
        return {}
    rows = [json.loads(ln) for ln in DOCS.read_text().splitlines()
            if ln.strip()]
    return {r["slot"]: r for r in rows}


def cmd_fetch() -> None:
    import diffs
    slots, meta_of = _slot_index(_manifests())
    # A row is a valid checkpoint only if it is FILLED, its chosen PR is
    # still among its slot's candidates (a redraw invalidates rows), AND
    # it was assembled under the current rules — cap, floor, and the
    # assembly version — else it is rebuilt from the cached diff (a pure
    # k_cand deepening retains everything). Unfilled slots are retried
    # every run.
    cands_of = {s["slot"]: {(c[0], int(c[1])) for c in s["candidates"]}
                for s in slots}
    filled = {}
    for s, r in _doc_rows().items():
        fp, cap, floor = meta_of.get(s, (None, None, None))
        if not r.get("unfilled") \
                and (r["repo"], r["num"]) in cands_of.get(s, set()) \
                and r.get("word_cap") == cap \
                and r.get("word_floor") == floor \
                and r.get("assembly") == diffs.ASSEMBLY:
            filled[s] = r
    LOCAL.mkdir(parents=True, exist_ok=True)
    with DOCS.open("w") as out:
        for s, r in filled.items():
            out.write(json.dumps(
                {**r, "fingerprint": meta_of[s][0]}) + "\n")
        for slot in slots:
            if slot["slot"] in filled:
                continue
            fp, cap, floor = meta_of[slot["slot"]]
            row = None
            for repo, num, loc in slot["candidates"]:
                raw = diffs.fetch_diff(repo, int(num), DIFF_CACHE)
                if raw is None:
                    print(f"FETCH FAIL {repo}#{num} "
                          f"(slot {slot['slot']})", flush=True)
                    continue
                text, meta = diffs.build_document(
                    diffs.parse_diff(raw), cap, floor)
                if text is None:
                    continue                 # floor miss: next candidate
                sha = hashlib.sha256(text.encode()).hexdigest()
                DOC_CACHE.mkdir(parents=True, exist_ok=True)
                (DOC_CACHE / f"{sha}.txt").write_text(text)
                row = {**{k: slot[k] for k in
                          ("slot", "arm", "author", "period", "ai")},
                       "repo": repo, "num": int(num), "loc": int(loc),
                       "doc_sha": sha, "fingerprint": fp,
                       "word_cap": cap, "word_floor": floor,
                       "assembly": diffs.ASSEMBLY, **meta}
                break
            if row is None:
                row = {**{k: slot[k] for k in
                          ("slot", "arm", "author", "period", "ai")},
                       "unfilled": True, "fingerprint": fp}
                print(f"UNFILLED slot {slot['slot']} (no candidate "
                      f"cleared the floor)", flush=True)
            out.write(json.dumps(row) + "\n")
            out.flush()
    rows = _doc_rows().values()
    filled_rows = [r for r in rows if not r.get("unfilled")]
    unfilled: dict[str, int] = {}
    for r in rows:
        if r.get("unfilled"):
            key = (f"P:{'ai' if r.get('ai') else 'nonai'}"
                   if r["arm"] == "P" else r["arm"])
            unfilled[key] = unfilled.get(key, 0) + 1
    print(f"documents: {len(filled_rows)} filled, "
          f"{len(rows) - len(filled_rows)} unfilled"
          f"{' ' + str(unfilled) if unfilled else ''}; "
          f"{sum(r['words'] for r in filled_rows)} words assembled")


def _batches(rows: list[dict]) -> list[list[dict]]:
    """Split scoring work into batches under BOTH request limits: file
    count (API cap) and total words (bigger uploads time out inside the
    API). An overweight single document still ships alone."""
    import gptzero_client as gzc
    out: list[list[dict]] = []
    cur: list[dict] = []
    words = 0
    for r in rows:
        if cur and (len(cur) >= gzc.BATCH_FILES
                    or words + r["words"] > gzc.BATCH_WORDS):
            out.append(cur)
            cur, words = [], 0
        cur.append(r)
        words += r["words"]
    if cur:
        out.append(cur)
    return out


def cmd_score(limit: int | None) -> None:
    import gptzero_client as gzc
    _, meta_of = _slot_index(_manifests())
    if gzc.PINNED_VERSION is None and limit is None:
        raise SystemExit(
            "full run requires a pinned detector version: smoke first "
            "(--score --limit 2), set gptzero_client.PINNED_VERSION to "
            "the version the responses report, then re-run --score")
    docs = {r["slot"]: r for r in _doc_rows().values()
            if not r.get("unfilled")}
    stale = [r["slot"] for r in docs.values()
             if r.get("fingerprint")
             != meta_of.get(r["slot"], (None,))[0]]
    if stale:
        raise SystemExit(
            f"{len(stale)} document rows predate the current "
            f"manifest(s) — run --fetch first")
    old = []
    if RESULTS.is_file():
        old = [json.loads(ln)
               for ln in RESULTS.read_text().splitlines() if ln.strip()]
    # A result binds to the document its slot CURRENTLY selects AND to
    # the pinned detector version: after a redraw changes a slot's
    # doc_sha, or once a pin is set, rows scored otherwise are dropped
    # and rescored (the response cache makes a same-version re-key
    # free). Rows for slots no longer in the manifest drop the same way.
    valid = [r for r in old
             if docs.get(r["slot"], {}).get("doc_sha") == r["doc_sha"]
             and (gzc.PINNED_VERSION is None
                  or r.get("model_version") == gzc.PINNED_VERSION)]
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS.open("w") as out:
        for r in valid:
            out.write(json.dumps(r) + "\n")
        done = {r["slot"] for r in valid}
        todo = [r for s, r in docs.items() if s not in done]
        if limit is not None:
            todo = todo[:limit]
        batches = _batches(todo)
        for i, chunk in enumerate(batches):
            items = [(r["doc_sha"], DOC_CACHE / f"{r['doc_sha']}.txt")
                     for r in chunk]
            try:
                scored = gzc.score_batch(items, RESP_CACHE, RESERVATIONS)
            except RuntimeError as e:
                print(f"BATCH FAIL: {e}", flush=True)
                continue          # deferred: absent from results, retried
            except urllib.error.HTTPError as e:
                raise SystemExit(
                    f"HTTP {e.code} on a batch — results so far are "
                    f"recorded; re-run --score to resume. If it "
                    f"persists, check the key.") from e
            for r, (resp, billed) in zip(chunk, scored):
                fields = gzc.doc_fields(resp)
                out.write(json.dumps(
                    {**r, **fields, "billed_words": billed}) + "\n")
                out.flush()
                print(f"scored {r['slot']}: {fields['predicted_class']} "
                      f"({billed} words billed)", flush=True)
            if i + 1 < len(batches):
                time.sleep(SCORE_PACE)
    print(f"reserved: {gzc.ledger(RESERVATIONS)}/{gzc.BUDGET_WORDS} "
          f"words")


def cmd_retest() -> None:
    """Dose-response stage: every scored document that was truncated at
    its design cap is re-assembled from the cached diff at RETEST_CAP
    and re-scored into RESULTS_RETEST. scores_v1 rows stay untouched —
    the analysis pairs the two scores per slot to measure what document
    length does to the detector."""
    import diffs
    import gptzero_client as gzc
    if gzc.PINNED_VERSION is None:
        raise SystemExit("retest requires a pinned detector version")
    scored = {r["slot"]: r for r in
              (json.loads(ln) for ln in
               RESULTS.read_text().splitlines() if ln.strip())}
    targets = [r for r in _doc_rows().values()
               if not r.get("unfilled") and r.get("truncated")
               and r["slot"] in scored
               and scored[r["slot"]]["doc_sha"] == r["doc_sha"]]
    rows = []
    for r in targets:
        raw = diffs.fetch_diff(r["repo"], r["num"], DIFF_CACHE)
        if raw is None:
            print(f"FETCH FAIL {r['repo']}#{r['num']} "
                  f"(slot {r['slot']})", flush=True)
            continue
        text, meta = diffs.build_document(
            diffs.parse_diff(raw), RETEST_CAP, r["word_floor"])
        if text is None:
            continue
        sha = hashlib.sha256(text.encode()).hexdigest()
        DOC_CACHE.mkdir(parents=True, exist_ok=True)
        (DOC_CACHE / f"{sha}.txt").write_text(text)
        rows.append({**{k: r[k] for k in
                        ("slot", "arm", "author", "period", "ai",
                         "repo", "num")},
                     "sha600": r["doc_sha"], "doc_sha": sha,
                     "word_cap": RETEST_CAP, **meta})
    DOCS_RETEST.write_text("".join(json.dumps(r) + "\n" for r in rows))
    by_slot = {r["slot"]: r for r in rows}
    old = []
    if RESULTS_RETEST.is_file():
        old = [json.loads(ln) for ln in
               RESULTS_RETEST.read_text().splitlines() if ln.strip()]
    valid = [r for r in old
             if by_slot.get(r["slot"], {}).get("doc_sha") == r["doc_sha"]
             and r.get("model_version") == gzc.PINNED_VERSION]
    RESULTS_RETEST.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_RETEST.open("w") as out:
        for r in valid:
            out.write(json.dumps(r) + "\n")
        done = {r["slot"] for r in valid}
        todo = [r for r in rows if r["slot"] not in done]
        batches = _batches(todo)
        for i, chunk in enumerate(batches):
            items = [(r["doc_sha"], DOC_CACHE / f"{r['doc_sha']}.txt")
                     for r in chunk]
            try:
                scored_batch = gzc.score_batch(items, RESP_CACHE,
                                               RESERVATIONS)
            except RuntimeError as e:
                print(f"BATCH FAIL: {e}", flush=True)
                continue
            except urllib.error.HTTPError as e:
                raise SystemExit(
                    f"HTTP {e.code} on a batch — results so far are "
                    f"recorded; re-run --retest to resume.") from e
            for r, (resp, billed) in zip(chunk, scored_batch):
                fields = gzc.doc_fields(resp)
                out.write(json.dumps(
                    {**r, **fields, "billed_words": billed}) + "\n")
                out.flush()
                print(f"retested {r['slot']}: "
                      f"{fields['predicted_class']} "
                      f"({billed} words billed)", flush=True)
            if i + 1 < len(batches):
                time.sleep(SCORE_PACE)
    print(f"reserved: {gzc.ledger(RESERVATIONS)}/{gzc.BUDGET_WORDS} "
          f"words")


FROZEN = BASE / "frozen"
PARAGRAPHS = LOCAL / "paragraph_summary.jsonl"


def cmd_score_sem() -> None:
    """Score every filled document with the SemEval-13c MIL-UniXcoder
    detector (local, free, pinned revision); append-only results,
    resumable. The report and freeze bind rows to the CURRENT document
    per slot, so redraws age out old rows harmlessly."""
    import sem13c
    filled = [r for r in _doc_rows().values() if not r.get("unfilled")]
    n = sem13c.score_rows(filled, DOC_CACHE, RESULTS_SEM)
    print(f"sem13c: {n} newly scored, corpus {len(filled)} docs")


def _load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines()
            if ln.strip()]


def _validate_freeze(manifest_slots: list[str], docs_rows: list[dict],
                     score_rows: list[dict], retest_docs: list[dict],
                     retest_rows: list[dict]) -> None:
    """The frozen set must be internally coherent: manifest slot
    definitions and document slots are unique, and cover each other
    exactly; every score row is the slot's current document; every
    filled document is scored; and retest document and score rows are
    unique PER SLOT in each file and bind one-to-one on (slot, sha600,
    doc_sha) to a current score."""
    from collections import Counter
    errors = []
    manifest_counts = Counter(manifest_slots)
    for slot, n in sorted(manifest_counts.items()):
        if n > 1:
            errors.append(f"duplicate manifest slot definition: {slot}")
    doc_slot_counts = Counter(r["slot"] for r in docs_rows)
    for slot, n in sorted(doc_slot_counts.items()):
        if n > 1:
            errors.append(f"duplicate document row: {slot}")
    only_manifest = sorted(set(manifest_counts) - set(doc_slot_counts))
    only_docs = sorted(set(doc_slot_counts) - set(manifest_counts))
    if only_manifest:
        errors.append(f"{len(only_manifest)} manifest slots without "
                      f"document rows: {only_manifest[:5]}")
    if only_docs:
        errors.append(f"{len(only_docs)} document rows not in any "
                      f"manifest: {only_docs[:5]}")
    filled = {r["slot"]: r for r in docs_rows if not r.get("unfilled")}
    seen: set[str] = set()
    scored: dict[str, dict] = {}
    for r in score_rows:
        if r["slot"] in seen:
            errors.append(f"duplicate slot in scores: {r['slot']}")
        seen.add(r["slot"])
        scored[r["slot"]] = r
        d = filled.get(r["slot"])
        if d is None or d["doc_sha"] != r["doc_sha"]:
            errors.append(f"score row doc_sha not the slot's current "
                          f"document: {r['slot']}")
    unscored = sorted(set(filled) - set(scored))
    if unscored:
        errors.append(f"{len(unscored)} filled documents unscored: "
                      f"{unscored[:5]}")

    def binding(rows: list[dict], kind: str) -> dict[str, tuple]:
        counts = Counter(rt["slot"] for rt in rows)
        for slot, n in sorted(counts.items()):
            if n > 1:
                errors.append(f"duplicate slot in retest {kind}: {slot}")
        mapping = {rt["slot"]: (rt.get("sha600"), rt["doc_sha"])
                   for rt in rows}
        for slot, (sha600, _long) in sorted(mapping.items()):
            v = scored.get(slot)
            if v is None or v["doc_sha"] != sha600:
                errors.append(f"retest {kind} row detached from "
                              f"current score: {slot}")
        return mapping
    doc_map = binding(retest_docs, "documents")
    score_map = binding(retest_rows, "scores")
    if doc_map != score_map:
        odd = sorted(set(doc_map.items()) ^ set(score_map.items()))
        errors.append(f"retest documents and scores not one-to-one: "
                      f"{[slot for slot, _m in odd][:5]}")
    if errors:
        raise SystemExit("freeze refused:\n  " + "\n  ".join(errors))


def _dominant_ext(text: str) -> str | None:
    """Most common file extension among the document's `// file:`
    headers — the language-stratification key."""
    from collections import Counter
    exts: Counter = Counter()
    for line in text.splitlines():
        if line.startswith("// file: "):
            name = line[len("// file: "):].strip().rsplit("/", 1)[-1]
            dot = name.rfind(".")
            exts[name[dot:] if dot > 0 else "(none)"] += 1
    return exts.most_common(1)[0][0] if exts else None


def _paragraph_summaries(score_rows: list[dict]) -> list[dict]:
    """Privacy-safe per-document metrics from the cached responses and
    document texts, so the heterogeneity, paired-secondary-outcome, and
    language-stratification claims are auditable from the frozen set.
    A scored document missing its cached response or its document text
    is a validation error."""
    import gptzero_client as gzc
    out = []
    for r in score_rows:
        cached = gzc._cache_path(RESP_CACHE, r["doc_sha"])
        if not cached.is_file():
            raise SystemExit(f"freeze refused: scored document missing "
                             f"cached response: {r['slot']}")
        doc_txt = DOC_CACHE / f"{r['doc_sha']}.txt"
        if not doc_txt.is_file():
            raise SystemExit(f"freeze refused: scored document missing "
                             f"document text: {r['slot']}")
        d = (json.loads(cached.read_text()).get("documents") or [{}])[0]
        paras = [p.get("completely_generated_prob", 0.0)
                 for p in (d.get("paragraphs") or [])]
        probs = r.get("class_probabilities") or {}
        out.append({
            "slot": r["slot"], "arm": r["arm"], "period": r["period"],
            "ai": r["ai"], "author": r.get("author"),
            "doc_sha": r["doc_sha"],
            "predicted_class": r.get("predicted_class"),
            "ai_prob": probs.get("ai"),
            "dominant_ext": _dominant_ext(doc_txt.read_text()),
            "n_paragraphs": len(paras),
            "max_paragraph_prob": max(paras, default=None),
            "share_paragraphs_gt50":
                (sum(1 for p in paras if p > 0.5) / len(paras))
                if paras else None,
            "mixed_prob": probs.get("mixed")})
    return out


def cmd_freeze() -> None:
    """Validate then snapshot the audit set — manifests, document
    metadata rows, score rows, per-document paragraph summaries, the
    generated report, and provenance — into the committed frozen/
    directory, so the reported numbers can be reviewed and reproduced
    from a fresh checkout without a paid rerun. Raw diffs, document
    texts, and API response caches stay local-only. Repos, PR numbers,
    and author logins in the frozen set are public GitHub metadata."""
    import contextlib
    import io
    import shutil
    from datetime import date

    import analyze
    import gptzero_client as gzc
    required = (MANIFEST, MANIFEST_B3, MANIFEST_ERAS, MANIFEST_PC,
                DOCS, RESULTS)
    missing = [p.name for p in required if not p.is_file()]
    if missing:
        raise SystemExit(f"freeze refused: missing {missing}")
    manifest_slots = [s["slot"]
                      for p in (MANIFEST, MANIFEST_B3, MANIFEST_ERAS,
                                MANIFEST_PC)
                      if p.is_file()
                      for s in json.loads(p.read_text())["slots"]]
    score_rows = _load_rows(RESULTS)
    _validate_freeze(manifest_slots, _load_rows(DOCS), score_rows,
                     _load_rows(DOCS_RETEST), _load_rows(RESULTS_RETEST))
    PARAGRAPHS.write_text("".join(
        json.dumps(r) + "\n" for r in _paragraph_summaries(score_rows)))
    if FROZEN.is_dir():
        shutil.rmtree(FROZEN)
    FROZEN.mkdir()
    kept = []
    for p in (*required, DOCS_RETEST, RESULTS_RETEST, PARAGRAPHS):
        if p.is_file():
            shutil.copy(p, FROZEN / p.name)
            kept.append(p.name)
    if RESULTS_SEM.is_file():
        # append-only log: freeze only the rows bound to the current
        # corpus (one per slot, pinned revision)
        bound = analyze.sem_bound(score_rows,
                                  _load_rows(RESULTS_SEM))
        (FROZEN / RESULTS_SEM.name).write_text(
            "".join(json.dumps(r) + "\n" for r in bound))
        kept.append(RESULTS_SEM.name)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        analyze.report(RESULTS, RESULTS_RETEST, PARAGRAPHS,
                       RESULTS_SEM)
    (FROZEN / "report.txt").write_text(buf.getvalue())
    (FROZEN / "PROVENANCE.md").write_text(
        f"# Frozen audit set ({date.today().isoformat()})\n\n"
        f"- detector version pin: {gzc.PINNED_VERSION}\n"
        f"- reservation ledger: {ledger_total()} words reserved, "
        f"ceiling {gzc.BUDGET_WORDS}\n"
        f"- files: {', '.join(kept)} + report.txt\n\n"
        f"The retest rows are the stage-1 sensitivity subset: every "
        f"document truncated at the design cap when the retest ran; "
        f"the report's coverage line states the bound share of the "
        f"current corpus. The ledger deliberately over-counts on "
        f"transport failures (every HTTP attempt reserves before it "
        f"runs); reconcile against the GPTZero dashboard by archiving "
        f"the ledger and seeding it with one dashboard-confirmed row "
        f"(see README).\n")
    print(f"frozen: {len(kept) + 2} files -> {FROZEN}")


def ledger_total() -> int:
    import gptzero_client as gzc
    return gzc.ledger(RESERVATIONS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--sample-b3", action="store_true")
    ap.add_argument("--sample-eras", action="store_true")
    ap.add_argument("--sample-pc", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--retest", action="store_true")
    ap.add_argument("--score-sem", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if a.sample:
        cmd_sample()
    elif a.sample_b3:
        cmd_sample_b3()
    elif a.sample_eras:
        cmd_sample_eras()
    elif a.sample_pc:
        cmd_sample_pc()
    elif a.fetch:
        cmd_fetch()
    elif a.score:
        cmd_score(a.limit)
    elif a.retest:
        cmd_retest()
    elif a.score_sem:
        cmd_score_sem()
    elif a.freeze:
        cmd_freeze()
    else:
        import analyze
        analyze.report(RESULTS, RESULTS_RETEST, PARAGRAPHS,
                       RESULTS_SEM)


if __name__ == "__main__":
    main()
