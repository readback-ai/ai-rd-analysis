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
import gptzero_client   # noqa: E402
import sampling         # noqa: E402

CLAUDE_MARK = "x\n\nCo-Authored-By: Claude <noreply@anthropic.com>"


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


def test_cache_hit_never_resubmits_or_reserves(tmp_path):
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

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"documents": []}'

    def fake_urlopen(req, timeout):
        sent.update(json.loads(req.data))
        return _Resp()

    monkeypatch.setattr(gptzero_client.urllib.request, "urlopen",
                        fake_urlopen)
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
        {"fingerprint": "FP", "params": {}, "slots": []}))
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
        gptzero_client, "score",
        lambda sha, text, cache_dir, resv, **kw:
            ({"version": "pinver",
              "documents": [{"predicted_class": "ai"}]}, 3))
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
        {"fingerprint": "FP", "params": {}, "slots": []}))
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
        gptzero_client, "score",
        lambda sha, text, cache_dir, resv, **kw:
            ({"version": resp_version,
              "documents": [{"predicted_class": "ai"}]}, 3))
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


def test_mismatched_response_version_is_not_recorded(
        tmp_path, monkeypatch):
    """PR re-review P2: a response whose version differs from the pin is
    a contract violation — logged and NOT written to results."""
    import gptzero_client
    gz, results = _score_world(tmp_path, monkeypatch, dict(_DOC_ROW),
                               resp_version="other")
    monkeypatch.setattr(gptzero_client, "PINNED_VERSION", "pinver")
    gz.cmd_score(None)
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


def test_analysis_paired_sign_and_arm_rates():
    def row(author, ai, p, cls="human", arm="P"):
        return {"arm": arm, "author": author, "ai": ai,
                "class_probabilities": {"ai": p},
                "predicted_class": cls, "truncated": False}
    rows = [row("a", True, 0.9, "ai"), row("a", False, 0.1),
            row("b", True, 0.8, "ai"), row("b", False, 0.2),
            row("c", True, 0.3), row("c", False, 0.6)]
    pr = analyze.paired(rows)
    assert (pr["pairs"], pr["wins"], pr["losses"]) == (3, 2, 1)
    assert pr["sign_p"] == pytest.approx(0.5)      # C(3,2)+C(3,3) / 8
    s = analyze.arm_stats([r for r in rows if r["ai"]])
    assert s["n"] == 3 and s["flag_ai"] == pytest.approx(2 / 3)
