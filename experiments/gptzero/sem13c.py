"""Second detector: the RELEASED LINEAR MIL COMPONENT of the
SemEval-2026 Task 13 Subtask C 1st-place team's system (Gainulla &
Shamsadinov 2026, "YoungDSMLKZ at SemEval-2026 Task 13") scoring the
SAME document corpus as GPTZero — locally and free.

Component, not the winning ensemble: the paper reports ~0.5906
macro-F1 for this linear max-pooling MIL model standalone, 0.6331
with its CatBoost head, and 0.7855 for the full routed ensemble —
only the linear component's weights are released, so transfer
conclusions here bind to the component alone.

Four-way code classification: human / ai / hybrid / adversarial — a
code-native instrument with exactly the hybrid class GPTZero never
produces. Inference mirrors the authors' published path: every
document PADS TO THE FULL 4096-token context before 512-token
chunking (stride 256), per-chunk linear logits max-pooled. Weights
load from the authors' HuggingFace repo at a PINNED revision and
rows carry an INFERENCE version, so a preprocessing change
invalidates cached scores instead of silently coexisting with them.

Domain note: the model was trained on whole source files, not
diff-assembled documents — scores are read comparatively, not
absolutely.
"""
from __future__ import annotations

import json
from pathlib import Path

CLASS_NAMES = ("human", "ai", "hybrid", "adversarial")
HF_REPO = "YoungDSMLKZ/UnixCoder-MIL"
HF_REVISION = "0619dccaf165ab4e310ed8213936b15bda572b8f"
BACKBONE = "microsoft/unixcoder-base"
BACKBONE_REVISION = "5604afdc964f6c53782a6813140ade5216b99006"
CHUNK, STRIDE, MAX_CHUNKS, MAX_LEN = 512, 256, 16, 4096
# Preprocessing identity: cached rows scored under any other value are
# invalid and rescored. pad4096 = pad every document to MAX_LEN before
# chunking, matching the authors' published inference path.
INFERENCE = "pad4096"


def _load():
    """Model + tokenizer, lazily: torch/transformers are heavyweight
    and only the scoring command needs them."""
    import torch
    import torch.nn.functional as F
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    from torch import nn
    from transformers import AutoConfig, AutoModel, AutoTokenizer

    class MilUniXcoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.config = AutoConfig.from_pretrained(
                BACKBONE, revision=BACKBONE_REVISION)
            self.unixcoder = AutoModel.from_pretrained(
                BACKBONE, revision=BACKBONE_REVISION)
            self.dropout = nn.Dropout(0.1)
            self.classifier = nn.Linear(self.config.hidden_size,
                                        len(CLASS_NAMES))

        def forward(self, input_ids, attention_mask):
            seq_len = input_ids.size(1)
            if seq_len > CHUNK:
                ids = input_ids.unfold(1, CHUNK, STRIDE)
                mask = attention_mask.unfold(1, CHUNK, STRIDE)
                if ids.size(1) > MAX_CHUNKS:
                    half = MAX_CHUNKS // 2
                    ids = torch.cat([ids[:, :half], ids[:, -half:]], 1)
                    mask = torch.cat([mask[:, :half], mask[:, -half:]],
                                     1)
                k = ids.size(1)
                flat_ids = ids.contiguous().view(-1, CHUNK)
                flat_mask = mask.contiguous().view(-1, CHUNK)
            else:
                k = 1
                pad = CHUNK - seq_len
                flat_ids = F.pad(input_ids, (0, pad), value=0)
                flat_mask = F.pad(attention_mask, (0, pad), value=0)
            out = self.unixcoder(input_ids=flat_ids,
                                 attention_mask=flat_mask)
            pooled = self.dropout(out.last_hidden_state[:, 0, :])
            logits = self.classifier(pooled).view(1, k, -1)
            return logits.max(dim=1).values

    tok = AutoTokenizer.from_pretrained(HF_REPO, revision=HF_REVISION)
    model = MilUniXcoder()
    weights = load_file(hf_hub_download(
        HF_REPO, "model.safetensors", revision=HF_REVISION))
    model.load_state_dict(weights)
    model.eval()
    return model, tok


def make_predictor():
    """text -> {class: prob}. One doc per forward pass (chunks batch
    internally); dropout disabled via eval()."""
    import torch
    model, tok = _load()

    def predict(text: str) -> dict:
        enc = tok(text, truncation=True, max_length=MAX_LEN,
                  padding="max_length", return_tensors="pt")
        with torch.no_grad():
            logits = model(enc["input_ids"], enc["attention_mask"])
            probs = torch.softmax(logits[0], dim=-1).tolist()
        return dict(zip(CLASS_NAMES, probs))
    return predict


def score_rows(doc_rows: list[dict], doc_cache: Path, out_path: Path,
               predictor=None) -> int:
    """Score every filled document row not already scored under the
    pinned revision; append rows keyed (slot, doc_sha). Returns the
    number newly scored. Free and local — no budget ledger."""
    done = set()
    if out_path.is_file():
        for ln in out_path.read_text().splitlines():
            if ln.strip():
                r = json.loads(ln)
                if (r.get("model_revision") == HF_REVISION
                        and r.get("inference") == INFERENCE):
                    done.add((r["slot"], r["doc_sha"]))
    todo = [r for r in doc_rows
            if (r["slot"], r["doc_sha"]) not in done]
    if not todo:
        return 0
    if predictor is None:
        predictor = make_predictor()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("a") as out:
        for r in todo:
            text = (doc_cache / f"{r['doc_sha']}.txt").read_text()
            probs = predictor(text)
            pred = max(probs, key=probs.get)
            out.write(json.dumps(
                {**{k: r[k] for k in ("slot", "arm", "author",
                                      "period", "ai", "doc_sha")},
                 "words": r.get("words"),
                 "truncated": r.get("truncated"),
                 "sem_probs": probs, "sem_pred": pred,
                 "model_revision": HF_REVISION,
                 "inference": INFERENCE}) + "\n")
            out.flush()
            n += 1
            print(f"sem13c {r['slot']}: {pred} "
                  f"(ai {probs['ai']:.2f}, hybrid "
                  f"{probs['hybrid']:.2f})", flush=True)
    return n
