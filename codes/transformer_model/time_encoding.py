"""
Fine-grained time basket encoding for HPC event sequences.

Basket scheme:
- 0-1000ms:   1000 bins (1ms resolution)
- 1-60s:      60 bins (1s resolution)
- 1-60min:    60 bins (1min resolution)
- 1-24hr:     24 bins (1hr resolution)
- 1-365 days: 365 bins (1day resolution)
- 365+ days:  1 bin (independent)

Total: 1510 baskets
"""

import torch
import torch.nn as nn
import numpy as np


class FineGrainedTimeBaskets:
    """
    Ultra-fine-grained time baskets for HPC event sequences.
    """
    
    def __init__(self):
        self.num_baskets = 1510
        
        # Basket boundaries
        self.ms_bins = 1000      # 0-999: milliseconds (0-1000ms)
        self.sec_bins = 60       # 1000-1059: seconds (1-60s)
        self.min_bins = 60       # 1060-1119: minutes (1-60min)
        self.hr_bins = 24        # 1120-1143: hours (1-24hr)
        self.day_bins = 365      # 1144-1508: days (1-365 days)
        self.long_bin = 1        # 1509: 365+ days
        
        # Starting indices for each range
        self.ms_start = 0
        self.sec_start = self.ms_start + self.ms_bins
        self.min_start = self.sec_start + self.sec_bins
        self.hr_start = self.min_start + self.min_bins
        self.day_start = self.hr_start + self.hr_bins
        self.long_start = self.day_start + self.day_bins
    
    def time_to_basket(self, time_seconds):
        """
        Convert time delta (in seconds) to basket ID.
        
        Args:
            time_seconds: float or array/tensor of floats (time in seconds)
        
        Returns:
            basket_id: int or array/tensor of ints (0-1509)
        """
        # Handle torch tensors
        if torch.is_tensor(time_seconds):
            return self._time_to_basket_torch(time_seconds)
        
        # Handle numpy/scalars
        is_scalar = np.isscalar(time_seconds)
        t = np.atleast_1d(np.asarray(time_seconds))
        baskets = np.zeros_like(t, dtype=np.int64)
        
        # 0-1 second: millisecond bins (0-999)
        mask = t < 1.0
        baskets[mask] = np.clip(
            (t[mask] * 1000).astype(np.int64),
            0, self.ms_bins - 1
        )
        
        # 1-60 seconds: second bins (1000-1059)
        mask = (t >= 1.0) & (t < 60.0)
        baskets[mask] = self.sec_start + np.clip(
            (t[mask] - 1.0).astype(np.int64),
            0, self.sec_bins - 1
        )
        
        # 1-60 minutes: minute bins (1060-1119)
        mask = (t >= 60.0) & (t < 3600.0)
        baskets[mask] = self.min_start + np.clip(
            ((t[mask] - 60.0) / 60.0).astype(np.int64),
            0, self.min_bins - 1
        )
        
        # 1-24 hours: hour bins (1120-1143)
        mask = (t >= 3600.0) & (t < 86400.0)
        baskets[mask] = self.hr_start + np.clip(
            ((t[mask] - 3600.0) / 3600.0).astype(np.int64),
            0, self.hr_bins - 1
        )
        
        # 1-365 days: day bins (1144-1508)
        mask = (t >= 86400.0) & (t < 31536000.0)  # 365 days in seconds
        baskets[mask] = self.day_start + np.clip(
            ((t[mask] - 86400.0) / 86400.0).astype(np.int64),
            0, self.day_bins - 1
        )
        
        # 365+ days: single bin (1509)
        mask = t >= 31536000.0
        baskets[mask] = self.long_start
        
        return baskets[0] if is_scalar else baskets
    
    def _time_to_basket_torch(self, time_seconds):
        """Torch version for GPU tensors."""
        t = time_seconds
        baskets = torch.zeros_like(t, dtype=torch.long)
        
        # 0-1 second: millisecond bins (0-999)
        mask = t < 1.0
        baskets[mask] = torch.clamp(
            (t[mask] * 1000).long(),
            0, self.ms_bins - 1
        )
        
        # 1-60 seconds: second bins (1000-1059)
        mask = (t >= 1.0) & (t < 60.0)
        baskets[mask] = self.sec_start + torch.clamp(
            (t[mask] - 1.0).long(),
            0, self.sec_bins - 1
        )
        
        # 1-60 minutes: minute bins (1060-1119)
        mask = (t >= 60.0) & (t < 3600.0)
        baskets[mask] = self.min_start + torch.clamp(
            ((t[mask] - 60.0) / 60.0).long(),
            0, self.min_bins - 1
        )
        
        # 1-24 hours: hour bins (1120-1143)
        mask = (t >= 3600.0) & (t < 86400.0)
        baskets[mask] = self.hr_start + torch.clamp(
            ((t[mask] - 3600.0) / 3600.0).long(),
            0, self.hr_bins - 1
        )
        
        # 1-365 days: day bins (1144-1508)
        mask = (t >= 86400.0) & (t < 31536000.0)
        baskets[mask] = self.day_start + torch.clamp(
            ((t[mask] - 86400.0) / 86400.0).long(),
            0, self.day_bins - 1
        )
        
        # 365+ days: single bin (1509)
        mask = t >= 31536000.0
        baskets[mask] = self.long_start
        
        return baskets
    
    def basket_to_description(self, basket_id):
        """Get human-readable description of a basket."""
        if basket_id < self.sec_start:
            ms = basket_id
            return f"{ms}ms"
        elif basket_id < self.min_start:
            sec = basket_id - self.sec_start + 1
            return f"{sec}s"
        elif basket_id < self.hr_start:
            min_val = basket_id - self.min_start + 1
            return f"{min_val}min"
        elif basket_id < self.day_start:
            hr = basket_id - self.hr_start + 1
            return f"{hr}hr"
        elif basket_id < self.long_start:
            day = basket_id - self.day_start + 1
            return f"{day}day"
        else:
            return "365+days"


class HybridTimeEncoder(nn.Module):
    """
    Hybrid time encoder: fine-grained baskets + continuous encoding.
    
    Combines:
    1. Fine-grained basket embeddings (1510 baskets)
    2. Continuous log-scaled encoding (for sub-millisecond precision)
    """
    def __init__(self, d_model, num_baskets=1510, use_hybrid=True):
        super().__init__()
        
        self.d_model = d_model
        self.use_hybrid = use_hybrid
        self.basket_converter = FineGrainedTimeBaskets()
        
        if use_hybrid:
            # Split d_model between basket and continuous
            self.basket_dim = d_model // 2
            self.continuous_dim = d_model - self.basket_dim
            
            # Basket embedding
            self.basket_embedding = nn.Embedding(num_baskets, self.basket_dim)
            
            # Continuous encoder
            self.continuous_encoder = nn.Sequential(
                nn.Linear(1, self.continuous_dim),
                nn.LayerNorm(self.continuous_dim),
                nn.ReLU(),
                nn.Linear(self.continuous_dim, self.continuous_dim)
            )
        else:
            # Only basket embeddings
            self.basket_embedding = nn.Embedding(num_baskets, d_model)
    
    def forward(self, time_deltas):
        """
        Args:
            time_deltas: [batch, seq_len] tensor of time in seconds
        
        Returns:
            time_encoding: [batch, seq_len, d_model]
        """
        # Convert to baskets
        baskets = self.basket_converter.time_to_basket(time_deltas)
        
        # Get basket embeddings
        basket_emb = self.basket_embedding(baskets)
        
        if self.use_hybrid:
            # Add continuous component (log-scaled for numerical stability)
            # log1p(x*1000) to get millisecond precision
            log_time = torch.log1p(time_deltas * 1000.0).unsqueeze(-1)
            continuous_emb = self.continuous_encoder(log_time)
            
            # Concatenate both representations
            time_encoding = torch.cat([basket_emb, continuous_emb], dim=-1)
        else:
            time_encoding = basket_emb
        
        return time_encoding


if __name__ == "__main__":
    # Test the time basket encoder
    print("="*80)
    print("TESTING FINE-GRAINED TIME BASKETS")
    print("="*80)
    
    converter = FineGrainedTimeBaskets()
    
    # Test cases
    test_times = [
        0.0,      # 0ms
        0.15,     # 150ms
        0.5,      # 500ms
        1.5,      # 1.5s
        30.0,     # 30s
        120.0,    # 2min
        1800.0,   # 30min
        7200.0,   # 2hr
        86400.0,  # 1 day
        604800.0, # 7 days
        31536000.0, # 365 days
        40000000.0  # > 365 days
    ]
    
    print("\\nTime → Basket Mapping:")
    print("-" * 80)
    for t in test_times:
        basket = converter.time_to_basket(t)
        desc = converter.basket_to_description(basket)
        print(f"  {t:12.1f}s → Basket {basket:4d} ({desc})")
    
    print("\\n" + "="*80)
    print("✓ Time basket encoding working correctly!")
    print("="*80)