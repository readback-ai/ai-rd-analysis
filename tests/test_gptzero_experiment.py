"""GPTZero calibration experiment (experiments/gptzero): sampler
eligibility and determinism, document assembly, budget guard, and
analysis math. Feature tests for new capability, mutation-verified."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "experiments" / "gptzero"))
import analyze          # noqa: E402
import diffs            # noqa: E402
import eras             # noqa: E402
import gptzero_client   # noqa: E402
import ablation         # noqa: E402
import newfile          # noqa: E402
import pc               # noqa: E402
import sampling         # noqa: E402
import sem13c           # noqa: E402

CLAUDE_MARK = "x\n\nCo-Authored-By: Claude <noreply@anthropic.com>"


_REAL_POST_ONCE = gptzero_client._post_once


@pytest.fixture(autouse=True)
def _no_live_gptzero(monkeypatch):
    """Tests must never reach the live API: the default transports raise
    unless a test injects its own."""
    def _blocked(*a, **k):
        raise AssertionError("live GPTZero call from a test")
    monkeypatch.setattr(gptzero_client, "_post_once", _blocked)
    monkeypatch.setattr(gptzero_client, "_post_files_once", _blocked)


def _pr(created, merged, num, login="alice", additions=100, msg="x"):
    return {"number": num, "createdAt": created, "mergedAt": merged,
            "additions": additions, "deletions": 0,
            "author": {"login": login, "__typename": "User"},
            "mergedBy": {"login": "bob", "__typename": "User"},
            "authorAssociation": "MEMBER",
            "commits": {"nodes": [{"commit": {"message": msg}}]},
            "reviews": {"nodes": []}}


def _q2(num, **kw):
    return _pr("2026-04-01T00:00:00Z", "2026-04-05T00:00:00Z", num, **kw)


def test_pools_eligibility(monkeypatch):
    """Fleet, bot-login, unmerged, and out-of-LOC-window PRs never enter
    the pools; a mixed author lands in both q2 arms; Q1-2024 unmarked
    PRs land in q1."""
    from pipeline import frame
    from pipeline.studies import productivity
    unmerged = _q2(9, login="alice")
    unmerged["mergedAt"] = None
    unmerged["mergedBy"] = None
    cells = {
        ("o/r", "2026-04-01..2026-06-30"): [
            _q2(1, login="alice", msg=CLAUDE_MARK),   # AI arm
            _q2(2, login="alice"),                    # nonai arm
            _q2(3, login="fleeter"),
            _q2(4, login="dependabot[bot]"),
            _q2(5, login="tiny", additions=10),
            _q2(6, login="huge", additions=5000),
            unmerged],
        ("o/r", "2024-01-01..2024-03-31"): [
            _pr("2024-02-01T00:00:00Z", "2024-02-05T00:00:00Z", 7,
                login="olda")],
    }
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins",
                        lambda: {"fleeter"})
    p = sampling.pools()
    assert set(p["q2"]) == {"alice"}
    assert p["q2"]["alice"]["ai"] == [("o/r", 1, 100)]
    assert p["q2"]["alice"]["nonai"] == [("o/r", 2, 100)]
    assert p["q1"] == {"olda": [("o/r", 7, 100)]}


def _pools(mixed=("alice",), ai_only=("bob",), q1=("olda",)):
    q2 = {a: {"ai": [("o/r", 1, 100)], "nonai": [("o/r", 2, 100)]}
          for a in mixed}
    q2.update({a: {"ai": [("o/r", 3, 100)], "nonai": []}
               for a in ai_only})
    return {"q2": q2, "q1": {a: [("o/q", 9, 80)] for a in q1}}


def test_draw_pairs_only_mixed_authors():
    """An AI-only author never anchors a pair; a drawn author yields
    exactly one slot per arm."""
    slots = sampling.draw(_pools())
    authors = {s["author"] for s in slots if s["arm"] == "P"}
    assert authors == {"alice"}
    alice = [s for s in slots if s["author"] == "alice"]
    assert sorted(s["ai"] for s in alice) == [False, True]


def test_draw_deterministic_fingerprint_sensitive(tmp_path):
    p = _pools()
    assert sampling.draw(p) == sampling.draw(p)
    fp = sampling.fingerprint(p)
    p2 = _pools()
    p2["q1"]["newcomer"] = [("o/z", 1, 60)]
    assert sampling.fingerprint(p2) != fp
    path = tmp_path / "m.json"
    _, rewrote = sampling.ensure_manifest(p, path)
    assert rewrote
    _, rewrote = sampling.ensure_manifest(p, path)
    assert not rewrote
    tampered = json.loads(path.read_text())
    tampered["slots"] = tampered["slots"][:-1]
    path.write_text(json.dumps(tampered))
    _, rewrote = sampling.ensure_manifest(p, path)
    assert rewrote


DIFF = """\
diff --git a/package-lock.json b/package-lock.json
+++ b/package-lock.json
@@ -1,2 +1,4 @@
+lockfile noise lockfile noise
diff --git a/README.md b/README.md
+++ b/README.md
@@ -1 +1,2 @@
+prose line that is not code
diff --git a/src/app.py b/src/app.py
+++ b/src/app.py
@@ -1,3 +1,6 @@
 context line
+def added_one():
+    return 1
-removed = True
@@ -10,2 +12,3 @@
+ADDED_TWO = 2
"""


def test_document_is_added_code_lines_only():
    files = diffs.parse_diff(DIFF)
    text, meta = diffs.build_document(files, cap=600, floor=1)
    assert "lockfile" not in text and "prose" not in text
    assert "context line" not in text and "removed" not in text
    assert "def added_one():" in text and "ADDED_TWO = 2" in text
    assert text.startswith("// file: src/app.py")
    assert meta["kept"] == ["src/app.py"]
    assert set(meta["dropped"]) == {"package-lock.json", "README.md"}
    assert meta["words"] == diffs.count_words(text)


def test_document_caps_at_hunk_boundary_and_floors():
    big_hunk = ["word " * 10] * 30            # 300 words
    files = [("a.py", [big_hunk, big_hunk, big_hunk])]
    text, meta = diffs.build_document(files, cap=650, floor=100)
    assert meta["truncated"]
    assert meta["words"] <= 650
    assert meta["words"] == 603               # header + exactly 2 hunks
    text, meta = diffs.build_document(files, cap=650, floor=604)
    assert text is None                        # floor: try next candidate


def test_budget_guard_blocks_before_http(tmp_path):
    resv = tmp_path / "resv.jsonl"
    resv.write_text(json.dumps(
        {"doc_sha": "prior",
         "words": gptzero_client.BUDGET_WORDS - 100}) + "\n")
    calls = []

    def transport(text):
        calls.append(text)
        return {"documents": [{"predicted_class": "ai"}]}

    with pytest.raises(SystemExit):
        gptzero_client.score("sha1", "w " * 200, tmp_path, resv,
                             transport=transport)
    assert calls == []


def test_cache_hit_never_resubmits_or_reserves(tmp_path, monkeypatch):
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", None)
    resv = tmp_path / "resv.jsonl"
    calls = []

    def transport(text):
        calls.append(text)
        return {"documents": [{"predicted_class": "ai"}]}

    resp, billed = gptzero_client.score("shaX", "some words here",
                                        tmp_path, resv,
                                        transport=transport)
    assert billed == 3 and len(calls) == 1
    assert gptzero_client.ledger(resv) == 3
    resp2, billed2 = gptzero_client.score("shaX", "some words here",
                                          tmp_path, resv,
                                          transport=transport)
    assert resp2 == resp and billed2 == 0 and len(calls) == 1
    assert gptzero_client.ledger(resv) == 3     # hit reserves nothing


def test_pinned_version_namespaces_cache_and_request(tmp_path,
                                                     monkeypatch):
    """PR review P2: the detector version is pinned per design — the
    request carries it and the response cache is namespaced by it, so a
    resumed or cross-design run can never silently reuse another
    model's scores."""
    monkeypatch.setenv("GPTZERO_API_KEY", "k")
    monkeypatch.setattr(gptzero_client, "PINNED_VERSION", "2026-01-01")
    assert "2026-01-01" in str(
        gptzero_client._cache_path(tmp_path, "sha"))
    sent = {}

    def fake_run(cmd, input=None, capture_output=True, text=True):
        sent.update(json.loads(input))
        assert not any("x-api-key" in c for c in cmd)   # key never in argv
        class R:
            returncode = 0
            stdout = '{"documents": []}\n200'
            stderr = ""
        return R()

    monkeypatch.setattr(gptzero_client.subprocess, "run", fake_run)
    monkeypatch.setattr(gptzero_client, "_post_once", _REAL_POST_ONCE)
    gptzero_client._post_once("text")
    assert sent["version"] == "2026-01-01"


def test_candidate_ordering_is_prefix_stable():
    """Deepening k must extend the candidate list, not reshuffle it —
    that is what lets a deeper pool refill unfilled slots without
    invalidating already-fetched ones."""
    import random
    # Contract pin, not a differential test: shuffle-then-slice makes the
    # property structural; rng.sample happens to satisfy it too in
    # current CPython, but only as an implementation detail.
    prs = [("o/r", n, 100) for n in range(60)]
    three = sampling._candidates(random.Random("s"), prs, 3)
    eight = sampling._candidates(random.Random("s"), prs, 8)
    assert eight[:3] == three


def test_fetch_retries_unfilled_and_stale_rows(tmp_path, monkeypatch):
    """An unfilled slot is re-attempted on the next --fetch run, and a
    filled row whose PR is no longer among its slot's candidates (after
    a redraw) is refetched rather than trusted."""
    import diffs
    import gz
    manifest = {"fingerprint": "FP",
                "params": {"word_cap": 600, "word_floor": 1},
                "slots": [
                    {"slot": "P:a:ai", "arm": "P", "author": "a",
                     "period": "Q2-2026", "ai": True,
                     "candidates": [["o/r", 1, 100]]},
                    {"slot": "P:a:nonai", "arm": "P", "author": "a",
                     "period": "Q2-2026", "ai": False,
                     "candidates": [["o/r", 2, 100]]}]}
    local = tmp_path / "local"
    local.mkdir()
    (local / "manifest.json").write_text(json.dumps(manifest))
    docs = local / "docs.jsonl"
    docs.write_text(json.dumps(
        {"slot": "P:a:ai", "arm": "P", "author": "a",
         "period": "Q2-2026", "ai": True, "unfilled": True}) + "\n" +
        json.dumps(
        {"slot": "P:a:nonai", "arm": "P", "author": "a",
         "period": "Q2-2026", "ai": False, "repo": "o/r", "num": 99,
         "loc": 5, "doc_sha": "stale", "words": 5, "kept": [],
         "dropped": [], "truncated": False}) + "\n")
    monkeypatch.setattr(gz, "LOCAL", local)
    monkeypatch.setattr(gz, "MANIFEST", local / "manifest.json")
    monkeypatch.setattr(gz, "DOCS", docs)
    monkeypatch.setattr(gz, "DOC_CACHE", local / "cache")
    monkeypatch.setattr(
        diffs, "fetch_diff",
        lambda repo, num, cache_dir, pace=0.5:
            f"diff --git a/x.py b/x.py\n+++ b/x.py\n@@ -1 +1,2 @@\n"
            f"+code_for_pr_{num} = {num}\n")
    gz.cmd_fetch()
    rows = {json.loads(ln)["slot"]: json.loads(ln)
            for ln in docs.read_text().splitlines()}
    assert rows["P:a:ai"]["num"] == 1          # unfilled slot now filled
    assert rows["P:a:nonai"]["num"] == 2       # stale row refetched


def test_attempted_words_count_against_ceiling(tmp_path, monkeypatch):
    """PR review P1: an HTTP attempt may be BILLED server-side even when
    the response is lost (connection drop after processing, crash before
    the cache write), so the ceiling must be enforced against words
    RESERVED per attempt, not against observed successes. Here a
    document fails all three attempts (3 x 10k words reserved); a later
    document whose words would exceed the ceiling counting those
    attempts must be refused with no HTTP call."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "BUDGET_WORDS", 50_000)
    monkeypatch.setattr(gzc.time, "sleep", lambda s: None)
    resv = tmp_path / "reservations.jsonl"

    def failing(text):
        raise gzc.urllib.error.URLError("dropped mid-flight")

    with pytest.raises(RuntimeError):
        gzc.score("shaA", "w " * 10_000, tmp_path, resv,
                  transport=failing)
    assert gzc.ledger(resv) == 30_000
    calls = []
    with pytest.raises(SystemExit):
        gzc.score("shaB", "w " * 21_000, tmp_path, resv,
                  transport=lambda t: calls.append(t) or {})
    assert calls == []


def test_every_retry_attempt_reserves(tmp_path, monkeypatch):
    """PR review P1: each attempt reserves its words BEFORE the HTTP call
    — two transient failures plus a success = three reservations."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", None)
    monkeypatch.setattr(gzc.time, "sleep", lambda s: None)
    resv = tmp_path / "reservations.jsonl"
    attempts = []

    def flaky(text):
        attempts.append(1)
        if len(attempts) < 3:
            raise gzc.urllib.error.URLError("reset")
        return {"documents": [{"predicted_class": "human"}]}

    _, billed = gzc.score("shaC", "one two three", tmp_path, resv,
                          transport=flaky)
    assert billed == 3
    assert gzc.ledger(resv) == 9        # 3 attempts x 3 words


def test_score_drops_rows_for_redrawn_documents(tmp_path, monkeypatch):
    """PR review P2: a results row is valid only for the document its
    slot currently selects — after a redraw changes the slot's doc_sha,
    the stale row must be dropped and the slot rescored, not skipped by
    name."""
    import gptzero_client
    import gz
    local = tmp_path / "local"
    (local / "results").mkdir(parents=True)
    (local / "cache" / "docs").mkdir(parents=True)
    (local / "manifest.json").write_text(json.dumps(
        {"fingerprint": "FP",
         "params": {"word_cap": 600, "word_floor": 100},
         "slots": [{"slot": "P:a:ai",
                    "candidates": [["o/r", 1, 100]]}]}))
    docs = local / "docs.jsonl"
    docs.write_text(json.dumps(
        {"slot": "P:a:ai", "arm": "P", "author": "a",
         "period": "Q2-2026", "ai": True, "repo": "o/r", "num": 1,
         "loc": 100, "doc_sha": "NEW", "words": 3, "kept": ["x.py"],
         "dropped": [], "truncated": False,
         "fingerprint": "FP"}) + "\n")
    (local / "cache" / "docs" / "NEW.txt").write_text("one two three")
    results = local / "results" / "scores.jsonl"
    results.write_text(json.dumps(
        {"slot": "P:a:ai", "doc_sha": "OLD", "ai": True, "arm": "P",
         "author": "a", "billed_words": 3,
         "predicted_class": "human"}) + "\n")
    monkeypatch.setattr(gz, "LOCAL", local)
    monkeypatch.setattr(gz, "MANIFEST", local / "manifest.json")
    monkeypatch.setattr(gz, "DOCS", docs)
    monkeypatch.setattr(gz, "RESULTS", results)
    monkeypatch.setattr(gz, "DOC_CACHE", local / "cache" / "docs")
    monkeypatch.setattr(gz, "RESP_CACHE", local / "cache" / "responses")
    monkeypatch.setattr(gz, "RESERVATIONS",
                        local / "results" / "reservations.jsonl",
                        raising=False)
    monkeypatch.setattr(gptzero_client, "PINNED_VERSION", "pinver")
    monkeypatch.setattr(
        gptzero_client, "score_batch",
        lambda items, cache_dir, resv, **kw:
            [({"version": "pinver",
               "documents": [{"predicted_class": "ai"}]}, 3)
             for _ in items])
    gz.cmd_score(None)
    rows = [json.loads(ln)
            for ln in results.read_text().splitlines() if ln.strip()]
    assert [r["doc_sha"] for r in rows] == ["NEW"]
    assert rows[0]["predicted_class"] == "ai"


def test_score_refuses_documents_from_an_older_manifest(
        tmp_path, monkeypatch):
    """PR review P2: --score after a redraw but before --fetch must
    refuse — document rows carry the fingerprint they were fetched
    under, and scoring only proceeds when it matches the manifest."""
    import gz
    local = tmp_path / "local"
    local.mkdir()
    (local / "manifest.json").write_text(json.dumps(
        {"fingerprint": "NEWFP", "params": {}, "slots": []}))
    docs = local / "docs.jsonl"
    docs.write_text(json.dumps(
        {"slot": "P:a:ai", "arm": "P", "author": "a",
         "period": "Q2-2026", "ai": True, "repo": "o/r", "num": 1,
         "loc": 100, "doc_sha": "X", "words": 3, "kept": [],
         "dropped": [], "truncated": False,
         "fingerprint": "OLDFP"}) + "\n")
    monkeypatch.setattr(gz, "MANIFEST", local / "manifest.json")
    monkeypatch.setattr(gz, "DOCS", docs)
    with pytest.raises(SystemExit):
        gz.cmd_score(None)


def test_b2_never_samples_paired_authors():
    """PR review P2: B2 is the INDEPENDENT baseline — no Arm-P author
    may appear in it, including paired authors with Q1 data who missed
    the B1 cap."""
    mixed = [f"a{i:02d}" for i in range(12)]
    pools_ = {"q2": {a: {"ai": [("o/r", 1, 100)],
                         "nonai": [("o/r", 2, 100)]} for a in mixed},
              "q1": {a: [("o/q", 9, 80)] for a in mixed}}
    slots = sampling.draw(pools_)
    p_authors = {s["author"] for s in slots if s["arm"] == "P"}
    b2_authors = {s["author"] for s in slots if s["arm"] == "B2"}
    assert not (p_authors & b2_authors)


def test_b1_same_repo_priority_is_prefix_stable(monkeypatch):
    """PR review P3: the same-repo preference must be applied to the
    FULL candidate ordering before slicing, so deepening k_cand cannot
    reorder a B1 slot's existing prefix."""
    prs = [("other/r", n, 80) for n in range(6)] + [("o/r", 99, 80)]
    pools_ = {"q2": {"alice": {"ai": [("o/r", 1, 100)],
                               "nonai": [("o/r", 2, 100)]}},
              "q1": {"alice": prs}}
    monkeypatch.setitem(sampling.PARAMS, "k_cand", 3)
    three = [s for s in sampling.draw(pools_) if s["arm"] == "B1"][0]
    monkeypatch.setitem(sampling.PARAMS, "k_cand", 8)
    eight = [s for s in sampling.draw(pools_) if s["arm"] == "B1"][0]
    assert eight["candidates"][:3] == three["candidates"]


def test_plus_plus_source_lines_survive_parsing():
    """PR review P3: a source line beginning '++' arrives as '+++...' in
    the diff; only '+++ <path>' OUTSIDE a hunk is a file header."""
    diff = ("diff --git a/inc.c b/inc.c\n"
            "+++ b/inc.c\n"
            "@@ -1 +1,2 @@\n"
            "+++counter;\n"
            "+done = 1;\n")
    files = diffs.parse_diff(diff)
    assert files == [("inc.c", [["++counter;", "done = 1;"]])]


def _score_world(tmp_path, monkeypatch, docs_row, results_rows=(),
                 resp_version="pinver"):
    import gptzero_client
    import gz
    local = tmp_path / "local"
    (local / "results").mkdir(parents=True)
    (local / "cache" / "docs").mkdir(parents=True)
    (local / "manifest.json").write_text(json.dumps(
        {"fingerprint": "FP",
         "params": {"word_cap": 600, "word_floor": 100},
         "slots": [{"slot": docs_row["slot"],
                    "candidates": [[docs_row.get("repo", "o/r"),
                                    docs_row.get("num", 1), 100]]}]}))
    docs = local / "docs.jsonl"
    docs.write_text(json.dumps(docs_row) + "\n")
    (local / "cache" / "docs" / f"{docs_row['doc_sha']}.txt")\
        .write_text("one two three")
    results = local / "results" / "scores.jsonl"
    results.write_text("".join(json.dumps(r) + "\n"
                               for r in results_rows))
    monkeypatch.setattr(gz, "LOCAL", local)
    monkeypatch.setattr(gz, "MANIFEST", local / "manifest.json")
    monkeypatch.setattr(gz, "DOCS", docs)
    monkeypatch.setattr(gz, "RESULTS", results)
    monkeypatch.setattr(gz, "DOC_CACHE", local / "cache" / "docs")
    monkeypatch.setattr(gz, "RESP_CACHE", local / "cache" / "responses")
    monkeypatch.setattr(gz, "RESERVATIONS",
                        local / "results" / "reservations.jsonl",
                        raising=False)
    monkeypatch.setattr(
        gptzero_client, "score_batch",
        lambda items, cache_dir, resv, **kw:
            [({"version": resp_version,
               "documents": [{"predicted_class": "ai"}]}, 3)
             for _ in items])
    return gz, results


_DOC_ROW = {"slot": "P:a:ai", "arm": "P", "author": "a",
            "period": "Q2-2026", "ai": True, "repo": "o/r", "num": 1,
            "loc": 100, "doc_sha": "SHA", "words": 3, "kept": ["x.py"],
            "dropped": [], "truncated": False, "fingerprint": "FP"}


def test_full_score_run_requires_a_pinned_version(tmp_path, monkeypatch):
    """PR re-review P2: only the smoke run (--limit) may go unpinned;
    an unlimited run with PINNED_VERSION unset must refuse."""
    import gptzero_client
    gz, _ = _score_world(tmp_path, monkeypatch, dict(_DOC_ROW))
    monkeypatch.setattr(gptzero_client, "PINNED_VERSION", None)
    with pytest.raises(SystemExit):
        gz.cmd_score(None)
    gz.cmd_score(2)                       # smoke is allowed unpinned


def test_pinned_run_invalidates_rows_from_other_versions(
        tmp_path, monkeypatch):
    """PR re-review P2: once a version is pinned, results scored under
    another (or no) version are invalid — dropped and rescored."""
    import gptzero_client
    stale = {**_DOC_ROW, "billed_words": 3, "predicted_class": "human",
             "model_version": None}
    gz, results = _score_world(tmp_path, monkeypatch, dict(_DOC_ROW),
                               results_rows=[stale],
                               resp_version="pinver")
    monkeypatch.setattr(gptzero_client, "PINNED_VERSION", "pinver")
    gz.cmd_score(None)
    rows = [json.loads(ln)
            for ln in results.read_text().splitlines() if ln.strip()]
    assert len(rows) == 1
    assert rows[0]["model_version"] == "pinver"
    assert rows[0]["predicted_class"] == "ai"      # rescored, not kept


def test_version_mismatch_aborts_before_caching(tmp_path, monkeypatch):
    """PR re-re-review P1: a response whose version differs from the pin
    must ABORT the run inside score() BEFORE the cache write — caching
    it would poison the pinned namespace (every later run replays the
    wrong-version response), and continuing would bill every remaining
    document while recording none. The attempt's reservation stays (it
    may have been billed); the cache stays empty."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", "pinver")
    resv = tmp_path / "resv.jsonl"
    with pytest.raises(SystemExit):
        gzc.score("shaV", "one two three", tmp_path, resv,
                  transport=lambda t: {"version": "other",
                                       "documents": []})
    assert not list(tmp_path.rglob("*.json"))     # nothing cached
    assert gzc.ledger(resv) == 3                  # attempt still reserved


def test_mismatch_halts_the_run_with_nothing_recorded(
        tmp_path, monkeypatch):
    """PR re-re-review P1 (contract pin, batch form): the
    version-mismatch SystemExit from score_batch propagates — the run
    halts with the whole batch unrecorded instead of billing on."""
    import gptzero_client
    import gz
    gz_mod, results = _score_world(tmp_path, monkeypatch,
                                   dict(_DOC_ROW))
    second = {**_DOC_ROW, "slot": "P:b:ai", "author": "b",
              "doc_sha": "SHA2"}
    with gz.DOCS.open("a") as f:
        f.write(json.dumps(second) + "\n")
    (gz.DOC_CACHE / "SHA2.txt").write_text("four five six")
    m = json.loads(gz.MANIFEST.read_text())
    m["slots"].append({"slot": "P:b:ai",
                       "candidates": [["o/r", 1, 100]]})
    gz.MANIFEST.write_text(json.dumps(m))
    calls = []

    def bad_batch(items, cache_dir, resv, **kw):
        calls.append(len(items))
        raise SystemExit("version mismatch")
    monkeypatch.setattr(gptzero_client, "PINNED_VERSION", "pinver")
    monkeypatch.setattr(gptzero_client, "score_batch", bad_batch)
    with pytest.raises(SystemExit):
        gz_mod.cmd_score(None)
    assert calls == [2]
    assert results.read_text().strip() == ""


def test_fetch_rebuilds_when_assembly_params_change(
        tmp_path, monkeypatch):
    """PR re-review P2: a document row survives --fetch only under the
    assembly parameters it was built with — changing word_cap must
    rebuild from the cached diff, not relabel the old document."""
    import diffs
    import gz
    manifest = {"fingerprint": "FP2",
                "params": {"word_cap": 10, "word_floor": 1},
                "slots": [
                    {"slot": "P:a:ai", "arm": "P", "author": "a",
                     "period": "Q2-2026", "ai": True,
                     "candidates": [["o/r", 1, 100]]}]}
    local = tmp_path / "local"
    local.mkdir()
    (local / "manifest.json").write_text(json.dumps(manifest))
    docs = local / "docs.jsonl"
    old = {**_DOC_ROW, "words": 600, "word_cap": 600,
           "word_floor": 100, "assembly": diffs.ASSEMBLY}
    docs.write_text(json.dumps(old) + "\n")
    monkeypatch.setattr(gz, "LOCAL", local)
    monkeypatch.setattr(gz, "MANIFEST", local / "manifest.json")
    monkeypatch.setattr(gz, "DOCS", docs)
    monkeypatch.setattr(gz, "DOC_CACHE", local / "cache")
    monkeypatch.setattr(
        diffs, "fetch_diff",
        lambda repo, num, cache_dir, pace=0.5:
            "diff --git a/x.py b/x.py\n+++ b/x.py\n@@ -1 +1,2 @@\n"
            "+short = 1\n")
    gz.cmd_fetch()
    rows = [json.loads(ln)
            for ln in docs.read_text().splitlines() if ln.strip()]
    assert rows[0]["word_cap"] == 10          # rebuilt under new params
    assert rows[0]["words"] <= 10


def test_report_treats_missing_version_as_its_own_version(
        tmp_path, capsys):
    """PR re-review P2: a row with no model_version must not silently
    pool with pinned rows — it counts as a distinct 'unknown' version
    and triggers the mixed-version refusal."""
    rows = [{"arm": "P", "author": "a", "ai": True, "words": 300,
             "class_probabilities": {"ai": 0.9},
             "predicted_class": "ai", "model_version": "v1"},
            {"arm": "P", "author": "a", "ai": False, "words": 300,
             "class_probabilities": {"ai": 0.1},
             "predicted_class": "human"}]
    p = tmp_path / "scores.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    analyze.report(p)
    assert "REFUSING" in capsys.readouterr().out


def _b3_node(num, login="dev", typ="User", merged="2022-08-01T00:00:00Z",
             additions=100):
    return {"number": num, "createdAt": "2022-07-15T00:00:00Z",
            "mergedAt": merged, "additions": additions, "deletions": 0,
            "author": {"login": login, "__typename": typ}}


def test_b3_node_hygiene_mirrors_frame_rules():
    """B3 has no census frame, so eligibility applies node-side: bots,
    unmerged PRs, and out-of-window LOC never become candidates."""
    import b3
    nodes = [_b3_node(1),
             _b3_node(2, login="dependabot[bot]"),
             _b3_node(3, typ="Bot", login="copilot"),
             _b3_node(4, merged=None),
             _b3_node(5, additions=10),
             _b3_node(6, additions=99999)]
    assert b3.eligible_nodes(nodes) == [("dev", 1, 100)]


def test_b3_draw_is_deterministic_and_one_doc_per_author(monkeypatch):
    """The repo draw is seeded PPS; slots take one document per author
    across the whole arm."""
    import b3
    monkeypatch.setitem(b3.B3_PARAMS, "n_docs", 20)
    pool = {f"o/r{i}": 50 + i for i in range(30)}
    assert b3.draw_repos(pool) == b3.draw_repos(pool)
    pages = {r: [_b3_node(1, login="samedev"), _b3_node(2, login=f"u{r}")]
             for r in pool}
    slots = b3.slots_for(sorted(pool), pages)
    authors = [s["author"] for s in slots]
    assert len(authors) == len(set(authors))     # no author twice
    assert len(slots) == b3.B3_PARAMS["n_docs"]
    assert all(s["arm"] == "B3" and s["ai"] is False for s in slots)


def test_b3_candidates_all_belong_to_the_slot_author():
    """PR #28 review P1: B3 candidate lists mixed several authors' PRs
    under the first candidate's author label, so a floor miss made
    cmd_fetch fill the slot with ANOTHER author's PR while keeping the
    recorded author (5/19 frozen rows misattributed). The slot's author
    is selected first and every candidate must be that author's PR."""
    import b3
    pages = {"o/r": [_b3_node(1, login="ann"),
                     _b3_node(2, login="bob"),
                     _b3_node(3, login="ann"),
                     _b3_node(4, login="bob"),
                     _b3_node(5, login="cyd")]}
    slots = b3.slots_for(["o/r"], pages)
    assert len(slots) == 1
    author = slots[0]["author"]
    by_author = {a: {num for a2, num, _l in
                     b3.eligible_nodes(pages["o/r"]) if a2 == a}
                 for a in ("ann", "bob", "cyd")}
    nums = {num for _r, num, _l in slots[0]["candidates"]}
    assert nums == by_author[author]     # every candidate, one author


def test_b3_fingerprint_tracks_pool():
    import b3
    pool = {"o/a": 30, "o/b": 40}
    fp = b3.fingerprint(pool)
    assert b3.fingerprint({**pool, "o/c": 25}) != fp
    assert b3.fingerprint(dict(reversed(pool.items()))) == fp


def _batch_resp(shas, version="pinver"):
    return {"version": version,
            "documents": [{"filename": f"{s}.txt",
                           "predicted_class": "ai",
                           "class_probabilities": {"ai": 1.0}}
                          for s in shas]}


def test_score_batch_caches_per_doc_and_reserves(tmp_path, monkeypatch):
    """Batch endpoint (support-recommended): one request scores many
    documents; each doc still gets its own versioned cache entry in the
    single-doc format and its own reservation row."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", "pinver")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    items = []
    for sha, text in (("shaA", "one two three"), ("shaB", "four five")):
        p = docs_dir / f"{sha}.txt"
        p.write_text(text)
        items.append((sha, p))
    sent = []

    def transport(paths):
        sent.append([p.name for p in paths])
        return _batch_resp([p.stem for p in paths])

    resv = tmp_path / "resv.jsonl"
    out = gzc.score_batch(items, tmp_path / "cache", resv,
                          transport=transport)
    assert [b for _r, b in out] == [3, 2]
    assert gzc.ledger(resv) == 5
    assert sent == [["shaA.txt", "shaB.txt"]]
    for sha in ("shaA", "shaB"):
        cached = json.loads(
            gzc._cache_path(tmp_path / "cache", sha).read_text())
        assert gzc.doc_fields(cached)["predicted_class"] == "ai"
        assert gzc.doc_fields(cached)["model_version"] == "pinver"


def test_score_batch_skips_cached_documents(tmp_path, monkeypatch):
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", "pinver")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    items = []
    for sha, text in (("shaA", "one two three"), ("shaB", "four five")):
        p = docs_dir / f"{sha}.txt"
        p.write_text(text)
        items.append((sha, p))
    pre = gzc._cache_path(tmp_path / "cache", "shaA")
    pre.parent.mkdir(parents=True)
    pre.write_text(json.dumps(_batch_resp(["shaA"])))
    sent = []

    def transport(paths):
        sent.append([p.name for p in paths])
        return _batch_resp([p.stem for p in paths])

    out = gzc.score_batch(items, tmp_path / "cache",
                          tmp_path / "resv.jsonl", transport=transport)
    assert sent == [["shaB.txt"]]           # cached doc not resubmitted
    assert [b for _r, b in out] == [0, 2]


def test_score_batch_version_or_shape_mismatch_caches_nothing(
        tmp_path, monkeypatch):
    """A batch whose response version differs from the pin, or whose
    document count doesn't match the upload, aborts before ANY cache
    write — a misattributed batch would poison every document in it."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", "pinver")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    p = docs_dir / "shaA.txt"
    p.write_text("one two three")
    with pytest.raises(SystemExit):
        gzc.score_batch([("shaA", p)], tmp_path / "cache",
                        tmp_path / "resv.jsonl",
                        transport=lambda paths:
                            _batch_resp(["shaA"], version="other"))
    with pytest.raises(SystemExit):
        gzc.score_batch([("shaA", p)], tmp_path / "cache",
                        tmp_path / "resv.jsonl",
                        transport=lambda paths:
                            {"version": "pinver", "documents": []})
    assert not list((tmp_path / "cache").rglob("*.json"))
    dumps = list(tmp_path.glob("batch_mismatch_*.json"))
    assert len(dumps) == 2
    assert json.loads(dumps[0].read_text())


def test_score_batch_retries_transient_failures(tmp_path, monkeypatch):
    """Live-run finding 2026-08-04: HTTP 408 on the first files-endpoint
    batch aborted the whole run. A transient batch failure (408/429/5xx/
    network) must back off and retry like the single-doc path, with every
    attempt reserving the batch's words, and exhausted retries must raise
    RuntimeError so the caller defers the batch."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", "pinver")
    monkeypatch.setattr(gzc.time, "sleep", lambda s: None)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    p = docs_dir / "shaA.txt"
    p.write_text("one two three")
    attempts = []

    def flaky(paths):
        attempts.append(1)
        if len(attempts) < 3:
            raise gzc.urllib.error.HTTPError("u", 408, "timeout",
                                             None, None)
        return _batch_resp([q.stem for q in paths])

    resv = tmp_path / "resv.jsonl"
    out = gzc.score_batch([("shaA", p)], tmp_path / "cache", resv,
                          transport=flaky)
    assert [b for _r, b in out] == [3]
    assert gzc.ledger(resv) == 9            # 3 attempts x 3 words

    def down(paths):
        raise gzc.urllib.error.HTTPError("u", 503, "unavailable",
                                         None, None)

    q = docs_dir / "shaB.txt"
    q.write_text("four five")
    resv2 = tmp_path / "resv2.jsonl"
    with pytest.raises(RuntimeError):
        gzc.score_batch([("shaB", q)], tmp_path / "cache", resv2,
                        transport=down)
    assert gzc.ledger(resv2) == 6           # 3 attempts x 2 words


def _row(author, ai, p, cls="human", arm="P", period="Q2-2026"):
    return {"arm": arm, "author": author, "ai": ai, "period": period,
            "class_probabilities": {"ai": p},
            "predicted_class": cls, "truncated": False}


def test_score_batch_rejects_partial_or_inexact_filename_mapping(
        tmp_path, monkeypatch):
    """PR #28 review P1: the per-item filename fallback could assign one
    response document to two uploaded files (reordered response with one
    unnamed document) and permanently cache the wrong score under a
    document SHA. The mapping must be all-or-nothing: a complete, unique,
    exact filename set (any order), or no filenames at all (upload
    order); anything partial, duplicate, or unknown aborts uncached."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", "pinver")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    items = []
    for sha, text in (("shaA", "one two three"), ("shaB", "four five")):
        p = docs_dir / f"{sha}.txt"
        p.write_text(text)
        items.append((sha, p))

    def reordered_one_unnamed(paths):
        return {"version": "pinver", "documents": [
            {"filename": "shaB.txt", "predicted_class": "ai",
             "class_probabilities": {"ai": 1.0}},
            {"predicted_class": "human",
             "class_probabilities": {"ai": 0.0}}]}

    with pytest.raises(SystemExit):
        gzc.score_batch(items, tmp_path / "cache",
                        tmp_path / "resv.jsonl",
                        transport=reordered_one_unnamed)
    assert not list((tmp_path / "cache").rglob("*.json"))

    def unknown_name(paths):
        return {"version": "pinver", "documents": [
            {"filename": "shaA.txt", "predicted_class": "ai",
             "class_probabilities": {"ai": 1.0}},
            {"filename": "OTHER.txt", "predicted_class": "human",
             "class_probabilities": {"ai": 0.0}}]}

    with pytest.raises(SystemExit):
        gzc.score_batch(items, tmp_path / "cache",
                        tmp_path / "resv2.jsonl", transport=unknown_name)
    assert not list((tmp_path / "cache").rglob("*.json"))

    def complete_reordered(paths):
        return {"version": "pinver", "documents": [
            {"filename": "shaB.txt", "predicted_class": "human",
             "class_probabilities": {"ai": 0.25}},
            {"filename": "shaA.txt", "predicted_class": "ai",
             "class_probabilities": {"ai": 0.75}}]}

    out = gzc.score_batch(items, tmp_path / "cache",
                          tmp_path / "resv3.jsonl",
                          transport=complete_reordered)
    assert analyze.ai_prob(
        {"class_probabilities":
         gzc.doc_fields(out[0][0])["class_probabilities"]}) == 0.75
    assert gzc.doc_fields(out[1][0])["predicted_class"] == "human"

    for f in (tmp_path / "cache").rglob("*.json"):
        f.unlink()

    def all_unnamed(paths):
        return {"version": "pinver", "documents": [
            {"predicted_class": "ai", "class_probabilities": {"ai": 0.9}},
            {"predicted_class": "human",
             "class_probabilities": {"ai": 0.1}}]}

    out = gzc.score_batch(items, tmp_path / "cache",
                          tmp_path / "resv4.jsonl", transport=all_unnamed)
    assert gzc.doc_fields(out[0][0])["predicted_class"] == "ai"
    assert gzc.doc_fields(out[1][0])["predicted_class"] == "human"


def test_analysis_paired_sign_and_arm_rates():
    rows = [_row("a", True, 0.9, "ai"), _row("a", False, 0.1),
            _row("b", True, 0.8, "ai"), _row("b", False, 0.2),
            _row("c", True, 0.3), _row("c", False, 0.6)]
    pr = analyze.paired(rows)
    assert (pr["pairs"], pr["wins"], pr["losses"]) == (3, 2, 1)
    assert pr["sign_p"] == pytest.approx(0.5)      # C(3,2)+C(3,3) / 8
    s = analyze.arm_stats([r for r in rows if r["ai"]])
    assert s["n"] == 3 and s["flag_ai"] == pytest.approx(2 / 3)


def test_analysis_breaks_out_all_predicted_classes():
    rows = [_row("a", True, 0.9, "ai"), _row("b", True, 0.5, "mixed"),
            _row("c", True, 0.2, "human"), _row("d", True, 0.1, "human")]
    s = analyze.arm_stats(rows)
    assert s["flag_ai"] == pytest.approx(1 / 4)
    assert s["flag_human"] == pytest.approx(2 / 4)
    assert s["flag_mixed"] == pytest.approx(1 / 4)


def test_paired_metric_secondary_outcomes():
    """The pre-specified secondary outcomes run the same within-author
    contrast on paragraph metrics; rows without the metric or an
    author never pair."""
    def prow(author, ai, share):
        return {"arm": "P", "period": "Q2-2026", "author": author,
                "ai": ai, "share_paragraphs_gt50": share}
    rows = [prow("a", True, 0.6), prow("a", False, 0.2),
            prow("b", True, 0.1), prow("b", False, 0.5),
            prow("c", True, 0.9), prow("c", False, 0.3),
            {"arm": "P", "period": "Q2-2026", "author": "d", "ai": True,
             "share_paragraphs_gt50": None}]
    pr = analyze.paired_metric(rows, "Q2-2026", "share_paragraphs_gt50")
    assert (pr["pairs"], pr["wins"], pr["losses"]) == (3, 2, 1)
    assert analyze.paired_metric(rows, "Q4-2025",
                                 "share_paragraphs_gt50") is None


def test_mixture_prevalence_anchors_and_clamp():
    """Method-of-moments prevalence: pi = (mean - human)/(anchor -
    human) per paired arm, clamped to [0, 1]; None when anchors are
    missing or inverted."""
    def row(arm, period, ai, p):
        return {"arm": arm, "period": period, "ai": ai,
                "class_probabilities": {"ai": p}}
    rows = ([row("P", "Q4-2025", True, 0.5)] * 4
            + [row("B3", "Q3-2022", False, 0.1)] * 4
            + [row("P", "Q2-2026", False, 0.3)] * 4
            + [row("P", "Q2-2026", True, 0.9)] * 4)
    s = analyze.mixture_stats(rows)
    assert s["anchor"] == pytest.approx(0.5)
    assert s["human"] == pytest.approx(0.1)
    by = {a["arm"]: a["pi"] for a in s["arms"]}
    assert by["Q4-2025 AI"] == pytest.approx(1.0)
    assert by["Q2-2026 nonAI"] == pytest.approx(0.5)
    assert by["Q2-2026 AI"] == pytest.approx(1.0)   # clamped
    assert analyze.mixture_stats(
        [row("P", "Q4-2025", True, 0.1),
         row("B3", "Q3-2022", False, 0.5)]) is None  # inverted anchors


def test_analysis_pairs_within_one_quarter_only():
    """A same-named author scored in two quarters must never be paired
    across them: paired() contrasts within one quarter's arm P."""
    rows = [_row("a", True, 0.9, period="Q4-2025"),
            _row("a", False, 0.1, period="Q2-2026"),
            _row("b", True, 0.8, period="Q4-2025"),
            _row("b", False, 0.2, period="Q4-2025")]
    assert analyze.paired(rows, period="Q2-2026") is None
    pr = analyze.paired(rows, period="Q4-2025")
    assert (pr["pairs"], pr["wins"]) == (1, 1)


def test_score_batch_retries_transient_error_envelopes(
        tmp_path, monkeypatch):
    """Live-run finding 2026-08-04: the files endpoint can return HTTP
    200 whose body is an error envelope ({'error': 'Request timeout or
    aborted', 'status': 408}, no documents); it was treated as a version
    mismatch and aborted the run. A transient-status envelope must
    retry with a fresh reservation like any transient failure; a
    non-transient envelope must still abort with the payload dumped."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", "pinver")
    monkeypatch.setattr(gzc.time, "sleep", lambda s: None)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    p = docs_dir / "shaA.txt"
    p.write_text("one two three")
    attempts = []

    def flaky(paths):
        attempts.append(1)
        if len(attempts) < 2:
            return {"error": "Request timeout or aborted", "status": 408}
        return _batch_resp([q.stem for q in paths])

    resv = tmp_path / "resv.jsonl"
    out = gzc.score_batch([("shaA", p)], tmp_path / "cache", resv,
                          transport=flaky)
    assert [b for _r, b in out] == [3]
    assert gzc.ledger(resv) == 6            # 2 attempts x 3 words

    q = docs_dir / "shaB.txt"
    q.write_text("four five")
    with pytest.raises(SystemExit):
        gzc.score_batch([("shaB", q)], tmp_path / "cache",
                        tmp_path / "resv2.jsonl",
                        transport=lambda paths:
                            {"error": "Payment required", "status": 402})
    assert list(tmp_path.glob("batch_mismatch_*.json"))


def test_batches_respect_file_and_word_caps(monkeypatch):
    """Scoring batches stay under BOTH request limits — file count and
    total words (oversized uploads time out inside the API); a single
    overweight document still ships alone."""
    import gz
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "BATCH_FILES", 3)
    monkeypatch.setattr(gzc, "BATCH_WORDS", 1000)
    rows = [{"words": w} for w in (400, 400, 400, 900, 1500, 100)]
    got = gz._batches(rows)
    assert [[r["words"] for r in b] for b in got] == \
        [[400, 400], [400], [900], [1500], [100]]
    assert all(len(b) <= 3 for b in got)


def test_default_transports_resolve_at_call_time(tmp_path, monkeypatch):
    """No-network-guard bypass: score()/score_batch() bound their live
    transports as import-time default arguments, so calls that omit the
    transport (the cmd paths) sidestepped the autouse guard and reached
    the live API from tests. Defaults must resolve the module attribute
    at call time."""
    import gptzero_client as gzc
    monkeypatch.setattr(gzc.subprocess, "run", lambda *a, **k:
                        (_ for _ in ()).throw(RuntimeError("live curl")))
    monkeypatch.setattr(gzc.time, "sleep", lambda s: None)
    with pytest.raises(AssertionError, match="live GPTZero call"):
        gzc.score("shaX", "one two", tmp_path / "cache",
                  tmp_path / "resv.jsonl")
    p = tmp_path / "shaY.txt"
    p.write_text("one two")
    with pytest.raises(AssertionError, match="live GPTZero call"):
        gzc.score_batch([("shaY", p)], tmp_path / "cache",
                        tmp_path / "resv.jsonl")


def _rt(slot, sha600, p, cls, arm="P", ai=True, cap=1200,
        truncated=False):
    return {"slot": slot, "arm": arm, "ai": ai, "period": "Q2-2026",
            "sha600": sha600, "doc_sha": f"{sha600}:long",
            "word_cap": cap, "truncated": truncated,
            "class_probabilities": {"ai": p}, "predicted_class": cls,
            "model_version": "pinver"}


def _v1(slot, sha, p, cls, arm="P", ai=True):
    return {"slot": slot, "arm": arm, "ai": ai, "period": "Q2-2026",
            "doc_sha": sha, "class_probabilities": {"ai": p},
            "predicted_class": cls, "truncated": True,
            "model_version": "pinver"}


def test_fetch_diff_survives_non_utf8_diffs(tmp_path, monkeypatch):
    """Stage-2 fetch crash 2026-08-04: a PR diff containing non-UTF-8
    bytes (0xb3) aborted the whole fetch run inside subprocess text
    decoding. fetch_diff must capture bytes, decode with replacement,
    and serve the same text from the cache on the next call."""
    raw = (b"diff --git a/f.c b/f.c\n+++ b/f.c\n"
           b"@@ -0,0 +1 @@\n+x \xb3 y\n")
    monkeypatch.setattr(
        diffs.subprocess, "run",
        lambda *a, **k: diffs.subprocess.CompletedProcess(
            a, 0, stdout=raw, stderr=b""))
    monkeypatch.setattr(diffs.time, "sleep", lambda s: None)
    got = diffs.fetch_diff("o/r", 1, tmp_path)
    assert "�" in got and "+x" in got
    assert diffs.fetch_diff("o/r", 1, tmp_path) == got  # cache round-trip


def test_retest_stats_pair_by_slot_and_source_sha():
    """Dose-response pairs bind by slot AND the design-cap doc_sha the
    retest row was built from: a redrawn document never pairs across
    assemblies, and deltas/flips are computed over true pairs only."""
    rows = [_v1("s1", "aaa", 0.2, "human"),
            _v1("s2", "bbb", 0.9, "ai"),
            _v1("s3", "ccc", 0.5, "human")]
    rt = [_rt("s1", "aaa", 0.7, "ai"),
          _rt("s2", "bbb", 0.8, "ai"),
          _rt("s3", "STALE", 0.1, "human")]      # redrawn: must not pair
    s = analyze.retest_stats(rows, rt, lambda r: r["arm"] == "P")
    assert s["n"] == 2
    assert s["mean_delta"] == pytest.approx((0.5 - 0.1) / 2)
    assert (s["wins"], s["losses"]) == (1, 1)
    assert s["flips"] == {"human->ai": 1}


def test_retest_command_targets_truncated_scored_docs_only(
        tmp_path, monkeypatch):
    """--retest re-assembles at RETEST_CAP exactly the filled, TRUNCATED
    docs whose current document is scored; untruncated and unscored docs
    are excluded, and already-retested slots are not re-billed."""
    import gz
    for name in ("LOCAL", "DOCS", "DOCS_RETEST", "RESULTS",
                 "RESULTS_RETEST", "DIFF_CACHE", "DOC_CACHE",
                 "RESP_CACHE", "RESERVATIONS"):
        monkeypatch.setattr(gz, name, tmp_path / getattr(gz, name).name)
    (tmp_path / "results").mkdir()
    monkeypatch.setattr(gz, "RESULTS",
                        tmp_path / "results" / "scores_v1.jsonl")
    monkeypatch.setattr(gz, "RESULTS_RETEST",
                        tmp_path / "results" / "scores_retest.jsonl")
    monkeypatch.setattr(gz, "RESERVATIONS",
                        tmp_path / "results" / "resv.jsonl")
    docrow = {"slot": "P:a:ai", "arm": "P", "author": "a",
              "period": "Q2-2026", "ai": True, "repo": "o/r", "num": 1,
              "doc_sha": "sha600", "words": 600, "truncated": True,
              "word_cap": 600, "word_floor": 100}
    unt = {**docrow, "slot": "P:a:nonai", "num": 2, "doc_sha": "shaU",
           "truncated": False}
    gz.DOCS.write_text(json.dumps(docrow) + "\n" + json.dumps(unt) + "\n")
    gz.RESULTS.write_text(json.dumps(
        {"slot": "P:a:ai", "doc_sha": "sha600",
         "model_version": "pinver"}) + "\n")
    import diffs as diffs_mod
    monkeypatch.setattr(diffs_mod, "fetch_diff",
                        lambda repo, num, cache: "RAW")
    monkeypatch.setattr(diffs_mod, "parse_diff", lambda raw: raw)
    monkeypatch.setattr(
        diffs_mod, "build_document",
        lambda parsed, cap, floor: ("long text " * 3,
                                    {"words": 6, "truncated": False}))
    import gptzero_client as gzc
    monkeypatch.setattr(gzc, "PINNED_VERSION", "pinver")
    sent = []

    def transport(paths):
        sent.append([p.name for p in paths])
        return _batch_resp([p.stem for p in paths], version="pinver")

    monkeypatch.setattr(gzc, "_post_files_once", transport)
    gz.cmd_retest()
    assert len(sent) == 1 and len(sent[0]) == 1     # truncated doc only
    out = [json.loads(ln) for ln in
           gz.RESULTS_RETEST.read_text().splitlines()]
    assert [r["slot"] for r in out] == ["P:a:ai"]
    assert out[0]["sha600"] == "sha600"
    assert out[0]["word_cap"] == gz.RETEST_CAP
    sent.clear()
    gz.cmd_retest()                                  # idempotent resume
    assert sent == []


def _freeze_env(tmp_path, monkeypatch):
    """Minimal coherent corpus for cmd_freeze: one filled+scored doc
    with its cached response and document text, all manifests
    present."""
    import b3
    import gz
    for name in ("LOCAL", "MANIFEST", "MANIFEST_B3", "MANIFEST_ERAS",
                 "MANIFEST_PC", "DOCS", "DOCS_RETEST", "RESULTS",
                 "RESULTS_RETEST", "RESULTS_SEM", "DOCS_NEWFILE",
                 "RESULTS_SEM_NF", "RESULTS_SEM_NF_FULL", "RESULTS_NF",
                 "RESERVATIONS", "RESP_CACHE", "DOC_CACHE"):
        monkeypatch.setattr(gz, name, tmp_path / getattr(gz, name).name)
    monkeypatch.setattr(gz, "FROZEN", tmp_path / "frozen")
    monkeypatch.setattr(gptzero_client, "PINNED_VERSION", "pinver")
    gz.MANIFEST_B3.write_text(json.dumps(
        {"slots": [{"slot": "B3:o/r"}],
         "params": {**b3.B3_PARAMS, "word_cap": 600,
                    "word_floor": 100}}))
    for m, params in ((gz.MANIFEST, sampling.PARAMS),
                      (gz.MANIFEST_ERAS, eras.PARAMS),
                      (gz.MANIFEST_PC, pc.PARAMS)):
        m.write_text(json.dumps({"slots": [], "params": params}))
    gz.DOCS.write_text(json.dumps(
        {"slot": "B3:o/r", "arm": "B3", "ai": False, "period": "Q3-2022",
         "doc_sha": "s", "words": 200, "truncated": True}) + "\n")
    gz.RESULTS.write_text(json.dumps(
        {"slot": "B3:o/r", "arm": "B3", "ai": False, "period": "Q3-2022",
         "author": "dev", "doc_sha": "s", "words": 200,
         "truncated": True,
         "class_probabilities": {"ai": 0.1, "mixed": 0.02},
         "predicted_class": "human",
         "model_version": "pinver"}) + "\n")
    gz.DOC_CACHE.mkdir(parents=True)
    (gz.DOC_CACHE / "s.txt").write_text(
        "// file: src/a.py\ncode\n// file: b.rs\ncode\n"
        "// file: c.py\ncode\n")
    resp = tmp_path / gz.RESP_CACHE.name / "pinver" / "s.json"
    resp.parent.mkdir(parents=True)
    resp.write_text(json.dumps({"version": "pinver", "documents": [
        {"predicted_class": "human",
         "class_probabilities": {"ai": 0.1, "mixed": 0.02},
         "paragraphs": [{"completely_generated_prob": 0.8},
                        {"completely_generated_prob": 0.1}]}]}))
    return gz


NEWFILE_DIFF = """\
diff --git a/src/old.py b/src/old.py
+++ b/src/old.py
@@ -1,2 +1,3 @@
+modified_existing_file = True
diff --git a/src/created.py b/src/created.py
new file mode 100644
+++ b/src/created.py
@@ -0,0 +1,3 @@
+def whole():
+    return "file"
+CREATED = True
diff --git a/vendor/lib.js b/vendor/lib.js
new file mode 100644
+++ b/vendor/lib.js
@@ -0,0 +1 @@
+vendored = 1
diff --git a/docs/readme.md b/docs/readme.md
new file mode 100644
+++ b/docs/readme.md
@@ -0,0 +1 @@
+prose, not code
"""


def test_created_files_are_new_code_files_only():
    """Only `new file mode` blocks count (edits to existing files are
    not whole files), and the allowlist/vendored filters apply."""
    got = newfile.created_files(NEWFILE_DIFF)
    assert [p for p, _t in got] == ["src/created.py"]
    assert got[0][1] == 'def whole():\n    return "file"\nCREATED = True\n'


def test_newfile_rows_pick_largest_eligible_and_cap(tmp_path,
                                                    monkeypatch):
    """One row per slot: the LARGEST created code file above the
    floor, with capped and full variants cached; slots whose PRs
    created no eligible file yield nothing."""
    monkeypatch.setattr(newfile, "WORD_FLOOR", 3)
    monkeypatch.setattr(newfile, "WORD_CAP", 5)
    diff_cache = tmp_path / "diffs"
    diff_cache.mkdir()
    (diff_cache / "o~r@1.diff").write_text(NEWFILE_DIFF)
    (diff_cache / "o~r@2.diff").write_text(
        "diff --git a/a.py b/a.py\n+++ b/a.py\n+edit_only = 1\n")
    docs = [{"slot": "P:a:ai", "arm": "P", "author": "a",
             "period": "Q2-2026", "ai": True, "repo": "o/r", "num": 1},
            {"slot": "P:b:ai", "arm": "P", "author": "b",
             "period": "Q2-2026", "ai": True, "repo": "o/r", "num": 2}]
    rows = newfile.build_rows(docs, diff_cache, tmp_path / "cache")
    assert [r["slot"] for r in rows] == ["P:a:ai"]
    r = rows[0]
    assert r["path"] == "src/created.py"
    assert r["truncated"] and r["words"] == 5
    assert r["words_full"] == 10   # 3-word header + 7-word file
    capped = (tmp_path / "cache" / f"{r['doc_sha']}.txt").read_text()
    full = (tmp_path / "cache" / f"{r['doc_sha_full']}.txt").read_text()
    assert full.startswith("// file: src/created.py\n")
    assert capped == " ".join(full.split()[:5])


def test_report_newfile_renders_without_gptzero_rows(capsys):
    """Live finding 2026-08-05: --report-newfile crashed formatting the
    absent GPTZero mean (None) before the billed pass ran. Unscored
    detector columns render as dashes, never TypeError."""
    nf = [{"slot": "P:a:ai", "arm": "P", "period": "Q2-2026",
           "author": "a", "ai": True, "doc_sha": "s", "words": 100,
           "truncated": False}]
    sem = [{"slot": "P:a:ai", "sem_pred": "ai",
            "sem_probs": {"human": 0.1, "ai": 0.7, "hybrid": 0.1,
                          "adversarial": 0.1}}]
    analyze.report_newfile(nf, sem, sem, [])
    out = capsys.readouterr().out
    assert "Q2-26-AI" in out and "TypeError" not in out
    assert "—" in out


ABL_DOC = """\
// file: src/a.py
# a real comment explaining the thing
def f(x):
    return x + 1
// file: src/b.js
// another comment line here
const y = 2;
"""


def test_ablation_split_separates_streams_and_drops_headers():
    """Variants are code-only and comments-only; the `// file:`
    headers belong to the document format and enter neither stream."""
    code, comment = ablation.split_document(ABL_DOC)
    assert "// file:" not in code and "// file:" not in comment
    assert "def f(x):" in code and "const y = 2;" in code
    assert "a real comment" in comment and "another comment" in comment
    assert "def f(x):" not in comment and "a real comment" not in code


def test_ablation_rows_are_paired_floored_and_deterministic(
        tmp_path, monkeypatch):
    """Two variants per selected document, each carrying its parent
    doc_sha for within-document pairing; documents whose variants fall
    under the floor are skipped; selection is seeded and stable."""
    monkeypatch.setattr(ablation, "WORD_FLOOR", 3)
    monkeypatch.setattr(ablation, "N_PER_GROUP", 1)
    cache = tmp_path / "docs"
    cache.mkdir()
    rich = ABL_DOC
    thin = "// file: t.py\nx = 1\n"          # no comments -> ineligible
    scores = []
    for i, (sha, text, arm, period) in enumerate((
            ("sha1", rich, "B3", "Q3-2022"),
            ("sha2", rich, "P", "Q2-2026"),
            ("sha3", thin, "P", "Q2-2026"))):
        (cache / f"{sha}.txt").write_text(text)
        scores.append({"slot": f"s{i}", "arm": arm, "author": "a",
                       "period": period, "ai": True, "repo": "o/r",
                       "num": i, "doc_sha": sha})
    rows = ablation.build_rows(scores, cache)
    assert rows == ablation.build_rows(scores, cache)   # deterministic
    assert {r["slot"] for r in rows} == {"s0", "s1"}    # thin excluded
    assert sorted(r["variant"] for r in rows) == [
        "code", "code", "comment", "comment"]
    assert {r["group"] for r in rows} == {"baseline", "Q2-2026"}
    for r in rows:
        assert r["parent_doc_sha"] in {"sha1", "sha2"}
        assert (cache / f"{r['doc_sha']}.txt").is_file()


def test_ablation_stats_pair_within_document():
    """Variants bind to the parent's CURRENT doc_sha; a variant whose
    parent was redrawn never pairs, and both variants are required."""
    rows = [{"slot": "s1", "doc_sha": "d1",
             "class_probabilities": {"ai": 0.8}},
            {"slot": "s2", "doc_sha": "d2",
             "class_probabilities": {"ai": 0.6}}]

    def v(slot, parent, variant, p, group="Q2-2026"):
        return {"slot": slot, "parent_doc_sha": parent,
                "variant": variant, "group": group,
                "class_probabilities": {"ai": p}}
    abl = [v("s1", "d1", "code", 0.2), v("s1", "d1", "comment", 0.9),
           v("s2", "STALE", "code", 0.1),
           v("s2", "STALE", "comment", 0.1)]
    got = ablation_groups = analyze.ablation_stats(rows, abl)
    assert set(got) == {"Q2-2026"}
    assert len(ablation_groups["Q2-2026"]) == 1
    e = got["Q2-2026"][0]
    assert (e["orig"], e["code"], e["comment"]) == (0.8, 0.2, 0.9)


def test_sem13c_inference_version_invalidates_cached_rows(tmp_path):
    """PR #29 round-2 review P1: inference preprocessing changed (pad
    to 4096 before chunking, matching the authors' published path), but
    the resume key was (slot, doc_sha, model_revision) — every stale
    row would have been treated as valid. Rows scored under a different
    (or absent) inference version must be rescored, and sem_bound must
    exclude them."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "s1.txt").write_text("code()")
    rows = [{"slot": "P:a:ai", "arm": "P", "author": "a",
             "period": "Q2-2026", "ai": True, "doc_sha": "s1",
             "words": 100, "truncated": False}]
    out = tmp_path / "sem.jsonl"
    stale = {"slot": "P:a:ai", "arm": "P", "author": "a",
             "period": "Q2-2026", "ai": True, "doc_sha": "s1",
             "sem_probs": {"human": 1.0, "ai": 0.0, "hybrid": 0.0,
                           "adversarial": 0.0}, "sem_pred": "human",
             "model_revision": sem13c.HF_REVISION}   # no inference key
    out.write_text(json.dumps(stale) + "\n")
    calls = []

    def stub(text):
        calls.append(text)
        return {"human": 0.0, "ai": 1.0, "hybrid": 0.0,
                "adversarial": 0.0}

    assert sem13c.score_rows(rows, docs_dir, out, predictor=stub) == 1
    assert len(calls) == 1                    # stale row NOT trusted
    scored = [json.loads(ln) for ln in out.read_text().splitlines()]
    assert scored[-1]["inference"] == sem13c.INFERENCE
    current = [{"slot": "P:a:ai", "doc_sha": "s1"}]
    bound = analyze.sem_bound(current, scored,
                              inference=sem13c.INFERENCE)
    assert len(bound) == 1 and bound[0]["sem_pred"] == "ai"


def test_sem13c_scores_resume_and_bind(tmp_path):
    """The sem13c scorer appends one row per (slot, doc_sha) under the
    pinned revision, skips already-scored docs on re-run, and
    sem_bound keeps only rows matching each slot's CURRENT document —
    redrawn docs age out instead of double-counting."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    rows = []
    for sha, slot in (("s1", "P:a:ai"), ("s2", "P:a:nonai")):
        (docs_dir / f"{sha}.txt").write_text("code()")
        rows.append({"slot": slot, "arm": "P", "author": "a",
                     "period": "Q2-2026", "ai": slot.endswith(":ai"),
                     "doc_sha": sha, "words": 100, "truncated": False})
    calls = []

    def stub(text):
        calls.append(text)
        return {"human": 0.1, "ai": 0.6, "hybrid": 0.2,
                "adversarial": 0.1}

    out = tmp_path / "sem.jsonl"
    assert sem13c.score_rows(rows, docs_dir, out, predictor=stub) == 2
    assert sem13c.score_rows(rows, docs_dir, out, predictor=stub) == 0
    assert len(calls) == 2                      # resume: no rescoring
    scored = [json.loads(ln) for ln in out.read_text().splitlines()]
    assert scored[0]["sem_pred"] == "ai"
    assert scored[0]["model_revision"] == sem13c.HF_REVISION
    current = [{"slot": "P:a:ai", "doc_sha": "s1"},
               {"slot": "P:a:nonai", "doc_sha": "REDRAWN"}]
    bound = analyze.sem_bound(current, scored)
    assert [r["slot"] for r in bound] == ["P:a:ai"]


def test_score_newfile_refuses_unpinned(tmp_path, monkeypatch):
    """PR #29 round-2 review P2: the created-file billed pass could
    run the whole arm with PINNED_VERSION = None (no smoke-run limit
    exists on this path). It must refuse before rewriting results or
    issuing any API call."""
    import gz
    monkeypatch.setattr(gz, "DOCS_NEWFILE",
                        tmp_path / "docs_newfile.jsonl")
    monkeypatch.setattr(gz, "RESULTS_NF", tmp_path / "scores_nf.jsonl")
    gz.DOCS_NEWFILE.write_text(json.dumps(
        {"slot": "P:a:ai", "arm": "P", "author": "a",
         "period": "Q2-2026", "ai": True, "doc_sha": "s",
         "words": 100}) + "\n")
    monkeypatch.setattr(gptzero_client, "PINNED_VERSION", None)
    with pytest.raises(SystemExit, match="pin"):
        gz.cmd_score_newfile()
    assert not gz.RESULTS_NF.exists()


def test_freeze_refuses_stale_design_manifests(tmp_path, monkeypatch):
    """PR #29 round-2 review P1: source PARAMS and frozen manifests
    could describe different experiments (code n_q1=60 vs manifest 20)
    and --freeze validated only internal consistency. A manifest whose
    recorded params differ from the current module PARAMS must refuse
    the freeze until resampled."""
    gz = _freeze_env(tmp_path, monkeypatch)
    gz.cmd_freeze()                                # matching: passes
    m = json.loads(gz.MANIFEST.read_text())
    m["params"] = {**m["params"], "n_q1": 999}
    gz.MANIFEST.write_text(json.dumps(m))
    with pytest.raises(SystemExit, match="design"):
        gz.cmd_freeze()


def test_freeze_requires_complete_sem_coverage(tmp_path, monkeypatch):
    """PR #29 round-2 review P2: sem13c results were optional and
    unversioned at freeze time while the report's conclusion was
    unconditional. When a sem results file exists, every frozen score
    row needs exactly one bound current-inference sem row, else the
    freeze refuses."""
    gz = _freeze_env(tmp_path, monkeypatch)

    def sem_row(sha):
        return {"slot": "B3:o/r", "arm": "B3", "period": "Q3-2022",
                "ai": False, "author": "dev", "doc_sha": sha,
                "sem_pred": "human",
                "sem_probs": {"human": 1.0, "ai": 0.0, "hybrid": 0.0,
                              "adversarial": 0.0},
                "model_revision": sem13c.HF_REVISION,
                "inference": sem13c.INFERENCE}

    gz.RESULTS_SEM.write_text(json.dumps(sem_row("STALE")) + "\n")
    with pytest.raises(SystemExit, match="sem13c"):
        gz.cmd_freeze()
    gz.RESULTS_SEM.write_text(json.dumps(sem_row("s")) + "\n")
    gz.cmd_freeze()                                # complete: passes
    assert (gz.FROZEN / "scores_sem13c.jsonl").is_file()
    assert "sem13c" in (gz.FROZEN / "report.txt").read_text()


def test_sem_bound_requires_current_revision():
    """PR #29 round-3 review P1: binding filtered only the inference
    version and kept the first matching row, so a row from an older
    HF_REVISION could pass and mask the current row. Binding requires
    the exact (revision, inference) pair."""
    current = [{"slot": "s", "doc_sha": "d"}]
    stale = {"slot": "s", "doc_sha": "d", "sem_pred": "human",
             "model_revision": "OLD", "inference": sem13c.INFERENCE}
    fresh = {**stale, "model_revision": sem13c.HF_REVISION,
             "sem_pred": "ai"}
    bound = analyze.sem_bound(current, [stale, fresh],
                              inference=sem13c.INFERENCE,
                              revision=sem13c.HF_REVISION)
    assert [r["sem_pred"] for r in bound] == ["ai"]


def test_freeze_refuses_duplicate_and_incomplete_nf_artifacts(
        tmp_path, monkeypatch):
    """PR #29 round-3 review P1: duplicate current sem rows passed the
    coverage check, the created-file billed results were copied without
    coverage/version validation, and the two created-file sem variants
    were independently optional. With DOCS_NEWFILE present both sem
    variants are required; RESULTS_NF, when present, needs exactly one
    current-document row per created-file doc under PINNED_VERSION."""
    gz = _freeze_env(tmp_path, monkeypatch)

    def sem_row(slot, sha):
        return {"slot": slot, "arm": "B3", "period": "Q3-2022",
                "ai": False, "author": "dev", "doc_sha": sha,
                "sem_pred": "human",
                "sem_probs": {"human": 1.0, "ai": 0.0, "hybrid": 0.0,
                              "adversarial": 0.0},
                "model_revision": sem13c.HF_REVISION,
                "inference": sem13c.INFERENCE}

    gz.RESULTS_SEM.write_text(json.dumps(sem_row("B3:o/r", "s")) + "\n"
                              + json.dumps(sem_row("B3:o/r", "s"))
                              + "\n")                 # duplicate current
    with pytest.raises(SystemExit, match="duplicate"):
        gz.cmd_freeze()
    gz.RESULTS_SEM.write_text(json.dumps(sem_row("B3:o/r", "s")) + "\n")

    nf = {"slot": "B3:o/r", "arm": "B3", "period": "Q3-2022",
          "ai": False, "author": "dev", "repo": "o/r", "num": 1,
          "path": "a.py", "doc_sha": "nfc", "words": 150,
          "truncated": False, "doc_sha_full": "nff", "words_full": 200}
    gz.DOCS_NEWFILE.write_text(json.dumps(nf) + "\n")
    with pytest.raises(SystemExit, match="newfile"):
        gz.cmd_freeze()                    # sem NF variants required
    for path, sha in ((gz.RESULTS_SEM_NF, "nfc"),
                      (gz.RESULTS_SEM_NF_FULL, "nff")):
        path.write_text(json.dumps(sem_row("B3:o/r", sha)) + "\n")
    gz.cmd_freeze()                        # complete: passes

    bad_nf = {**nf, "doc_sha": "STALE", "predicted_class": "human",
              "model_version": "pinver", "billed_words": 150}
    gz.RESULTS_NF.write_text(json.dumps(bad_nf) + "\n")
    with pytest.raises(SystemExit, match="created-file"):
        gz.cmd_freeze()                    # stale doc_sha refused
    good_nf = {**bad_nf, "doc_sha": "nfc", "model_version": "OTHER"}
    gz.RESULTS_NF.write_text(json.dumps(good_nf) + "\n")
    with pytest.raises(SystemExit, match="created-file"):
        gz.cmd_freeze()                    # wrong pin refused
    gz.RESULTS_NF.write_text(json.dumps(
        {**good_nf, "model_version": "pinver"}) + "\n")
    gz.cmd_freeze()
    assert (gz.FROZEN / gz.RESULTS_NF.name).is_file()


def test_freeze_failure_preserves_previous_snapshot(
        tmp_path, monkeypatch):
    """PR #29 round-3 review P2: frozen/ was removed before the sem and
    created-file validations ran, so a late refusal destroyed the prior
    audit set. Freeze stages into a temporary directory and replaces
    the snapshot only after every validation passes."""
    gz = _freeze_env(tmp_path, monkeypatch)
    gz.cmd_freeze()
    marker = (gz.FROZEN / "report.txt").read_text()
    gz.RESULTS_SEM.write_text(json.dumps(
        {"slot": "B3:o/r", "doc_sha": "STALE", "sem_pred": "human",
         "sem_probs": {"human": 1.0, "ai": 0.0, "hybrid": 0.0,
                       "adversarial": 0.0},
         "model_revision": sem13c.HF_REVISION,
         "inference": sem13c.INFERENCE}) + "\n")
    with pytest.raises(SystemExit):
        gz.cmd_freeze()
    assert (gz.FROZEN / "report.txt").read_text() == marker


def test_freeze_swap_failure_preserves_previous_snapshot(
        tmp_path, monkeypatch):
    """PR #29 round-4 review P2: the final swap deleted the previous
    snapshot before renaming the staging directory, so a crash or
    rename failure between the two lost both. The old snapshot must
    survive a failed swap (kept as backup, rolled back on
    exception)."""
    from pathlib import PosixPath
    gz = _freeze_env(tmp_path, monkeypatch)
    gz.cmd_freeze()
    marker = (gz.FROZEN / "report.txt").read_text()

    real_rename = PosixPath.rename

    def flaky(self, target):
        if self.name.endswith(".tmp"):
            raise OSError("simulated rename failure")
        return real_rename(self, target)

    monkeypatch.setattr(PosixPath, "rename", flaky)
    with pytest.raises(OSError, match="simulated"):
        gz.cmd_freeze()
    monkeypatch.setattr(PosixPath, "rename", real_rename)
    assert (gz.FROZEN / "report.txt").read_text() == marker


def test_freeze_writes_the_audit_set(tmp_path, monkeypatch):
    """--freeze snapshots manifests, row files, paragraph summaries,
    the generated report, and provenance into the committed frozen/
    dir — the review artifact for the reported numbers (PR #28 review
    P2), including the paragraph-level heterogeneity claim."""
    gz = _freeze_env(tmp_path, monkeypatch)
    gz.cmd_freeze()
    names = {f.name for f in gz.FROZEN.iterdir()}
    assert {"manifest_v1_50k.json", "scores_v1.jsonl", "report.txt",
            "paragraph_summary.jsonl", "PROVENANCE.md"} <= names
    report = (gz.FROZEN / "report.txt").read_text()
    assert "Q3-22-era" in report
    assert "paragraph-level" in report
    para = [json.loads(ln) for ln in
            (gz.FROZEN / "paragraph_summary.jsonl").read_text()
            .splitlines()]
    assert para[0]["slot"] == "B3:o/r"
    assert para[0]["share_paragraphs_gt50"] == pytest.approx(0.5)
    assert para[0]["author"] == "dev"
    assert para[0]["ai_prob"] == pytest.approx(0.1)
    assert para[0]["dominant_ext"] == ".py"      # 2 .py vs 1 .rs
    assert "pinver" in (gz.FROZEN / "PROVENANCE.md").read_text()


def test_freeze_refuses_incoherent_inputs(tmp_path, monkeypatch):
    """PR #28 review P1: --freeze copied files without validating their
    relationships, committing retest rows detached from current source
    hashes and a report whose denominators disagreed. Freeze must
    refuse: a score row whose doc_sha is not the slot's current
    document, duplicate slots, a filled document with no score, a
    retest row not bound to a current score, and a scored document
    missing its cached response."""
    gz = _freeze_env(tmp_path, monkeypatch)

    def rows(path):
        return [json.loads(ln) for ln in
                path.read_text().splitlines() if ln.strip()]

    def write(path, rs):
        path.write_text("".join(json.dumps(r) + "\n" for r in rs))

    good_results = rows(gz.RESULTS)
    stale = [{**good_results[0], "doc_sha": "OTHER"}]
    write(gz.RESULTS, stale)
    with pytest.raises(SystemExit, match="doc_sha"):
        gz.cmd_freeze()
    write(gz.RESULTS, good_results * 2)          # duplicate slot
    with pytest.raises(SystemExit, match="duplicate"):
        gz.cmd_freeze()
    write(gz.RESULTS, good_results)
    docs = rows(gz.DOCS)
    write(gz.DOCS, docs + [{**docs[0], "slot": "B3:o/x",
                            "doc_sha": "x"}])    # filled, unscored
    with pytest.raises(SystemExit, match="unscored"):
        gz.cmd_freeze()
    write(gz.DOCS, docs)
    write(gz.RESULTS_RETEST, [{**good_results[0], "sha600": "GONE",
                               "doc_sha": "s:long", "word_cap": 1200}])
    with pytest.raises(SystemExit, match="retest"):
        gz.cmd_freeze()
    gz.RESULTS_RETEST.unlink()
    (tmp_path / gz.RESP_CACHE.name / "pinver" / "s.json").unlink()
    with pytest.raises(SystemExit, match="response"):
        gz.cmd_freeze()


def test_freeze_refuses_retest_and_manifest_incoherence(
        tmp_path, monkeypatch):
    """PR #28 review round 3: freeze validated retest SCORES but never
    retest DOCUMENT rows (the detached B3 rows shipped in the frozen
    set), and required manifests without inspecting them. Retest doc
    and score rows must bind one-to-one on (slot, sha600, doc_sha) to a
    current score; document slots must be unique and cover the
    manifests' slots exactly."""
    gz = _freeze_env(tmp_path, monkeypatch)

    def rows(path):
        return [json.loads(ln) for ln in
                path.read_text().splitlines() if ln.strip()]

    def write(path, rs):
        path.write_text("".join(json.dumps(r) + "\n" for r in rs))

    rt_doc = {"slot": "B3:o/r", "arm": "B3", "ai": False,
              "period": "Q3-2022", "sha600": "s", "doc_sha": "s:long",
              "word_cap": 1200, "words": 300, "truncated": False}
    rt_score = {**rt_doc, "class_probabilities": {"ai": 0.2},
                "predicted_class": "human", "model_version": "pinver"}
    write(gz.DOCS_RETEST, [rt_doc])
    write(gz.RESULTS_RETEST, [rt_score])
    gz.cmd_freeze()                                   # coherent: passes

    detached = {**rt_doc, "slot": "B3:o/GONE", "sha600": "nope"}
    write(gz.DOCS_RETEST, [rt_doc, detached])         # doc row extra
    with pytest.raises(SystemExit, match="retest"):
        gz.cmd_freeze()
    write(gz.DOCS_RETEST, [rt_doc])

    docs = rows(gz.DOCS)
    write(gz.DOCS, docs * 2)                          # duplicate doc slot
    with pytest.raises(SystemExit, match="duplicate"):
        gz.cmd_freeze()
    write(gz.DOCS, docs)

    gz.MANIFEST.write_text(json.dumps(
        {"slots": [{"slot": "P:ghost:ai"}],
         "params": sampling.PARAMS}))                 # uncovered manifest
    with pytest.raises(SystemExit, match="manifest"):
        gz.cmd_freeze()
    gz.MANIFEST.write_text(json.dumps({"slots": [],
                                       "params": sampling.PARAMS}))

    # PR #28 review round 4: same slot twice with DIFFERENT long-doc
    # hashes, mirrored in both retest files — full-tuple uniqueness and
    # the set comparison both accepted it, double-counting the source
    # document. Uniqueness must hold per slot in each file.
    twin = {**rt_doc, "doc_sha": "s:long2"}
    twin_score = {**rt_score, "doc_sha": "s:long2"}
    write(gz.DOCS_RETEST, [rt_doc, twin])
    write(gz.RESULTS_RETEST, [rt_score, twin_score])
    with pytest.raises(SystemExit, match="duplicate"):
        gz.cmd_freeze()
    write(gz.DOCS_RETEST, [rt_doc])
    write(gz.RESULTS_RETEST, [rt_score])

    # duplicate slot definitions across manifests must refuse, not
    # silently collapse into the coverage set
    gz.MANIFEST.write_text(json.dumps({"slots": [{"slot": "B3:o/r"}],
                                       "params": sampling.PARAMS}))
    with pytest.raises(SystemExit, match="duplicate"):
        gz.cmd_freeze()


def _eras_pools(q4=("alice", "bob"), q1_26=("alice",),
                q2_26=("carol", "dana")):
    def entry():
        return {"ai": [("o/r", 1, 100), ("o/r", 3, 200)],
                "nonai": [("o/r", 2, 100)]}
    return {"Q4-2025": {a: entry() for a in q4},
            "Q1-2026": {a: entry() for a in q1_26},
            "Q2-2026": {a: entry() for a in q2_26}}


def test_eras_draw_quarter_slots_deterministic_and_independent():
    """Each quarter draws its own paired slots (quarter-qualified ids,
    one slot per arm per author); the draw is deterministic and one
    quarter's pool never influences another quarter's slots."""
    p = _eras_pools()
    slots = eras.draw(p)
    assert slots == eras.draw(p)
    assert {s["slot"] for s in slots} == {
        "P:Q4-2025:alice:ai", "P:Q4-2025:alice:nonai",
        "P:Q4-2025:bob:ai", "P:Q4-2025:bob:nonai",
        "P:Q1-2026:alice:ai", "P:Q1-2026:alice:nonai",
        "P:Q2-2026:carol:ai", "P:Q2-2026:carol:nonai",
        "P:Q2-2026:dana:ai", "P:Q2-2026:dana:nonai"}
    assert all(s["arm"] == "P" and s["period"] in eras.QUARTERS
               for s in slots)
    q1_before = [s for s in slots if s["period"] == "Q1-2026"]
    p2 = _eras_pools(q4=("alice", "bob", "carol"))
    q1_after = [s for s in eras.draw(p2) if s["period"] == "Q1-2026"]
    assert q1_after == q1_before


def test_eras_deepening_keeps_existing_slots_and_exclusions_hold(
        monkeypatch):
    """Raising n_authors deepens a quarter without redrawing its
    existing slots (whole-pool shuffle, then a prefix); excluded
    authors (the v1 Q2-2026 draw) never appear and reduce the quarter's
    target so the pooled quarter still totals n_authors pairs."""
    pool = _eras_pools(q2_26=("carol", "dana", "erin", "fred"))
    monkeypatch.setitem(eras.PARAMS, "quarter_targets", {})
    monkeypatch.setitem(eras.PARAMS, "n_authors", 2)
    shallow = [s for s in eras.draw(pool) if s["period"] == "Q4-2025"]
    monkeypatch.setitem(eras.PARAMS, "n_authors", 3)
    deep = [s for s in eras.draw(pool) if s["period"] == "Q4-2025"]
    assert deep[:len(shallow)] == shallow      # prefix-stable deepening
    excl = {"Q2-2026": {"carol", "erin"}}
    q2 = [s for s in eras.draw(pool, excl) if s["period"] == "Q2-2026"]
    assert {s["author"] for s in q2}.isdisjoint(excl["Q2-2026"])
    # 2 excluded authors in-pool -> target 3 - 2 = 1 author (2 slots)
    assert len(q2) == 2
    fp = eras.fingerprint(pool, excl)
    assert fp != eras.fingerprint(pool)
    assert fp != eras.fingerprint(pool, {"Q2-2026": {"carol"}})


def test_eras_draw_skips_unmixed_authors_and_caps_depth(monkeypatch):
    monkeypatch.setitem(eras.PARAMS, "quarter_targets", {})
    p = _eras_pools()
    p["Q4-2025"]["aionly"] = {"ai": [("o/r", 9, 100)], "nonai": []}
    assert not [s for s in eras.draw(p) if s["author"] == "aionly"]
    monkeypatch.setitem(eras.PARAMS, "n_authors", 1)
    q4 = [s for s in eras.draw(p) if s["period"] == "Q4-2025"]
    assert len(q4) == 2 and len({s["author"] for s in q4}) == 1


def test_eras_manifest_fingerprint_tracks_pools(tmp_path):
    p = _eras_pools()
    fp = eras.fingerprint(p)
    p2 = _eras_pools(q1_26=("alice", "newcomer"))
    assert eras.fingerprint(p2) != fp
    path = tmp_path / "m.json"
    _, rewrote = eras.ensure_manifest(p, path)
    assert rewrote
    _, rewrote = eras.ensure_manifest(p, path)
    assert not rewrote
    tampered = json.loads(path.read_text())
    tampered["slots"] = tampered["slots"][:-1]
    path.write_text(json.dumps(tampered))
    _, rewrote = eras.ensure_manifest(p, path)
    assert rewrote


def test_pc_pools_admit_only_canonical_agents(monkeypatch):
    """PR #29 review P1: the control admitted ANY bot-like author with
    AI evidence — 9/22 scored rows were Dependabot/Actions/Stainless
    automation, not coding agents, so the known-AI claim wasn't
    licensed. Eligibility is the canonical layer-B classification
    (cls.agent_author / AGENT_PR_AUTHORS): a Dependabot PR carrying an
    AI marker, human-authored AI PRs, and unmerged agent PRs never
    enter."""
    from pipeline import frame

    def agent_pr(num, merged="2026-04-05T00:00:00Z"):
        p = _pr("2026-04-01T00:00:00Z", merged, num,
                login="devin-ai-integration[bot]", msg=CLAUDE_MARK)
        p["author"]["__typename"] = "Bot"
        if merged is None:
            p["mergedBy"] = None
        return p

    cells = {("o/r", "2026-04-01..2026-06-30"): [
        agent_pr(1),
        _q2(2, login="alice", msg=CLAUDE_MARK),      # human AI: excluded
        _q2(3, login="dependabot[bot]"),             # bot, not AI
        _q2(4, login="dependabot[bot]", msg=CLAUDE_MARK),  # bot + marker:
        # still NOT a coding agent — the review's misclassification
        agent_pr(9, merged=None)]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    p = pc.pools()
    assert set(p["Q2-2026"]) == {("devin-ai-integration", "o/r")}
    assert p["Q2-2026"][("devin-ai-integration", "o/r")] == \
        [("o/r", 1, 100)]
    assert p["Q1-2026"] == {}


def test_pc_draw_targets_per_agent_with_group_deepening():
    """pc-v2: each agent aims for n_per_agent_quarter documents per
    quarter — repo-diverse agents get one slot per group; concentrated
    agents deepen already-selected groups (up to per_group, disjoint
    candidate chunks). Slot 0 keeps the pc-v1 id and candidate list so
    scored documents survive the deepening."""
    from collections import Counter
    diverse = {("botA", f"o/r{i}"): [(f"o/r{i}", 1, 100)]
               for i in range(10)}
    rich = [("o/z", n, 100) for n in range(1, 21)]     # 20 PRs, 1 repo
    pools_ = {"Q4-2025": {}, "Q1-2026": {},
              "Q2-2026": {**diverse, ("botB", "o/z"): rich}}
    slots = pc.draw(pools_)
    assert slots == pc.draw(pools_)
    per = Counter(s["author"] for s in slots)
    assert per["botA"] == pc.PARAMS["n_per_agent_quarter"]
    # botB: 1 group -> slot 0 plus per_group-1 deepened slots
    b = [s for s in slots if s["author"] == "botB"]
    assert len(b) == pc.PARAMS["per_group"]
    assert b[0]["slot"] == "PC:Q2-2026:botB:o/z"
    assert {s["slot"] for s in b[1:]} == {
        "PC:Q2-2026:botB:o/z:1", "PC:Q2-2026:botB:o/z:2"}
    chunks = [{tuple(c) for c in s["candidates"]} for s in b]
    assert len(b[0]["candidates"]) == pc.PARAMS["k_cand"]
    assert all(len(c) == pc.PARAMS["extra_cand"] for c in chunks[1:])
    assert not (chunks[0] | chunks[1]) & chunks[2] \
        and not chunks[0] & chunks[1]                # disjoint
    # a thin group (few PRs) never yields empty extra slots
    pools_["Q2-2026"][("botC", "o/t")] = [("o/t", 1, 100),
                                          ("o/t", 2, 90)]
    thin = [s for s in pc.draw(pools_) if s["author"] == "botC"]
    assert len(thin) == 1                            # 2 PRs < k_cand+1
    fp = pc.fingerprint(pools_)
    pools_["Q2-2026"][("botD", "o/y")] = [("o/y", 9, 100)]
    assert pc.fingerprint(pools_) != fp


def test_pc_agent_targets_override_default(monkeypatch):
    """Deep-pool agents take their agent_targets quota while default
    agents keep n_per_agent_quarter; raising a target only APPENDS
    slots (existing ids and candidate chunks unchanged)."""
    from collections import Counter
    prs = [("o/z", n, 100) for n in range(1, 30)]
    pools_ = {"Q4-2025": {}, "Q1-2026": {},
              "Q2-2026": {("deep", f"o/r{i}"): [(f"o/r{i}", 1, 100)]
                          for i in range(12)}}
    pools_["Q2-2026"][("shallow", "o/z")] = prs
    pools_["Q2-2026"][("shallow", "o/y")] = [("o/y", n, 100)
                                             for n in range(1, 30)]
    monkeypatch.setitem(pc.PARAMS, "agent_targets", {"deep": 10})
    slots = pc.draw(pools_)
    per = Counter(s["author"] for s in slots)
    assert per["deep"] == 10
    assert per["shallow"] == pc.PARAMS["n_per_agent_quarter"]
    monkeypatch.setitem(pc.PARAMS, "agent_targets", {"deep": 4})
    fewer = [s for s in pc.draw(pools_) if s["author"] == "deep"]
    more = [s for s in slots if s["author"] == "deep"]
    assert more[:len(fewer)] == fewer          # deepening appends only


def test_eras_quarter_targets_override_and_deepen(monkeypatch):
    """quarter_targets raises one quarter's author target without
    touching others, and the deepened draw keeps the shallower draw as
    a prefix."""
    pool = _eras_pools(q4=tuple(f"a{i}" for i in range(8)))
    monkeypatch.setitem(eras.PARAMS, "n_authors", 2)
    monkeypatch.setitem(eras.PARAMS, "quarter_targets", {})
    shallow = [s for s in eras.draw(pool) if s["period"] == "Q4-2025"]
    assert len({s["author"] for s in shallow}) == 2
    monkeypatch.setitem(eras.PARAMS, "quarter_targets", {"Q4-2025": 5})
    deep = [s for s in eras.draw(pool) if s["period"] == "Q4-2025"]
    assert len({s["author"] for s in deep}) == 5
    assert deep[:len(shallow)] == shallow
    q1 = [s for s in eras.draw(pool) if s["period"] == "Q1-2026"]
    assert len({s["author"] for s in q1}) <= 2   # others keep default


def test_b2_deepening_keeps_membership_prefix():
    """B2 draws by whole-pool shuffle then prefix, so raising n_q1
    extends the arm without redrawing who is already in it (PR #28
    review noted random.sample redrew membership on every change)."""
    pools_ = _pools(q1=tuple(f"q{i}" for i in range(30)))
    old_nq1 = sampling.PARAMS["n_q1"]
    try:
        sampling.PARAMS["n_q1"] = 5
        small = [s["author"] for s in sampling.draw(pools_)
                 if s["arm"] == "B2"]
        sampling.PARAMS["n_q1"] = 12
        big = [s["author"] for s in sampling.draw(pools_)
               if s["arm"] == "B2"]
    finally:
        sampling.PARAMS["n_q1"] = old_nq1
    assert big[:len(small)] == small
    assert len(big) > len(small)


def test_eras_pools_use_paired_eligibility(monkeypatch):
    """The eras pools apply exactly the v1 paired-arm eligibility
    (sampling.eligible_item) per quarter: fleet, bot-login, unmerged,
    and out-of-window PRs never enter; AI/unmarked split by marker."""
    from pipeline import frame
    from pipeline.studies import productivity

    def pr(created, merged, num, login="alice", additions=100, msg="x"):
        return _pr(created, merged, num, login=login,
                   additions=additions, msg=msg)

    cells = {
        ("o/r", "2025-10-01..2025-12-31"): [
            pr("2025-11-01T00:00:00Z", "2025-11-05T00:00:00Z", 1,
               msg=CLAUDE_MARK),
            pr("2025-11-02T00:00:00Z", "2025-11-06T00:00:00Z", 2),
            pr("2025-11-03T00:00:00Z", "2025-11-07T00:00:00Z", 3,
               login="fleeter"),
            pr("2025-11-04T00:00:00Z", "2025-11-08T00:00:00Z", 4,
               login="tiny", additions=10)],
        ("o/r", "2026-01-01..2026-03-31"): [
            pr("2026-02-01T00:00:00Z", "2026-02-05T00:00:00Z", 5)],
    }
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins",
                        lambda: {"fleeter"})
    p = eras.pools()
    assert set(p["Q4-2025"]) == {"alice"}
    assert p["Q4-2025"]["alice"]["ai"] == [("o/r", 1, 100)]
    assert p["Q4-2025"]["alice"]["nonai"] == [("o/r", 2, 100)]
    assert p["Q1-2026"] == {"alice": {"ai": [],
                                      "nonai": [("o/r", 5, 100)]}}
    assert p["Q2-2026"] == {}
