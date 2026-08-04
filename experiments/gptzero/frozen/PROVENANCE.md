# Frozen audit set (2026-08-04)

- detector version pin: 2026-07-04-base
- reservation ledger: 264732 words reserved, ceiling 270000
- files: manifest_v1_50k.json, manifest_b3.json, manifest_eras.json, docs_v1.jsonl, docs_retest.jsonl, scores_v1.jsonl, scores_retest.jsonl + report.txt

The ledger deliberately over-counts on transport failures (every HTTP attempt reserves before it runs); reconcile against the GPTZero dashboard by archiving the ledger and seeding it with one dashboard-confirmed row (see README).
