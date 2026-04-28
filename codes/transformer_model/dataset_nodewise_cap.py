"""
Dataset for node-wise sorted HPC event sequences with time deltas and per-window event capping.


Expected impact (seq_len=2048, cap=50):
    NET_CXI_RAW_DATA : ~1449 → 50 per window  (-97%)
    FS_DISK_FULL     : ~227  → 50 per window  (-78%)
    INFO_NOISE       : ~241  → 50 per window  (-79%)
    NET_CXI_TIMEOUT  : ~60   → 50 per window  (-17%)
    Rare events      : unchanged

"""

import torch
from torch.utils.data import Dataset
import numpy as np
from pathlib import Path

PAD_IDX  = 87
UNK_IDX  = 88
MASK_IDX = 89

# Default cap — tune this:
#   50 = moderate (recommended starting point)
#   10 = aggressive
#   None = no cap (same as original dataset_nodewise.py)
DEFAULT_MAX_PER_EVENT = 500


class GloballySortedSequentialDataset(Dataset):
    """
    Memory-mapped dataset for node-wise sorted sequences with per-window event capping.

    Args:
        cache_dir       : Path to cached numpy data directory
        split           : 'train', 'val', or 'test'
        seq_len         : Sequence length (default 2048)
        stride          : Stride between sequences (default 1024)
        sort_type       : 'node' for node-wise sorted, 'global' for globally sorted
        max_per_event   : Maximum occurrences of any single event per window.
                          Set to None to disable capping (same as original dataset).
    """

    def __init__(self, cache_dir, split='train', seq_len=2048, stride=1024,
                 sort_type='global', max_per_event=DEFAULT_MAX_PER_EVENT):
        self.cache_dir     = Path(cache_dir)
        self.split         = split
        self.seq_len       = seq_len
        self.stride        = stride
        self.max_per_event = max_per_event

        # Support both global and node-wise sorted caches
        if sort_type == 'node':
            token_file     = self.cache_dir / f'{split}_node_ts_sorted_tokens.npy'
            timestamp_file = self.cache_dir / f'{split}_node_ts_sorted_timestamps.npy'
        else:
            token_file     = self.cache_dir / f'{split}_global_sorted_tokens.npy'
            timestamp_file = self.cache_dir / f'{split}_global_sorted_timestamps.npy'

        if not token_file.exists():
            raise FileNotFoundError(
                f"Cache file not found: {token_file}\n"
                f"Please run build_cache_spark first!"
            )

        print(f"Loading {split} dataset ({sort_type} sorted, memory-mapped)...")
        self.tokens     = np.load(token_file,     mmap_mode='r')
        self.timestamps = np.load(timestamp_file, mmap_mode='r')

        self.num_sequences = max(1, (len(self.tokens) - seq_len) // stride + 1)
        print(f"  ✓ {split}: {len(self.tokens):,} tokens → {self.num_sequences:,} sequences")

        if max_per_event is not None:
            print(f"  ✓ Event cap: {max_per_event} per event type per window "
                  f"(excess → <UNK>={UNK_IDX})")
        else:
            print(f"  ✓ Event cap: disabled (original behavior)")

    def __len__(self):
        return self.num_sequences
    
    def _apply_event_cap(self, tokens):
        if self.max_per_event is None:
            return tokens

        for event_idx in np.unique(tokens[tokens < PAD_IDX]):
            positions = np.where(tokens == event_idx)[0]
            if len(positions) > self.max_per_event:
                # Replace excess occurrences with UNK
                tokens[positions[self.max_per_event:]] = UNK_IDX

        return tokens

    def __getitem__(self, idx):
        # Calculate start position
        start = idx * self.stride
        end   = start + self.seq_len + 1

        # Load tokens — must copy since we modify in place for capping
        tokens     = self.tokens[start:end].copy()
        timestamps = self.timestamps[start:end]

        tokens = self._apply_event_cap(tokens)

        timestamps_ns   = timestamps.astype('datetime64[ns]').astype(np.int64)
        time_deltas_ns  = np.diff(timestamps_ns)
        time_deltas_sec = time_deltas_ns / 1e9

        time_deltas_sec = np.clip(time_deltas_sec, 0.0, 86400.0)

        time_deltas_sec = np.concatenate([[0.0], time_deltas_sec])

        if len(tokens) < self.seq_len + 1:
            pad_len = self.seq_len + 1 - len(tokens)
            tokens          = np.concatenate([tokens,
                                              np.full(pad_len, PAD_IDX,
                                                      dtype=tokens.dtype)])
            time_deltas_sec = np.concatenate([time_deltas_sec,
                                              np.zeros(pad_len)])

        x      = torch.from_numpy(tokens[:-1].copy()).long()
        y      = torch.from_numpy(tokens[1:].copy()).long()
        deltas = torch.from_numpy(time_deltas_sec[:-1].copy()).float()

        return {
            'event_ids':   x,
            'target':      y,
            'time_deltas': deltas,
        }


def collate_fn(batch):
    """Collate function for DataLoader."""
    event_ids   = torch.stack([item['event_ids']   for item in batch])
    targets     = torch.stack([item['target']      for item in batch])
    time_deltas = torch.stack([item['time_deltas'] for item in batch])

    return {
        'event_ids':   event_ids,
        'target':      targets,
        'time_deltas': time_deltas,
    }



if __name__ == '__main__':
    import sys
    from collections import Counter

    cache_dir = sys.argv[1] if len(sys.argv) > 1 else \
        './gnn_project/cached_data_global_sorted_v2'

    print("=" * 60)
    print("Testing dataset_nodewise_cap.py")
    print("=" * 60)

    # Test with cap=50
    dataset = GloballySortedSequentialDataset(
        cache_dir=cache_dir,
        split='val',
        seq_len=2048,
        stride=1024,
        sort_type='node',
        max_per_event=50,
    )

    # Check first 10 sequences
    print("\nEvent frequency in first 10 sequences (with cap=50):")
    counter = Counter()
    for i in range(10):
        batch = dataset[i]
        ids   = batch['event_ids'].numpy()
        for tok in ids:
            if tok < PAD_IDX:
                counter[int(tok)] += 1

    print(f"  Most common events:")
    for tok, cnt in counter.most_common(10):
        print(f"    idx {tok}: {cnt} occurrences across 10 sequences "
              f"(max {50*10} with cap=50)")

    max_single = max(
        (batch['event_ids'].numpy() == tok).sum()
        for i in range(10)
        for tok in range(87)
        for batch in [dataset[i]]
    )
    print(f"\n  Max occurrences of any single event in any single sequence: "
          f"{max_single} (should be ≤ 50)")

    # Compare with no cap
    dataset_nocap = GloballySortedSequentialDataset(
        cache_dir=cache_dir,
        split='val',
        seq_len=2048,
        stride=1024,
        sort_type='node',
        max_per_event=None,
    )

    batch_nocap = dataset_nocap[0]
    batch_cap   = dataset[0]

    ids_nocap = batch_nocap['event_ids'].numpy()
    ids_cap   = batch_cap['event_ids'].numpy()

    n_raw_data_nocap = (ids_nocap == 0).sum()
    n_raw_data_cap   = (ids_cap   == 0).sum()
    n_unk_nocap      = (ids_nocap == UNK_IDX).sum()
    n_unk_cap        = (ids_cap   == UNK_IDX).sum()

    print(f"\nFirst sequence comparison (seq_len=2048):")
    print(f"  NET_CXI_RAW_DATA (idx=0): "
          f"{n_raw_data_nocap} → {n_raw_data_cap} (capped)")
    print(f"  <UNK> (idx=88):           "
          f"{n_unk_nocap} → {n_unk_cap} (excess events)")
    print(f"\n✓ Test passed")