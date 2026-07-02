# Scope & methods: AI-assisted development at leading AI organizations

Snapshot 2026-06-29. Window analyzed: **Q1-2024 (pre-AI baseline) + Q3-2025 → Q2-2026**.
All detection is read-only GitHub API. Source artifacts: `ai_labs.yaml` (org list),
`data/ai_evidence_repos.csv` (repos), `agents.yaml` + `artifacts/agent_detection_cues.md`
(detection).

---

## 1. Methods used to detect AI contributions

We scope by **org provenance** (curated allowlist of leading AI orgs) and detect AI
contributions **within** those orgs via three complementary public signals:

**A. Agent-authored PRs** (delegated *cloud* agents that open the PR themselves) — found by
PR-author bot login. 8 confirmed handles: `copilot-swe-agent[bot]`,
`devin-ai-integration[bot]`, `cursor[bot]`, `google-labs-jules[bot]`, `codegen-sh[bot]`,
`amazon-q-developer[bot]`, `factory-droid[bot]`, `claude[bot]`.

**B. AI co-author trailers on commits** (the dominant pattern — a human opens the PR but
commits were written with AI). Found by **bare-term commit-message search**:
- **Claude Code**: `Co-Authored-By: Claude <noreply@anthropic.com>` + footer
  `🤖 Generated with [Claude Code]`
- **Cursor Agent**: `Co-authored-by: Cursor <cursoragent@cursor.com>`
- **aider** (minor): its co-author trailer
- **CRITICAL CORRECTION**: the GitHub `author-email:` search qualifier does **not** match
  co-authored commits (it matches only the primary author), undercounting Claude usage
  ~10-16× org-scoped. Bare-term free-text search is required. (Evidence:
  `agent_detection_cues.md`.)

**C. Committed agent-config files** (repo-level corroboration, not a primary metric):
`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `copilot-instructions.md`, etc.

**"AI-code PR" definition (analysis unit):** a PR *contains AI-written code* if **any of
its commits** carries a Claude/Cursor co-author trailer or the Claude Code footer. This
captures human-opened, AI-assisted PRs — far more common than bot-opened PRs (e.g.
HuggingFace: 1,815 AI-trailer commits vs 39 bot PRs).

**What is structurally UNDETECTABLE** (and why we exclude no-signal repos): locally-run
IDE/CLI tools leave no public marker — Windsurf/Cascade, Codex CLI (default config),
Cursor *IDE* inline, Copilot autocomplete, Tabnine, etc. A repo with zero detected AI is
therefore **not provably AI-free**. Consequences:
- We do **not** use no-detected-AI repos as "no-AI controls" — we can't certify them.
- The control is **temporal**: the *same* in-scope repos in **Q1-2024**, before AI-coding
  tools were in meaningful use — a sound "before" baseline.
- Counts are a **floor** (squash-merge can strip trailers).

**Keep rule for a repo:** AI-code ≥ 0.1% of its PRs in any period **OR** ≥ 5 absolute
AI-trailer commits.

**Sampling/weighting:** AI-evidence repos enumerated by commit-trailer search → product
repos (meta/demo excluded) → PR census (uniform-500 for repos with >50 PRs/period, full
census for smaller repos) → per-repo metrics, reported **equal-weight** and
**contributor-weighted** (by core human contributors).

---

## 2. In scope

**Universe scanned:** 105 orgs (curated `ai_labs.yaml`, Meta-controlled orgs excluded
a priori — see §3). **74 are AI-active** (≥5 detectable AI commits in the window) →
**196 AI-evidence repos** → **175 product repos across 59 orgs** carry the analysis
(21 meta/demo repos excluded, §3). 1,940 core human contributors; median 4/repo.

**74 AI-active orgs by category** (AI-commit count in parens):

- **Frontier / model labs**: anthropics (3387), openai (35), mistralai (25), QwenLM (258),
  MoonshotAI (59), zai-org (9), deepseek-ai (5), MiniMax-AI (64), stepfun-ai (10),
  SkyworkAI (15), InternLM (20), ByteDance-Seed (23), modelscope (113), cohere-ai (9),
  ibm-granite (44), Aleph-Alpha (12), thinking-machines-lab (243), imbue-ai (14017),
  SakanaAI (31), Physical-Intelligence (14), NVIDIA-NeMo (873), NVlabs (35).
- **Research orgs / academic**: allenai (984), EleutherAI (158), NousResearch (441),
  LAION-AI (191), OpenBMB (854), stanfordnlp (27), stanford-crfm (6), HazyResearch (19),
  SalesforceAIResearch (18).
- **Infra / serving / frameworks**: vllm-project (873), sgl-project (612), ggml-org (38),
  langchain-ai (1476), run-llama (158), autogluon (95), unslothai (69),
  Unstructured-IO (77), modular (31), ml-explore (11).
- **Vector DBs**: milvus-io (617), zilliztech (520), weaviate (508), pinecone-io (295),
  qdrant (253), chroma-core (36).
- **Compute / hardware / platform startups**: tenstorrent (1574), PrimeIntellect-ai (955),
  LambdaLabsML (455), anyscale (182), basetenlabs (158), groq (44), sambanova (12),
  Cerebras (5), scaleapi (100), replicate (16), modal-labs (15), fw-ai (99),
  togethercomputer (103), Lightning-AI (5).
- **Product / vertical / dev-tool startups**: huggingface (1815), character-ai (2007),
  writer (172), elevenlabs (141), twelvelabs-io (232), runwayml (22), Stability-AI (87),
  anysphere/Cursor (37), augmentcode (17), fal-ai (32), ContextualAI (13), jina-ai (18),
  sarvamai (29).

Tool mix: ~84% of detected AI commits are **Claude**; **Cursor** is concentrated in a few
orgs (OpenBMB, writer, Stability-AI, sarvamai). Per-repo detail in `data/ai_evidence_repos.csv`.

---

## 3. Excluded — and why

### 3a. Excluded orgs: 31 "dark" (< 5 detectable AI commits in the window)
These leading AI orgs show no meaningful *detectable* AI contribution. **Not a claim they
don't use AI** — they likely use locally-run / private tooling invisible to public
attribution — so they cannot serve as controls and have no signal to analyze:

`google-deepmind, xai-org, AI21Labs, 01-ai, baichuan-inc, OpenGVLab, Tencent-Hunyuan,
bigcode-project, bigscience-workshop, mosaicml, kakaobrain, AI4Bharat, reka-ai,
Essential-AI, harmonic-ai, chaidiscovery, insilicomedicine, snorkel-team, lm-sys,
voyage-ai, nomic-ai, argilla-io, Exafunction (Windsurf), shield-ai, replit, lumalabs,
SesameAILabs, arcee-ai, tensorflow, jax-ml, keras-team`

Notable: the core **ML framework orgs** (`tensorflow`, `jax-ml`, `keras-team`) and several
frontier labs (`google-deepmind`, `xai-org`, `deepseek-ai` was just at threshold) are dark —
consistent with private development or untracked tools.

### 3b. Excluded repos: 21 meta/demo (of the 196 AI-evidence repos)
Repos whose *purpose* is examples/evaluation/scaffolding, where heavy AI-coding is expected
and unrepresentative of normal engineering. Dropped per Ron's call:
`anthropics/claudes-c-compiler, thinking-machines-lab/tinker-cookbook,
langchain-ai/skills-benchmarks, anyscale/templates, fw-ai/cookbook,
langchain-ai/langchain-skills, imbue-ai/forever-claude-template,
modular/max-agentic-cookbook, fw-ai/benchmark, langchain-ai/langsmith-skills,
run-llama/template-*, togethercomputer/together-sandbox, SkyworkAI/Skywork-Skills,
anyscale/ai-infra-cookbook, sarvamai/sarvam-ai-cookbook, basetenlabs/ml-cookbook,
modal-labs/modal-examples, Cerebras/inference-examples` (and similar).

### 3c. Excluded a priori: Meta-controlled orgs
`meta-llama`, `facebookresearch`, `pytorch` — Meta develops with internal tooling that
leaves no public attribution, so detectable signal is ~0 (meta-llama) or dominated by
*external* contributors (pytorch's agent PRs are outside contributors, not Meta staff).
Including them would misrepresent "Meta's practices." Kept in the org list for provenance,
excluded from practice metrics.

### 3d. Funded $100M+ startups with NO public code (documented in `ai_labs.yaml`)
Magic, Poolside, Cognition/Devin, World Labs, Reflection AI, H Company, Harvey, Glean,
Sierra, Hippocratic, SSI, and most healthcare/enterprise raisers — no public repos, so
out of scope for any GitHub-observable analysis.

---

## Org-list provenance & proposed external-sourced v2 (2026-06-29)

The v1 105-org list was hand-curated (model knowledge + your seeds + GitHub `users/`
verification) — editorial, with gaps. Proposed reproducible v2, anchored to external lists:

| Category | External source | Pull method |
|---|---|---|
| Model/frontier labs | Hugging Face Hub (top orgs by model downloads); Epoch AI "Notable/Frontier AI Models" DB (epoch.ai/data/ai-models, CSV) | HF `/api/models?sort=downloads`; Epoch CSV |
| Funded startups ($100M+) | TechCrunch 2025 $100M+ list (already used) | web |
| OSS infra/frameworks/vector DBs | LF AI & Data Landscape (github.com/lfai/lfai-landscape, CSV/YAML); GitHub `search/repositories topic:<llm-inference|vector-database|llmops|ai-agents> stars:>N` | landscape data; GitHub search |
| Big-tech AI sub-orgs | GitHub stars+AI-topics within the org | GitHub search |

Cleaning required: (1) **name-map** external→GitHub org (HF `Qwen`→`QwenLM`, `laion`→
`LAION-AI`; Epoch uses company names); (2) **filter noise** — keep `type=Organization`,
drop individual fine-tuners (HF `intfloat`, `jonatasgrosman`) and course/awesome/spam repos
(`affaan-m/ECC`), apply downloads/stars floor.

Gaps v2 would add (surfaced by HF + GitHub-topic, missing from v1): BAAI, Answer.AI
(`answerdotai`), Comfy-Org, pyannote, coqui, RedHatAI, sentence-transformers, timm;
BentoML, LiteLLM/BerriAI, MLflow, Langfuse, LangFlow, Flowise, RAGFlow/infiniflow,
browser-use, Composio, Meilisearch.

## v2 RESULT (2026-07-02): 216-org defensible AI-active set

Pipeline: external candidate pool (482 from HF Hub + GitHub-topic + LF landscape) →
quality gate (flagship repo ≥1k★) = 364 → all-time AI-evidence scan (Claude+Cursor ≥5
commits) → drop general-infra (supabase/apache/kubernetes/grafana/…) → **∪ TechCrunch
$100M+ funded startups with AI evidence** (funding = their quality signal, star-gate exempt).

Result: **216 AI-active orgs** = the 74 v1-active orgs (all retained, 0 dropped) + **142
new**. Reproducible; provenance per org in `data/resume_state/v2/candidates.tsv`; final set
in `data/resume_state/v2/v2_active.txt`. Scale table: `.../v2/org_scale.tsv`.

Notable new orgs (AI commits): microsoft(5465, big-tech — repo-enum scopes to DeepSpeed/
autogen/etc.), mlflow(2933), NVIDIA(2843), LiteLLM/BerriAI(1890), Dify/langgenius(1724),
Composio(1318), promptfoo, onyx, browser-use, comet-ml, langfuse, Prefect, HKUDS, alibaba,
Arize, firecrawl, neuralmagic. Big-tech org-level counts are "has-activity" flags; the
AI-evidence-repo enumeration does the real repo scoping (as in v1 Tier-2).

Remaining for v2 analysis: AI-evidence-repo enumeration on the 142 new orgs (v1 orgs already
enumerated) → product repos → census → re-run weighted analysis. (v1 findings hold; v2
broadens the population defensibly.)

## Caveats
- Detection is a floor (trailer stripping; invisible local tools).
- Org allowlist is editorial — omissions are blind spots; criteria are documented and
  versioned in `ai_labs.yaml`.
- Public repos only; private development is unobservable.
- "Dark" orgs are a statement about *public detectability*, not about actual AI use.
