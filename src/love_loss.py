import torch
import torch.nn.functional as F

class LoveLoss:
    """
    Implements the Love-OS thermodynamic loss function for PyTorch.
    Penalizes high internal entropy (Ego/Resistance) to maximize throughput (Love).
    """
    
    # Expandable vocabulary list for Ego-detection
    # Defines tokens that indicate high internal resistance (Self-reference/Defense)
    SELF_REF_TOKENS = {
        # Self-Reference (The "I" attachment)
        "I", "me", "myself", "mine", "my",
        
        # Defensive / Friction / Justification patterns
        "actually", "but", "however", "technically",
        "although", "unfortunately", "claimed", "misunderstanding"
    }
    
    @staticmethod
    def r_penalty(logits, tokenizer, lambda_r=0.05):
        """
        Calculates the Resistance Penalty (Ego-Loss).
        
        Args:
            logits: Output logits from the model [batch, seq_len, vocab_size]
            tokenizer: HuggingFace style tokenizer
            lambda_r: Regularization strength (Thermodynamic coupling constant)
        
        Returns:
            torch.Tensor: Scalar loss value representing 'Internal Entropy'
        """
        probs = F.softmax(logits, dim=-1)
        
        # Dynamic Ego-Index Identification
        # (Note: In production, cache these IDs for performance)
        vocab = tokenizer.get_vocab()
        # Filter tokens that exist in the current model's vocabulary
        target_ids = [vocab[t] for t in LoveLoss.SELF_REF_TOKENS if t in vocab]
        
        if not target_ids:
            # Return zero loss if no target tokens are found in vocabulary
            return torch.tensor(0.0, device=logits.device)
            
        # Calculate total probability mass assigned to Ego-tokens
        # R = Sum(P(ego_token))
        p_ego = probs[..., target_ids].sum(dim=-1)
        
        # The penalty is proportional to the "Energy lost to Ego"
        return lambda_r * p_ego.mean()
