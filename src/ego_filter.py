# src/ego_filter.py
import torch
import numpy as np

class EgoFilter:
    """
    Runtime filter to suppress Ego-Resistance ($R$) during inference.
    """

    @staticmethod
    def apply_logit_bias(logits, tokenizer, bias: float = -5.0):
        """
        Heavily suppresses defensive/self-referential tokens.
        """
        # Define Ego-tokens (simplified set for runtime)
        EGO_TOKENS = {"actually", "but", "however", "technically"}
        
        vocab = tokenizer.get_vocab()
        bias_ids = [vocab[t] for t in EGO_TOKENS if t in vocab]
        
        if bias_ids:
            # Apply negative bias to suppress R
            logits[..., bias_ids] += bias
            
        return logits

    @staticmethod
    def should_stop_early(logits, entropy_threshold: float = 1.5):
        """
        Checks if the model is 'rambling' (High Entropy).
        If entropy is low (confident), stop generating to reduce Latency ($L$).
        """
        probs = torch.softmax(logits[:, -1, :], dim=-1)
        
        # Calculate Shannon Entropy
        # H = -Sum(p * log(p))
        entropy = -(probs * (probs.clamp_min(1e-12)).log()).sum(dim=-1).mean().item()
        
        # If entropy is very low, the model is confident -> STOP.
        # If entropy is high, it's confused/hallucinating -> Continue (or Abort).
        return entropy < entropy_threshold
