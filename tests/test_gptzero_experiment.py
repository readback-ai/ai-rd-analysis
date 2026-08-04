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
import sampling         # noqa: E402

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


def test_b3_draw_is_deterministic_and_one_doc_per_author():
    """The repo draw is seeded PPS; slots take one document per author
    across the whole arm."""
    import b3
    pool = {f"o/r{i}": 50 + i for i in range(30)}
    assert b3.draw_repos(pool) == b3.draw_repos(pool)
    pages = {r: [_b3_node(1, login="samedev"), _b3_node(2, login=f"u{r}")]
             for r in pool}
    slots = b3.slots_for(sorted(pool), pages)
    authors = [s["author"] for s in slots]
    assert len(authors) == len(set(authors))     # no author twice
    assert len(slots) == b3.B3_PARAMS["n_docs"]
    assert all(s["arm"] == "B3" and s["ai"] is False for s in slots)


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
    out = [json.loads(l) for l in
           gz.RESULTS_RETEST.read_text().splitlines()]
    assert [r["slot"] for r in out] == ["P:a:ai"]
    assert out[0]["sha600"] == "sha600"
    assert out[0]["word_cap"] == gz.RETEST_CAP
    sent.clear()
    gz.cmd_retest()                                  # idempotent resume
    assert sent == []


def _eras_pools(q4=("alice", "bob"), q1_26=("alice",)):
    def entry():
        return {"ai": [("o/r", 1, 100), ("o/r", 3, 200)],
                "nonai": [("o/r", 2, 100)]}
    return {"Q4-2025": {a: entry() for a in q4},
            "Q1-2026": {a: entry() for a in q1_26}}


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
        "P:Q1-2026:alice:ai", "P:Q1-2026:alice:nonai"}
    assert all(s["arm"] == "P" and s["period"] in eras.QUARTERS
               for s in slots)
    q1_before = [s for s in slots if s["period"] == "Q1-2026"]
    p2 = _eras_pools(q4=("alice", "bob", "carol"))
    q1_after = [s for s in eras.draw(p2) if s["period"] == "Q1-2026"]
    assert q1_after == q1_before


def test_eras_draw_skips_unmixed_authors_and_caps_depth(monkeypatch):
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
