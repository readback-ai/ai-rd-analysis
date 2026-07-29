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
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE.parents[1] / "src"))

LOCAL = BASE / "local"
MANIFEST = LOCAL / "manifest_v1_50k.json"
DOCS = LOCAL / "docs_v1.jsonl"
RESULTS = LOCAL / "results" / "scores_v1.jsonl"
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


def _doc_rows() -> dict[str, dict]:
    if not DOCS.is_file():
        return {}
    rows = [json.loads(ln) for ln in DOCS.read_text().splitlines()
            if ln.strip()]
    return {r["slot"]: r for r in rows}


def cmd_fetch() -> None:
    import diffs
    manifest = json.loads(MANIFEST.read_text())
    cap = manifest["params"]["word_cap"]
    floor = manifest["params"]["word_floor"]
    # A row is a valid checkpoint only if it is FILLED, its chosen PR is
    # still among its slot's candidates (a redraw invalidates rows), AND
    # it was assembled under the current rules — cap, floor, and the
    # assembly version — else it is rebuilt from the cached diff (a pure
    # k_cand deepening retains everything). Unfilled slots are retried
    # every run.
    cands_of = {s["slot"]: {(c[0], int(c[1])) for c in s["candidates"]}
                for s in manifest["slots"]}
    filled = {s: r for s, r in _doc_rows().items()
              if not r.get("unfilled")
              and (r["repo"], r["num"]) in cands_of.get(s, set())
              and r.get("word_cap") == cap
              and r.get("word_floor") == floor
              and r.get("assembly") == diffs.ASSEMBLY}
    LOCAL.mkdir(parents=True, exist_ok=True)
    fp = manifest["fingerprint"]
    with DOCS.open("w") as out:
        for r in filled.values():
            out.write(json.dumps({**r, "fingerprint": fp}) + "\n")
        for slot in manifest["slots"]:
            if slot["slot"] in filled:
                continue
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


def cmd_score(limit: int | None) -> None:
    import gptzero_client as gzc
    fp = json.loads(MANIFEST.read_text())["fingerprint"]
    if gzc.PINNED_VERSION is None and limit is None:
        raise SystemExit(
            "full run requires a pinned detector version: smoke first "
            "(--score --limit 2), set gptzero_client.PINNED_VERSION to "
            "the version the responses report, then re-run --score")
    docs = {r["slot"]: r for r in _doc_rows().values()
            if not r.get("unfilled")}
    stale = [r["slot"] for r in docs.values()
             if r.get("fingerprint") != fp]
    if stale:
        raise SystemExit(
            f"{len(stale)} document rows predate the current manifest "
            f"({fp}) — run --fetch first")
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
        for r in todo:
            text = (DOC_CACHE / f"{r['doc_sha']}.txt").read_text()
            try:
                resp, billed = gzc.score(r["doc_sha"], text, RESP_CACHE,
                                         RESERVATIONS)
            except RuntimeError as e:
                print(f"SCORE FAIL {r['slot']}: {e}", flush=True)
                continue          # deferred: absent from results, retried
            fields = gzc.doc_fields(resp)
            if (gzc.PINNED_VERSION is not None
                    and fields["model_version"] != gzc.PINNED_VERSION):
                print(f"VERSION MISMATCH {r['slot']}: response reports "
                      f"{fields['model_version']!r}, pin is "
                      f"{gzc.PINNED_VERSION!r} — not recorded",
                      flush=True)
                continue
            out.write(json.dumps(
                {**r, **fields, "billed_words": billed}) + "\n")
            out.flush()
            print(f"scored {r['slot']}: {fields['predicted_class']} "
                  f"({billed} words billed)", flush=True)
    print(f"reserved: {gzc.ledger(RESERVATIONS)}/{gzc.BUDGET_WORDS} "
          f"words")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if a.sample:
        cmd_sample()
    elif a.fetch:
        cmd_fetch()
    elif a.score:
        cmd_score(a.limit)
    else:
        import analyze
        analyze.report(RESULTS)


if __name__ == "__main__":
    main()
