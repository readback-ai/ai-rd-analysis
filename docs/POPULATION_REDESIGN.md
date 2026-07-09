# PROPOSAL: clean 5-rule population definition (for Ron's review, 2026-07-09)

Replaces the accreted admission machinery (two-tier source scoping, top-10
gate, name/description fallbacks, single-product clause, re-audit narrative,
v1_carryover provenance argument) with:

## The rules
1. **Candidates** — union of five citable third-party lists (snapshots +
   transcriptions in `data/resume_state/v2/`): LF AI & Data landscape,
   HF hub top orgs, GitHub AI-topic orgs, **Epoch AI notable-models
   organizations** (epoch.ai, CC-BY; models <= cutoff; `epoch_org_map.tsv`),
   and a **declared hand-curated list** (`curated_ai_orgs.tsv`: TechCrunch
   2025 $100M+ transcription + prominent labs — stated plainly as curation).
2. **Quality** — flagship repo >=1,000 stars. Exemption: members of the two
   AI-developer lists (Epoch, curated) — those lists already vet
   significance (funding / notable models).
3. **AI-developer identity** — org is an AI developer iff it is on an
   AI-developer list OR >=2 of its top-5 starred repos carry maintainer
   AI topics.
4. **Evidence keep** (one rule, one pass) — >=5 AI-evidence PRs/commits
   across the three detection layers, or >=0.1% of PRs (union of scan TSVs
   and the census itself; `census_org_evidence.json`).
5. **Scope** — AI developers enter FULL-ORG, except the 14 declared
   conglomerate umbrella orgs (google, microsoft, alibaba, Tencent, apple,
   facebook, sony, IBM, Netflix, awslabs, intel, GoogleCloudPlatform,
   dotnet, apache) which enter REPO-SCOPED (their AI-topic repos only).
   Non-developers with a >=1k-star AI-topic flagship also enter repo-scoped.
   Everything else is out.

Plus ONE override table (`org_overrides.tsv`, ~14 rows): the 11 adjudicated
AI-washed exclusions (gitleaks, meilisearch, daytonaio...) + 2-3 inclusions
for topic-sparse AI orgs (embeddings-benchmark/MTEB, flashinfer-ai).

## Outcome vs current population
- full-org: 175 (every one already in the current population; 0 new)
- repo-scoped strata: 48 (up from 6 — absorbs single-product orgs like
  ollama/BerriAI/langgenius AND big-tech umbrellas, one uniform mechanism)
- excluded that are currently in: 41, of which ~11 are the adjudicated
  AI-users (intended), ~25 are evidence-thin orgs contributing zero or
  near-zero censused AI activity today (meta-llama, cerebras,
  thinking-machines-lab, google-research: real orgs, no measurable AI-tool
  footprint — the population criterion says measurable), and ~5 are
  debatable (AnswerDotAI, FlagOpen, datahub-project — review requested).

## What re-baselining requires if approved
AI-repo enumeration for the 42 new stratum orgs (~1 API pass), census gap
fill (most strata repos are already censused), then re-run analyze/integrate
and refresh v2_results headline + appendix tables (expect small deltas: the
v2->v2.1 re-baseline moved the headline 0.2pp).
