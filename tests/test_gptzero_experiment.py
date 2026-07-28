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
    calls = []

    def transport(text):
        calls.append(text)
        return {"documents": [{"predicted_class": "ai"}]}

    with pytest.raises(SystemExit):
        gptzero_client.score("sha1", "w " * 200,
                             spent=gptzero_client.BUDGET_WORDS - 100,
                             cache_dir=tmp_path, transport=transport)
    assert calls == []


def test_cache_hit_never_resubmits(tmp_path):
    calls = []

    def transport(text):
        calls.append(text)
        return {"documents": [{"predicted_class": "ai"}]}

    resp, billed = gptzero_client.score("shaX", "some words here",
                                        spent=0, cache_dir=tmp_path,
                                        transport=transport)
    assert billed == 3 and len(calls) == 1
    resp2, billed2 = gptzero_client.score("shaX", "some words here",
                                          spent=0, cache_dir=tmp_path,
                                          transport=transport)
    assert resp2 == resp and billed2 == 0 and len(calls) == 1


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
    manifest = {"params": {"word_cap": 600, "word_floor": 1},
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


def test_transport_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setenv("GPTZERO_API_KEY", "k")
    monkeypatch.setattr(gptzero_client.time, "sleep", lambda s: None)
    attempts = []

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"documents": [{"predicted_class": "human"}]}'

    def fake_urlopen(req, timeout):
        attempts.append(1)
        if len(attempts) == 1:
            raise gptzero_client.urllib.error.URLError("reset")
        return _Resp()

    monkeypatch.setattr(gptzero_client.urllib.request, "urlopen",
                        fake_urlopen)
    resp = gptzero_client._post("text")
    assert resp["documents"][0]["predicted_class"] == "human"
    assert len(attempts) == 2


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
