import torch
import torch.nn.functional as F

class LoveLoss:
    """
    Implements the Love-OS thermodynamic loss function for PyTorch.
    Penalizes high internal entropy (Ego/Resistance) to maximize throughput (Love).
    
    Formula:
        Loss = Task_Loss + lambda_r * R
        where R = Sum(P(ego_tokens))
    """
    
    # Vocabulary mapping for Ego-detection
    # List of tokens representing self-reference and defensive friction
    SELF_REF_TOKENS = {
        # Self-Reference (Ego-centric)
        "I", "me", "myself", "mine", "my",
        
        # Defensive / Friction (Resistance)
        "actually", "but", "however", "although", "yet"
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
        # Convert logits to probabilities
        probs = F.softmax(logits, dim=-1)
        
        # Dynamic Ego-Index Identification
        # (Note: In production, cache these IDs for performance)
        vocab = tokenizer.get_vocab()
        
        # Filter tokens that exist in the current tokenizer's vocabulary
        target_ids = [vocab[t] for t in LoveLoss.SELF_REF_TOKENS if t in vocab]
        
        # If no ego-tokens found in vocabulary, return zero penalty
        if not target_ids:
            return torch.tensor(0.0, device=logits.device)
            
        # Calculate total probability mass assigned to Ego-tokens
        # R = Sum(P(ego_token))
        p_ego = probs[..., target_ids].sum(dim=-1)
        
        # The penalty is proportional to the "Energy lost to Ego"
        return lambda_r * p_ego.mean()
