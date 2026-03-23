# nli_guard.py
# Natural Language Inference guard for ABSTAIN decision.
# (c) Love-OS Architect Project, 2026. MIT License.

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import os
import re
import itertools

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    _HF_AVAILABLE = True
except ImportError:
    _HF_AVAILABLE = False

@dataclass
class NLIGuardConfig:
    model_name: str = os.environ.get("NLI_MODEL", "joeddav/xlm-roberta-large-xnli")
    device: str = os.environ.get("NLI_DEVICE", "cuda" if torch.cuda.is_available() else "cpu") if _HF_AVAILABLE else "cpu"
    abstain_ratio_th: float = float(os.environ.get("NLI_ABSTAIN_RATIO", 0.25))
    abstain_prob_th: float  = float(os.environ.get("NLI_ABSTAIN_PROB",  0.80))
    max_pairs: int = int(os.environ.get("NLI_MAX_PAIRS", 45))
    min_len: int = 3

class NLIGuard:
    """NLI-based contradiction detector."""
    def __init__(self, cfg: Optional[NLIGuardConfig] = None):
        self.cfg = cfg or NLIGuardConfig()
        self.tokenizer = None
        self.model = None
        if _HF_AVAILABLE:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.cfg.model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.cfg.model_name).to(self.cfg.device)
                self.model.eval()
            except Exception:
                self.tokenizer = None
                self.model = None

    _SEP = re.compile(r'[.?!!?\n]+|(?<=\.)\s+')

    def _sent_split(self, text: str) -> List[str]:
        sents = [s.strip() for s in self._SEP.split(text) if s and len(s.strip()) >= self.cfg.min_len]
        uniq = []
        [uniq.append(s) for s in sents if s not in uniq]
        return uniq

    def _softmax(self, x):
        import math
        ex = [math.exp(v - max(x)) for v in x]
        s = sum(ex) or 1.0
        return [v/s for v in ex]

    def _nli_pair(self, premise: str, hypothesis: str) -> Tuple[str, float]:
        if self.model is None or self.tokenizer is None:
            # Rule-based fallback for CPU/Offline environments
            neg = ["no", "not", "never", "don't", "cannot", "won't", "isn't", "aren't"]
            score = 0.0
            if any(n in premise.lower() for n in neg) != any(n in hypothesis.lower() for n in neg):
                score += 0.6
            if ("but" in premise.lower() or "however" in premise.lower()) and ("but" not in hypothesis.lower() and "however" not in hypothesis.lower()):
                score += 0.3
            label = "contradiction" if score >= 0.6 else "neutral"
            return label, min(score, 0.99)

        enc = self.tokenizer(premise, hypothesis, truncation=True, padding=True, return_tensors="pt").to(self.cfg.device)
        with torch.no_grad():
            out = self.model(**enc).logits.squeeze(0).tolist()
        probs = self._softmax(out)

        id2label = getattr(self.model.config, "id2label", {})
        if id2label:
            label_scores = {id2label[i].lower(): probs[i] for i in range(len(probs))}
            label_scores = {
                "entailment": float(label_scores.get("entailment", 0.0)),
                "neutral":    float(label_scores.get("neutral", 0.0)),
                "contradiction": float(label_scores.get("contradiction", 0.0)),
            }
        else:
            idx = int(max(range(len(probs)), key=lambda i: probs[i]))
            candidates = ["entailment", "neutral", "contradiction"]
            label_scores = {c: 0.0 for c in candidates}
            label_scores[candidates[idx]] = probs[idx]

        label = max(label_scores, key=label_scores.get)
        return label, float(label_scores[label])

    def analyze(self, text: str) -> Dict:
        sents = self._sent_split(text)
        pairs = list(itertools.combinations(sents, 2))
        if len(pairs) > self.cfg.max_pairs:
            pairs = pairs[:self.cfg.max_pairs]

        contradictions = 0
        max_c_prob = 0.0
        top_pairs: List[Tuple[str, str, float]] = []

        for (a, b) in pairs:
            lab, prob = self._nli_pair(a, b)
            if lab == "contradiction":
                contradictions += 1
                max_c_prob = max(max_c_prob, prob)
                if len(top_pairs) < 5:
                    top_pairs.append((a, b, prob))

        ratio = (contradictions / max(1, len(pairs))) if pairs else 0.0
        abstain = (ratio >= self.cfg.abstain_ratio_th) or (max_c_prob >= self.cfg.abstain_prob_th)

        return {
            "sentences": sents,
            "pairs_evaluated": len(pairs),
            "contradiction_ratio": float(ratio),
            "max_contradiction_prob": float(max_c_prob),
            "abstain": bool(abstain),
            "examples": top_pairs
        }
