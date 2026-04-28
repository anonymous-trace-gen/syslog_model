"""
Multi-node parallelized intervention-based causal analysis.


Checkpointing:
    Each rank writes ate_partial_rank{N}.pkl  (atomic .tmp → rename on Lustre)
    Rank 0 signals done via rank0_done.flag AFTER merge is complete.
    Other ranks signal done immediately after computation.
    On resubmit: each rank resumes from its own partial checkpoint.

"""

import argparse
import json
import logging
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / 'train_lm'))   #

# from dataset_nodewise import GloballySortedSequentialDataset, collate_fn
from dataset_nodewise_cap import GloballySortedSequentialDataset, collate_fn

from model import SequentialFailureTransformer
from nodewise_parallel_causal_analysis import InterventionCausalAnalyzer

# common.py is co-located in the same causal_intervention/ directory
try:
    from common import LABEL_MAPPING, IDX_TO_LABEL
    _vocab_source = "common.py (causal_intervention/)"
except ImportError:
    LABEL_MAPPING = None
    IDX_TO_LABEL  = None
    _vocab_source = "fallback (integer labels)"

# Total vocab size including special tokens
VOCAB_SIZE = 90
# Number of real (non-special) events
N_REAL_EVENTS = 87
# Special token names — never used as cause/effect
SPECIAL_TOKEN_NAMES = {"<PAD>", "<UNK>", "<MASK>"}



# Rank / environment helpers
# *************

def get_rank_and_world():
    """Read rank/world from SLURM env vars. Falls back to 0/1 for interactive."""
    rank       = int(os.environ.get('SLURM_PROCID',  0))
    world_size = int(os.environ.get('SLURM_NTASKS',  1))
    local_rank = int(os.environ.get('SLURM_LOCALID', 0))
    return rank, world_size, local_rank


def setup_logging(output_dir: Path, rank: int):
    """Each rank writes to its own log file; only rank 0 also logs to stdout."""
    handlers = [
        logging.FileHandler(output_dir / f'causal_rank{rank}.log', mode='a'),
    ]
    if rank == 0:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s [rank{rank}] %(levelname)s %(message)s',
        handlers=handlers,
        force=True,
    )


# Vocab / model helpers
# *********************

def build_fallback_vocab():
    """
    If utils/common.py is not importable, build integer-label vocab.
    Special tokens are placed at indices 89, 90, 91 to match training.
    """
    logging.warning(
        "utils.common not importable — using integer labels.\n"
        "  ATE output will show indices instead of event names.\n"
        "  Fix: ensure revised_code/ is on sys.path before running."
    )
    label_mapping = {str(i): i for i in range(N_REAL_EVENTS)}
    # label_mapping.update({"<PAD>": 89, "<UNK>": 90, "<MASK>": 91})
    label_mapping.update({"<PAD>": 87, "<UNK>": 88, "<MASK>": 89})

    idx_to_label  = {v: k for k, v in label_mapping.items()}
    return label_mapping, idx_to_label


def load_model(checkpoint_path: str, args, device: torch.device):
    model = SequentialFailureTransformer(
        vocab_size       = VOCAB_SIZE,
        d_model          = args.d_model,
        num_layers       = args.num_layers,
        num_heads        = args.num_heads,
        max_seq_len      = args.seq_len,
        num_time_baskets = 1510,
    ).to(device)

    ckpt  = torch.load(checkpoint_path, map_location='cpu')
    state = ckpt.get('model_state_dict', ckpt)
    state = {k.replace('module.', ''): v for k, v in state.items()}
    model.load_state_dict(state)
    model.eval()

    n_params = sum(p.numel() for p in model.parameters())
    logging.info(f"Model: {n_params:,} parameters  |  "
                 f"val_loss in ckpt: {ckpt.get('val_loss', 'N/A')}")
    return model



# Per-rank ATE computation
# *********************

def partial_ckpt_path(output_dir: Path, rank: int) -> Path:
    return output_dir / f'ate_partial_rank{rank}.pkl'


def _save_partial_checkpoint(ckpt_path: Path, row_mapping,
                              ate, ci_lo, ci_hi, tgap,
                              completed_local_rows: int,
                              total_local_rows: int,
                              rank: int):
    """Atomic write: .tmp → rename (safe on Lustre)."""
    data = {
        'row_mapping':          row_mapping,
        'ate_matrix':           ate,
        'ci_low':               ci_lo,
        'ci_high':              ci_hi,
        'temporal_gap':         tgap,
        'completed_local_rows': completed_local_rows,
        'total_local_rows':     total_local_rows,
        'timestamp':            time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    tmp = Path(str(ckpt_path) + '.tmp')
    with open(tmp, 'wb') as f:
        pickle.dump(data, f)
    tmp.rename(ckpt_path)
    logging.info(
        f"Checkpoint: local row {completed_local_rows}/{total_local_rows} "
        f"({completed_local_rows / total_local_rows * 100:.1f}%)"
    )


def compute_rank_rows(analyzer: InterventionCausalAnalyzer,
                      dataloader: DataLoader,
                      my_rows: list,
                      event_indices: list,
                      n_bootstrap: int,
                      min_occurrences: int,
                      output_dir: Path,
                      rank: int,
                      checkpoint_every: int):
    """
    Compute ATE for cause rows assigned to this rank.
    Resumes automatically from partial checkpoint if one exists.
    """
    n_total   = len(event_indices)
    n_my      = len(my_rows)
    ckpt_path = partial_ckpt_path(output_dir, rank)

    ate_partial   = np.zeros((n_my, n_total), dtype=np.float32)
    ci_lo_partial = np.zeros((n_my, n_total), dtype=np.float32)
    ci_hi_partial = np.zeros((n_my, n_total), dtype=np.float32)
    tgap_partial  = np.zeros((n_my, n_total), dtype=np.float32)
    start_local_i = 0

    # Resume from checkpoint
    if ckpt_path.exists():
        try:
            with open(ckpt_path, 'rb') as f:
                ckpt = pickle.load(f)
            if ckpt.get('row_mapping') == my_rows:
                ate_partial   = ckpt['ate_matrix']
                ci_lo_partial = ckpt['ci_low']
                ci_hi_partial = ckpt['ci_high']
                tgap_partial  = ckpt['temporal_gap']
                start_local_i = ckpt['completed_local_rows']
                logging.info(
                    f"Resumed from local row {start_local_i}/{n_my} "
                    f"({start_local_i / n_my * 100:.1f}%)"
                )
            else:
                logging.warning("Checkpoint row_mapping mismatch — starting fresh")
        except Exception as e:
            logging.warning(f"Checkpoint load failed ({e}) — starting fresh")

    if start_local_i >= n_my:
        logging.info("All rows already complete — nothing to compute")
        return ate_partial, ci_lo_partial, ci_hi_partial, tgap_partial

    # Main loop
    for local_i, global_row_i in tqdm(
        enumerate(my_rows),
        total=n_my, initial=start_local_i,
        desc=f"rank{rank}"
    ):
        if local_i < start_local_i:
            continue

        cause_idx = event_indices[global_row_i]

        for j, effect_idx in enumerate(event_indices):
            if cause_idx == effect_idx:
                continue
            ate, ci_lo, ci_hi, tgap = analyzer.compute_ate(
                dataloader, cause_idx, effect_idx,
                n_bootstrap=n_bootstrap,
                min_occurrences=min_occurrences,
            )
            ate_partial[local_i, j]   = ate
            ci_lo_partial[local_i, j] = ci_lo
            ci_hi_partial[local_i, j] = ci_hi
            tgap_partial[local_i, j]  = tgap

        # Atomic checkpoint after every `checkpoint_every` rows
        if (local_i + 1) % checkpoint_every == 0 or (local_i + 1) == n_my:
            _save_partial_checkpoint(
                ckpt_path, my_rows,
                ate_partial, ci_lo_partial, ci_hi_partial, tgap_partial,
                completed_local_rows=local_i + 1,
                total_local_rows=n_my,
                rank=rank,
            )

    return ate_partial, ci_lo_partial, ci_hi_partial, tgap_partial


# Merge for rank 0 
# *********************

def merge_partial_matrices(output_dir: Path, world_size: int, n_events: int):
    """Merge per-rank partial ATE matrices into one full n_events × n_events matrix."""
    ate_full   = np.zeros((n_events, n_events), dtype=np.float32)
    ci_lo_full = np.zeros((n_events, n_events), dtype=np.float32)
    ci_hi_full = np.zeros((n_events, n_events), dtype=np.float32)
    tgap_full  = np.zeros((n_events, n_events), dtype=np.float32)

    for r in range(world_size):
        path = partial_ckpt_path(output_dir, r)
        if not path.exists():
            logging.warning(f"Missing partial checkpoint for rank {r} — rows will be zero")
            continue
        with open(path, 'rb') as f:
            data = pickle.load(f)

        for local_i, global_i in enumerate(data['row_mapping']):
            ate_full[global_i]   = data['ate_matrix'][local_i]
            ci_lo_full[global_i] = data['ci_low'][local_i]
            ci_hi_full[global_i] = data['ci_high'][local_i]
            tgap_full[global_i]  = data['temporal_gap'][local_i]

        pct = data['completed_local_rows'] / data['total_local_rows'] * 100
        logging.info(
            f"  ✓ Rank {r:3d}: {len(data['row_mapping'])} rows, "
            f"{data['completed_local_rows']}/{data['total_local_rows']} complete "
            f"({pct:.0f}%)"
        )

    return ate_full, ci_lo_full, ci_hi_full, tgap_full


def _wait_for_all_ranks(output_dir: Path, world_size: int,
                        timeout_minutes: int = 700):
    """
    Rank 0 polls for done flags from all other ranks.
    115 min timeout leaves a 5-min buffer before the 2-hour walltime.
    """
    deadline = time.time() + timeout_minutes * 60
    while time.time() < deadline:
        done = [(output_dir / f'rank{r}_done.flag').exists()
                for r in range(1, world_size)] 
        if all(done):
            logging.info("  ✓ All ranks finished")
            return True
        remaining = (deadline - time.time()) / 60
        logging.info(
            f"  Waiting: {sum(done)}/{world_size} ranks done  "
            f"({remaining:.0f} min remaining)"
        )
        time.sleep(30)
    logging.warning("Timeout — proceeding with merge on available partials")
    return False


# Main

def main():
    parser = argparse.ArgumentParser(
        description='Multi-node parallelized causal analysis — SC2026'
    )
    # Paths
    parser.add_argument('--model_path',   required=True,
                        help='Path to best_model.pt checkpoint')
    parser.add_argument('--cache_dir',    required=True,
                        help='Path to cached_data_global/')
    parser.add_argument('--output_dir',   required=True,
                        help='Output directory (Lustre path)')
    # Dataset
    parser.add_argument('--seq_len',      type=int, default=2048)
    parser.add_argument('--stride',       type=int, default=1024)
    parser.add_argument('--batch_size',   type=int, default=64,
                        help='Per-GPU batch size for ATE forward passes')
    parser.add_argument('--split',        default='val')
    parser.add_argument('--max_analysis_sequences', type=int, default=10000,
                        help='Subsample val set to this many sequences '
                             '(fixed seed=42 for reproducibility)')
    # Model architecture — must match training
    parser.add_argument('--d_model',      type=int, default=512)
    parser.add_argument('--num_layers',   type=int, default=6)
    parser.add_argument('--num_heads',    type=int, default=8)
    # Analysis
    parser.add_argument('--top_k_events', type=int, default=None,
                        help='Analyse top-K most frequent events. '
                             'Default=None → all 89 real events')
    parser.add_argument('--n_bootstrap',  type=int, default=500,
                        help='Bootstrap iterations per pair (500 = paper quality)')
    parser.add_argument('--significance_threshold', type=float, default=0.02,
                        help='Minimum ATE to accept an edge')
    parser.add_argument('--min_occurrences', type=int, default=10,
                        help='Skip pair if cause appears fewer than N times')
    parser.add_argument('--max_cascade_depth', type=int, default=5)
    parser.add_argument('--checkpoint_every', type=int, default=1,
                        help='Save partial checkpoint every N completed rows')
    parser.add_argument('--require_temporal_order', action='store_true',
                        default=False,
                        help='Reject edges where cause does not precede effect')
    # Control
    parser.add_argument('--merge_only',   action='store_true',
                        help='Skip computation — only merge existing partials '
                             'and run downstream steps (rank 0 only)')
    
    parser.add_argument('--world_size', type=int, default=None,
                    help='Override world_size for merge_only mode')
    
    parser.add_argument('--max_per_event', type=int, default=10,
                    help='Cap per event type per window — must match training')
    args = parser.parse_args()

    # ── Rank / device setup ───────────────────────────────────────────
    rank, world_size, local_rank = get_rank_and_world()
    if args.merge_only and args.world_size is not None:
        world_size = args.world_size
    # device     = torch.device(
    #     f'cuda:{local_rank}' if torch.cuda.is_available() else 'cpu'
    # )
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(output_dir, rank)

    if rank == 0:
        logging.info("=" * 72)
        logging.info(f"MULTI-NODE CAUSAL ANALYSIS  (SC2026)  — {world_size} ranks")
        logging.info("=" * 72)
        logging.info(f"Model    : {args.model_path}")
        logging.info(f"Output   : {args.output_dir}")
        logging.info(f"Vocab    : {_vocab_source}")
        logging.info(f"Events   : {args.top_k_events or 'all 89 real'} "
                     f"(special tokens excluded)")
        logging.info(f"Bootstrap: {args.n_bootstrap}  "
                     f"Threshold: {args.significance_threshold}  "
                     f"Max seqs: {args.max_analysis_sequences:,}")
        logging.info("=" * 72)

    # Vocabulary 
    global LABEL_MAPPING, IDX_TO_LABEL
    if LABEL_MAPPING is None:
        LABEL_MAPPING, IDX_TO_LABEL = build_fallback_vocab()
    else:
        logging.info(f"Vocabulary: {len(LABEL_MAPPING)} tokens  "
                     f"({sum(1 for k in LABEL_MAPPING if k not in SPECIAL_TOKEN_NAMES)} real, "
                     f"3 special)  source: {_vocab_source}")

    # Load model 
    model = load_model(args.model_path, args, device)

    # Dataset 
    dataset = GloballySortedSequentialDataset(
        cache_dir=args.cache_dir,
        split=args.split,
        seq_len=args.seq_len,
        stride=args.stride,
        sort_type='node',
        max_per_event=args.max_per_event 
    )
    if args.max_analysis_sequences and len(dataset) > args.max_analysis_sequences:
        rng     = np.random.default_rng(seed=42)
        indices = rng.choice(len(dataset),
                             size=args.max_analysis_sequences, replace=False)
        dataset = Subset(dataset, sorted(indices.tolist()))

    dataloader = DataLoader(
        dataset, batch_size=args.batch_size, shuffle=False,
        collate_fn=collate_fn, num_workers=4, pin_memory=True,
    )
    logging.info(
        f"Dataset: {len(dataset):,} sequences, {len(dataloader):,} batches"
    )

    # Analyzer
    analyzer = InterventionCausalAnalyzer(
        model=model,
        label_mapping=LABEL_MAPPING,
        idx_to_label=IDX_TO_LABEL,
        device=str(device),
    )

    event_indices_path = output_dir / 'event_indices.json'

    if rank == 0 and not event_indices_path.exists():
        event_indices = analyzer.get_analysis_event_indices(
            top_k=args.top_k_events,
            dataloader=dataloader if args.top_k_events else None,
        )
        with open(event_indices_path, 'w') as f:
            json.dump(event_indices, f)
        logging.info(f"event_indices.json written: {len(event_indices)} events")


    _wait_for_file(event_indices_path, timeout_sec=60, rank=rank)
    with open(event_indices_path) as f:
        event_indices = json.load(f)

    n_events = len(event_indices)
    logging.info(f"Analysing {n_events} events  "
             f"({N_REAL_EVENTS} real — 0 special tokens included)")

    special_in_list = [
        idx for idx in event_indices
        if idx in analyzer._special_indices
    ]
    if special_in_list:
        logging.error(
            f"BUG: special token indices {special_in_list} found in "
            f"event_indices — they will be skipped in compute_ate()"
        )

    my_rows = list(range(rank, n_events, world_size))
    logging.info(f"Assigned {len(my_rows)} rows: "
                 f"{my_rows[:6]}{'...' if len(my_rows) > 6 else ''}")

    if not args.merge_only:
        t0 = time.time()
        compute_rank_rows(
            analyzer         = analyzer,
            dataloader       = dataloader,
            my_rows          = my_rows,
            event_indices    = event_indices,
            n_bootstrap      = args.n_bootstrap,
            min_occurrences  = args.min_occurrences,
            output_dir       = output_dir,
            rank             = rank,
            checkpoint_every = args.checkpoint_every,
        )
        elapsed = (time.time() - t0) / 60
        logging.info(f"Computation finished in {elapsed:.1f} min")

        # Signal done (rank 0 signals AFTER merge below)
        if rank != 0:
            (output_dir / f'rank{rank}_done.flag').write_text(
                time.strftime('%Y-%m-%d %H:%M:%S')
            )

    if rank == 0:
        if not args.merge_only:
            # Wait for all other ranks
            _wait_for_all_ranks(output_dir, world_size)

        logging.info("\n" + "=" * 72)
        logging.info("MERGE PHASE")
        logging.info("=" * 72)
        ate_full, ci_lo_full, ci_hi_full, tgap_full = merge_partial_matrices(
            output_dir, world_size, n_events
        )

        # Inject merged matrices into analyzer
        analyzer.ate_matrix      = ate_full
        analyzer.ci_low_matrix   = ci_lo_full
        analyzer.ci_high_matrix  = ci_hi_full
        analyzer.temporal_matrix = tgap_full > 0
        analyzer._event_indices  = event_indices

        # Save 
        np.save(output_dir / 'ate_matrix_full.npy',  ate_full)
        np.save(output_dir / 'ci_low_full.npy',      ci_lo_full)
        np.save(output_dir / 'ci_high_full.npy',     ci_hi_full)
        np.save(output_dir / 'tgap_full.npy',        tgap_full)
        logging.info("Full matrices saved.")

        # Extract causal edges
        logging.info("\n" + "=" * 72)
        logging.info("EDGE EXTRACTION")
        logging.info("=" * 72)
        edges = analyzer.extract_edges(
            significance_threshold=args.significance_threshold,
            require_temporal_order=args.require_temporal_order,
        )
        analyzer.print_top_edges(n=30)

        # Cascade discovery
        logging.info("\n" + "=" * 72)
        logging.info("CASCADE DISCOVERY")
        logging.info("=" * 72)
        cascades = analyzer.discover_cascades(
            max_depth=args.max_cascade_depth,
            min_path_ate=args.significance_threshold,
        )
        analyzer.print_top_cascades(cascades, n=20)

        # Save all outputs
        logging.info("\n" + "=" * 72)
        logging.info("SAVING OUTPUTS")
        logging.info("=" * 72)
        analyzer.save(output_dir)

        analyzer.plot_ate_heatmap(
            output_dir / 'ate_heatmap.png', top_n=n_events
        )
        analyzer.plot_causal_graph(
            output_dir / 'causal_graph.png', top_n_edges=50
        )
        analyzer.plot_category_summary(
            output_dir / 'category_summary.png'
        )
        analyzer.export_for_triangulation(
            output_dir / 'transformer_edges_for_triangulation.csv'
        )

        import pandas as pd
        pd.DataFrame(cascades).to_csv(
            output_dir / 'cascades.csv', index=False
        )

        # Rank 0 done flag — written LAST so resubmit knows merge completed
        (output_dir / 'rank0_done.flag').write_text(
            time.strftime('%Y-%m-%d %H:%M:%S')
        )

        logging.info("\n" + "=" * 72)
        logging.info(f"COMPLETE")
        logging.info(f"  Events analysed : {n_events}")
        logging.info(f"  Edges accepted  : {len(edges)}")
        logging.info(f"  Cascades found  : {len(cascades)}")
        logging.info(f"  Output dir      : {output_dir}")
        logging.info("=" * 72)



def _wait_for_file(path: Path, timeout_sec: int = 60, rank: int = 0):
    deadline = time.time() + timeout_sec
    while True:
        if path.exists() and path.stat().st_size > 0:
            # Also verify it's valid JSON
            try:
                with open(path) as f:
                    json.load(f)
                return  # file exists and is valid JSON
            except (json.JSONDecodeError, OSError):
                pass  # not ready yet, keep waiting
        if time.time() > deadline:
            raise TimeoutError(f"[rank{rank}] Timed out waiting for {path}")
        time.sleep(2)


if __name__ == '__main__':
    main()