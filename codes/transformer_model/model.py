"""
Sequential Transformer with fine-grained time encoding.
"""

import torch
import torch.nn as nn
from time_encoding import HybridTimeEncoder


class SequentialFailureTransformer(nn.Module):
    """
    Transformer model for HPC failure prediction.
    
    Uses three types of embeddings:
    1. Token embeddings (event types)
    2. Position embeddings (sequence order)
    3. Time embeddings (fine-grained time baskets + continuous)
    """
    def __init__(self, vocab_size, d_model=512, num_layers=6, num_heads=8,
                 max_seq_len=2048, dropout=0.1, num_time_baskets=1510):
        super().__init__()
        
        self.d_model = d_model
        
        # Token embedding
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        
        # Position embedding (sequence order)
        self.position_embedding = nn.Embedding(max_seq_len, d_model)
        
        # Fine-grained time encoder
        self.time_encoder = HybridTimeEncoder(
            d_model=d_model,
            num_baskets=num_time_baskets,
            use_hybrid=True
        )
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=num_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True  # Pre-norm for better training stability
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        
        # Output projection
        self.fc_out = nn.Linear(d_model, vocab_size)
        
        self.dropout = nn.Dropout(dropout)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights for better training."""
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)
    
    def forward(self, event_ids, time_deltas):
        """
        Args:
            event_ids: [batch, seq_len] - token IDs
            time_deltas: [batch, seq_len] - time in seconds
        
        Returns:
            logits: [batch, seq_len, vocab_size]
        """
        batch_size, seq_len = event_ids.shape
        
        # Token embeddings
        token_emb = self.token_embedding(event_ids)  # [B, L, D]
        
        # Position embeddings
        positions = torch.arange(seq_len, device=event_ids.device).unsqueeze(0)
        pos_emb = self.position_embedding(positions)  # [1, L, D]
        
        # Fine-grained time embeddings
        time_emb = self.time_encoder(time_deltas)  # [B, L, D]
        
        # Combine all three embeddings
        x = self.dropout(token_emb + pos_emb + time_emb)
        
        # Create causal mask (prevents looking ahead)
        causal_mask = nn.Transformer.generate_square_subsequent_mask(
            seq_len,
            device=x.device
        )
        
        # Transformer
        x = self.transformer(x, mask=causal_mask, is_causal=True)
        
        # Output logits
        logits = self.fc_out(x)
        
        return logits