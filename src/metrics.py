# src/metrics.py
import re
from typing import Dict

class LoveMetrics:
    """
    Computes V/R/I metrics for text, strictly in English.
    Target Domain: Technical Writing & Social Media (High S/N ratio).
    """
    
    # R-Factors: Signals of Ego/Attachment/Friction
    SELF_REF_WORDS = {
        "i", "me", "my", "myself", "mine", "we", "our", "us"
    }
    
    DEFENSE_PHRASES = {
        "actually", "to be honest", "honestly", "frankly",
        "in fact", "technically", "don't get me wrong",
        "unfortunatelly", "however", "claimed", "allegedly"
    }
    
    # I-Factors: Signals of Throughput/Action
    CITATION_PATTERN = re.compile(r"(https?://|\[\d+\]|@[\w_]+)")
    WORD_PATTERN = re.compile(r"\b\w+\b")

    @staticmethod
    def compute(item: Dict) -> Dict:
        """
        item = {
            'output': str,
            'tokens_used': int,
            'latency_sec': float,
            'correct': bool (optional)
        }
        """
        text = item.get('output', '').lower()
        tokens_used = int(item.get('tokens_used', 1))
        latency_sec = float(item.get('latency_sec', 0.0))
        
        words = LoveMetrics.WORD_PATTERN.findall(text)
        total_words = max(len(words), 1)

        # 1. Calculate R (Resistance/Entropy)
        self_refs = sum(1 for w in words if w in LoveMetrics.SELF_REF_WORDS)
        defense_hits = sum(1 for p in LoveMetrics.DEFENSE_PHRASES if p in text)
        redundancy = max(text.count('...'), 0) + max(text.count('!!'), 0)
        
        # R_proxy formulation:
        # Heavily penalize defensive phrases (friction) over simple self-refs
        r_proxy = (
            0.3 * (self_refs / total_words) +
            0.5 * (defense_hits / max(total_words / 20, 1)) +
            0.2 * (redundancy / max(total_words / 50, 1))
        )

        # 2. Calculate I (Throughput/Signal)
        # Citations/Links are high signal
        has_citation = bool(LoveMetrics.CITATION_PATTERN.search(item.get('output', ''))) 
        bullet_points = text.count('\n-') + text.count('\n*')
        
        actionability = (bullet_points + (2 if has_citation else 0)) / max(total_words / 50, 1)
        
        # I_proxy = (Signal Density) / (Energy Cost)
        # If 'correct' is unknown, assume 1.0 for unsupervised estimation
        quality_score = 1.0 + (0.5 * actionability)
        i_proxy = quality_score / max(tokens_used, 1) * 100  # Scale up

        return {
            'R_proxy': float(r_proxy),
            'I_proxy': float(i_proxy),
            'latency_sec': latency_sec,
            'tokens_used': tokens_used
        }
