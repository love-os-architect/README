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
    device: str = "cuda" if (_HF_AVAILABLE and torch.cuda.is_available()) else "cpu"
    abstain_ratio_th: float = float(os.environ.get("NLI_ABSTAIN_RATIO", 0.25))
    abstain_prob_th: float = float(os.environ.get("NLI_ABSTAIN_PROB", 0.80))
    max_pairs: int = int(os.environ.get("NLI_MAX_PAIRS", 45))
    min_len: int = 3


class NLIGuard:
    """
    Love-OS NLI Guard for Zero-Time ABSTAIN / 0-Ritual Decision.
    A universal, model-agnostic sentinel for detecting logical entropy.
    """

    def __init__(self, cfg: Optional[NLIGuardConfig] = None):
        self.cfg = cfg or NLIGuardConfig()
        self.tokenizer = None
        self.model = None
        self.contradiction_idx = 2  # Default fallback

        if _HF_AVAILABLE:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.cfg.model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.cfg.model_name).to(self.cfg.device)
                self.model.eval()

                # --- DYNAMIC LABEL RESOLUTION ---
                # Architecturally ensures we never misidentify "synchronization" as "contradiction"
                if hasattr(self.model.config, "label2id"):
                    for label_name, idx in self.model.config.label2id.items():
                        if "contradiction" in label_name.lower():
                            self.contradiction_idx = idx
                            break
                            
                print(f"[NLIGuard] Initialized {self.cfg.model_name} on {self.cfg.device}.")
                print(f"[NLIGuard] Contradiction mapped to tensor index: [{self.contradiction_idx}]")

            except Exception as e:
                print(f"[NLIGuard] Model load failed: {e}. Defaulting to rule-based logic.")
                self.tokenizer = self.model = None

    # Multi-lingual punctuation support (handles English, Japanese, Chinese, etc.)
    _SEP = re.compile(r'[.!?。！？\n]+|(?<=[.!?。！？])\s+')

    def _sent_split(self, text: str) -> List[str]:
        """Splits text into valid sentences with O(1) lookup deduplication."""
        sents = [s.strip() for s in self._SEP.split(text) if s.strip() and len(s.strip()) >= self.cfg.min_len]
        
        seen = set()
        return [s for s in sents if not (s in seen or seen.add(s))]

    def _get_contradiction_prob(self, premise: str, hypothesis: str) -> Tuple[str, float]:
        """Evaluates a sentence pair for logical collision (dissipation)."""
        if self.model is None or self.tokenizer is None:
            # Rule-based fallback for offline/CPU-constrained environments
            neg_words = {"no", "not", "never", "don't", "cannot", "won't", "isn't", "aren't", "but", "however"}
            p_lower = premise.lower()
            h_lower = hypothesis.lower()
            
            neg_p = any(n in p_lower for n in neg_words)
            neg_h = any(n in h_lower for n in neg_words)
            
            score = 0.0
            if neg_p != neg_h:
                score += 0.65
            if ("but" in p_lower or "however" in p_lower) and not ("but" in h_lower or "however" in h_lower):
                score += 0.35
                
            label = "contradiction" if score >= 0.6 else "neutral"
            return label, min(score, 0.99)

        # High-Fidelity Neural Inference
        enc = self.tokenizer(
            premise, hypothesis, 
            truncation=True, max_length=512, padding=True, return_tensors="pt"
        ).to(self.cfg.device)
        
        with torch.no_grad():
            logits = self.model(**enc).logits.squeeze(0).cpu().numpy()

        probs = torch.softmax(torch.tensor(logits), dim=0).numpy()

        # Extract contradiction probability using the dynamically resolved index
        contradiction_prob = float(probs[self.contradiction_idx]) if len(probs) > self.contradiction_idx else float(probs[-1])
        label = "contradiction" if contradiction_prob == max(probs) else "neutral"

        return label, contradiction_prob

    def analyze(self, text: str) -> Dict:
        """
        Full structural diagnosis of the text. 
        Returns ABSTAIN state if logical entropy exceeds geometric safety thresholds.
        """
        sents = self._sent_split(text)
        
        # Zero-Edge Case: Early exit if no valid pairs exist (avoids computational waste)
        if len(sents) < 2:
            return {
                "sentences": sents, 
                "pairs_evaluated": 0, 
                "contradiction_ratio": 0.0,
                "max_contradiction_prob": 0.0, 
                "abstain": False, 
                "examples": []
            }

        pairs = list(itertools.combinations(sents, 2))
        if len(pairs) > self.cfg.max_pairs:
            pairs = pairs[:self.cfg.max_pairs]

        contradictions = 0
        max_c_prob = 0.0
        top_pairs: List[Tuple[str, str, float]] = []

        for a, b in pairs:
            lab, prob = self._get_contradiction_prob(a, b)
            if lab == "contradiction":
                contradictions += 1
                if prob > max_c_prob:
                    max_c_prob = prob
                if len(top_pairs) < 5:
                    top_pairs.append((a, b, prob))

        ratio = contradictions / len(pairs) if pairs else 0.0
        
        # The /0 Trigger: If logical friction is too high, initiate ABSTAIN (Zero-Ritual)
        abstain = (ratio >= self.cfg.abstain_ratio_th) or (max_c_prob >= self.cfg.abstain_prob_th)

        return {
            "sentences": sents,
            "pairs_evaluated": len(pairs),
            "contradiction_ratio": float(ratio),
            "max_contradiction_prob": float(max_c_prob),
            "abstain": bool(abstain),
            "examples": top_pairs
        }
