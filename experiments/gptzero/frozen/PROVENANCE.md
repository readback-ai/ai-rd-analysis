# Frozen audit set (2026-08-06)

- detector version pin: 2026-07-04-base
- reservation ledger: 479539 words reserved, ceiling 500000
- files: manifest_v1_50k.json, manifest_b3.json, manifest_eras.json, manifest_pc.json, docs_v1.jsonl, scores_v1.jsonl, docs_retest.jsonl, scores_retest.jsonl, paragraph_summary.jsonl, docs_newfile.jsonl, scores_sem13c.jsonl, scores_sem13c_newfile.jsonl, scores_sem13c_newfile_full.jsonl + report.txt

The retest rows are the stage-1 sensitivity subset: every document truncated at the design cap when the retest ran; the report's coverage line states the bound share of the current corpus. The ledger deliberately over-counts on transport failures (every HTTP attempt reserves before it runs); reconcile against the GPTZero dashboard by archiving the ledger and seeding it with one dashboard-confirmed row (see README).
