"""
Training script for Sequential Language Model with Fine-Grained Time Encoding.
WITH ROBUST CHECKPOINTING AND RESUME CAPABILITY.
"""

import os
import torch
import torch.nn as nn
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler
from pathlib import Path
import argparse
import logging
from tqdm import tqdm
import time
import json
from datetime import timedelta
import numpy as np

# from dataset_nodewise import GloballySortedSequentialDataset, collate_fn
from dataset_nodewise_cap import GloballySortedSequentialDataset, collate_fn

from model import SequentialFailureTransformer

PAD_IDX   = 87
UNK_IDX   = 88
MASK_IDX  = 89

def setup_distributed():
    import os
    from datetime import timedelta
    
    rank = int(os.environ.get('SLURM_PROCID', 0))
    world_size = int(os.environ.get('SLURM_NTASKS', 1))
    
    # With --gpu-bind, each task sees only its assigned GPU as device 0
    local_rank = 0
    
    if rank == 0:
        print(f"✓ Initializing {world_size} processes with GPU binding", flush=True)
    
    torch.cuda.set_device(0)
    
    dist.init_process_group(
        backend='nccl',
        init_method='env://',
        world_size=world_size,
        rank=rank,
        timeout=timedelta(minutes=30)
    )
    
    if rank == 0:
        print(f"✓ Distributed initialized!", flush=True)
    
    return rank, world_size, 0


def save_checkpoint(model, optimizer, scheduler, epoch, batch_idx, args, 
                    train_loss, train_acc, val_loss, val_acc, 
                    best_val_loss, output_dir, is_best=False):
    """
    Save checkpoint with all training state.
    """
    checkpoint = {
        'epoch': epoch,
        'batch_idx': batch_idx,
        'model_state_dict': model.module.state_dict() if hasattr(model, 'module') else model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict() if scheduler is not None else None,
        'train_loss': train_loss,
        'train_acc': train_acc,
        'val_loss': val_loss,
        'val_acc': val_acc,
        'best_val_loss': best_val_loss,
        'args': vars(args),
        'timestamp': time.time()
    }
    
    if is_best:
        checkpoint_path = Path(output_dir) / 'best_model.pt'
        torch.save(checkpoint, checkpoint_path)
        logging.info(f"  ✓ Saved BEST model (val_loss: {val_loss:.4f})")
    else:
        checkpoint_path = Path(output_dir) / 'latest_checkpoint.pt'
        torch.save(checkpoint, checkpoint_path)
        
        # Also save periodic checkpoints
        periodic_path = Path(output_dir) / f'checkpoint_epoch_{epoch}.pt'
        torch.save(checkpoint, periodic_path)
        logging.info(f"  ✓ Saved checkpoint: epoch {epoch}")
    
    # Save training state JSON (for easy inspection)
    state_file = Path(output_dir) / 'training_state.json'
    with open(state_file, 'w') as f:
        json.dump({
            'epoch': epoch,
            'batch_idx': batch_idx,
            'train_loss': float(train_loss),
            'train_acc': float(train_acc),
            'val_loss': float(val_loss),
            'val_acc': float(val_acc),
            'best_val_loss': float(best_val_loss),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, indent=2)
    
    return checkpoint_path


def load_checkpoint(checkpoint_path, model, optimizer=None, scheduler=None):
    """
    Load checkpoint and restore training state.
    """
    if not Path(checkpoint_path).exists():
        return None
    
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    
    # Load model state
    if hasattr(model, 'module'):
        model.module.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint['model_state_dict'])
    
    # Load optimizer state
    if optimizer is not None and checkpoint.get('optimizer_state_dict') is not None:
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    
    # Load scheduler state
    if scheduler is not None and checkpoint.get('scheduler_state_dict') is not None:
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
    
    return checkpoint


def train_epoch(model, dataloader, optimizer, criterion, device, epoch, rank, world_size, 
                scheduler=None, start_batch=0, output_dir=None, args=None, best_val_loss=float('inf')):
    """
    Train for one epoch with periodic checkpointing.
    """
    model.train()
    total_loss = 0
    total_correct = 0
    total_tokens = 0
    num_batches = 0
    
    # Checkpoint every N batches
    CHECKPOINT_INTERVAL = 500  # Save every 500 batches
    
    # Only show progress bar on rank 0
    iterator = tqdm(dataloader, desc=f"Epoch {epoch}") if rank == 0 else dataloader
    
    for batch_idx, batch in enumerate(iterator):
        # Skip batches if resuming
        if batch_idx < start_batch:
            continue
        
        event_ids = batch['event_ids'].to(device)
        targets = batch['target'].to(device)
        time_deltas = batch['time_deltas'].to(device)
        
        # Forward pass
        logits = model(event_ids, time_deltas)
        
        # Reshape for loss calculation
        logits_flat = logits.reshape(-1, logits.size(-1))
        targets_flat = targets.reshape(-1)
        
        # Calculate loss
        loss = criterion(logits_flat, targets_flat)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        if scheduler is not None:
            scheduler.step()
        
        # Track metrics
        with torch.no_grad():
            predictions = logits_flat.argmax(dim=-1)
            # mask = targets_flat != PAD_IDX
            mask = (targets_flat != PAD_IDX) & (targets_flat != UNK_IDX)
            correct = (predictions[mask] == targets_flat[mask]).sum().item()
            num_valid = mask.sum().item()
            
            total_loss += loss.item()
            total_correct += correct
            total_tokens += num_valid
            num_batches += 1
        
        # Update progress bar
        if rank == 0 and isinstance(iterator, tqdm):
            accuracy = correct / max(num_valid, 1)
            iterator.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{accuracy:.3f}',
                'batch': f'{batch_idx}/{len(dataloader)}'
            })
        
        # Periodic checkpoint (every CHECKPOINT_INTERVAL batches)
        # if rank == 0 and output_dir is not None and (batch_idx + 1) % CHECKPOINT_INTERVAL == 0:
        #     avg_loss = total_loss / num_batches
        #     avg_acc = total_correct / max(total_tokens, 1)
            
        #     logging.info(f"\\n  Checkpoint at batch {batch_idx+1}/{len(dataloader)}")
        #     save_checkpoint(
        #         model, optimizer, scheduler, epoch, batch_idx,
        #         args, avg_loss, avg_acc, best_val_loss, 0.0,
        #         best_val_loss, output_dir, is_best=False
        #     )
        if (batch_idx + 1) % CHECKPOINT_INTERVAL == 0:
            # ✅ ALL ranks must reach this point and stop
            dist.barrier() 
            
            if rank == 0 and output_dir is not None:
                avg_loss = total_loss / max(num_batches, 1)
                avg_acc = total_correct / max(total_tokens, 1)
                
                logging.info(f"\n[Batch {batch_idx+1}] Rank 0 is saving checkpoint...")
                save_checkpoint(
                    model, optimizer, scheduler, epoch, batch_idx,
                    args, avg_loss, avg_acc, best_val_loss, 0.0,
                    best_val_loss, output_dir, is_best=False
                )
            
            # ✅ ALL ranks wait for Rank 0 to finish writing before starting the next batch
            dist.barrier()
    
    avg_loss = total_loss / num_batches
    avg_accuracy = total_correct / max(total_tokens, 1)
    
    # Synchronize metrics across all GPUs
    avg_loss_tensor = torch.tensor(avg_loss, device=device)
    avg_acc_tensor = torch.tensor(avg_accuracy, device=device)
    
    dist.all_reduce(avg_loss_tensor, op=dist.ReduceOp.SUM)
    dist.all_reduce(avg_acc_tensor, op=dist.ReduceOp.SUM)
    
    avg_loss = avg_loss_tensor.item() / world_size
    avg_accuracy = avg_acc_tensor.item() / world_size
    
    return avg_loss, avg_accuracy


def validate(model, dataloader, criterion, device, rank, world_size):
    """Validate the model."""
    model.eval()
    total_loss = 0
    total_correct = 0
    total_tokens = 0
    num_batches = 0
    
    with torch.no_grad():
        for batch in dataloader:
            event_ids = batch['event_ids'].to(device)
            targets = batch['target'].to(device)
            time_deltas = batch['time_deltas'].to(device)
            
            logits = model(event_ids, time_deltas)
            
            logits_flat = logits.reshape(-1, logits.size(-1))
            targets_flat = targets.reshape(-1)
            
            loss = criterion(logits_flat, targets_flat)
            
            predictions = logits_flat.argmax(dim=-1)
            # mask = targets_flat != PAD_IDX
            mask = (targets_flat != PAD_IDX) & (targets_flat != UNK_IDX)
            correct = (predictions[mask] == targets_flat[mask]).sum().item()
            num_valid = mask.sum().item()
            
            total_loss += loss.item()
            total_correct += correct
            total_tokens += num_valid
            num_batches += 1
    
    avg_loss = total_loss / num_batches
    avg_accuracy = total_correct / max(total_tokens, 1)
    
    # Synchronize across GPUs
    avg_loss_tensor = torch.tensor(avg_loss, device=device)
    avg_acc_tensor = torch.tensor(avg_accuracy, device=device)
    
    dist.all_reduce(avg_loss_tensor, op=dist.ReduceOp.SUM)
    dist.all_reduce(avg_acc_tensor, op=dist.ReduceOp.SUM)
    
    avg_loss = avg_loss_tensor.item() / world_size
    avg_accuracy = avg_acc_tensor.item() / world_size
    
    return avg_loss, avg_accuracy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache_dir', type=str, required=True)
    parser.add_argument('--output_dir', type=str, required=True)
    parser.add_argument('--batch_size', type=int, default=16)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--d_model', type=int, default=512)
    parser.add_argument('--num_layers', type=int, default=6)
    parser.add_argument('--num_heads', type=int, default=8)
    parser.add_argument('--seq_len', type=int, default=2048)
    parser.add_argument('--stride', type=int, default=1024)
    parser.add_argument('--lr', type=float, default=0.0001)
    parser.add_argument('--warmup_steps', type=int, default=1000)
    parser.add_argument('--resume', type=str, default=None, help='Path to checkpoint to resume from')
    parser.add_argument('--auto_resume', action='store_true', help='Auto-resume from latest checkpoint if exists')
    parser.add_argument('--sort_type', type=str, default='global', 
                    choices=['global', 'node'],
                    help='Cache sort type: global or node')
    parser.add_argument('--event_weights', type=str, default=None,
                    help='Path to event_weights.npy for balanced training')
    parser.add_argument('--max_per_event', type=int, default=500,
                    help='Cap per event type per window (None=disabled)')
    args = parser.parse_args()
    
    # Setup distributed training
    rank, world_size, local_rank = setup_distributed()

    device = torch.device(f'cuda:0')
    
    # Setup logging (only on rank 0)
    if rank == 0:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(output_dir / 'training.log', mode='a'),  # Append mode
                logging.StreamHandler()
            ]
        )
        logging.info("\\n" + "="*80)
        logging.info("SEQUENTIAL LM WITH FINE-GRAINED TIME ENCODING")
        logging.info("="*80)
        logging.info(f"Nodes: {world_size // 8}")
        logging.info(f"GPUs: {world_size}")
        logging.info(f"Batch size per GPU: {args.batch_size}")
        logging.info(f"Effective batch size: {args.batch_size * world_size}")
        logging.info(f"Sequence length: {args.seq_len}")
        logging.info(f"Stride: {args.stride}")
        logging.info(f"Model dim: {args.d_model}")
        logging.info(f"Layers: {args.num_layers}")
        logging.info(f"Heads: {args.num_heads}")
        logging.info(f"Time baskets: 1510 (fine-grained)")
        logging.info(f"Total epochs: {args.epochs}")
        logging.info("="*80)
    
    # Load datasets
    if rank == 0:
        logging.info("\\nLoading datasets (memory-mapped)...")
    else:
        # Optional: slight delay for non-zero ranks to spread metadata load
        time.sleep(rank % 10 * 0.1)
    
    max_per_event = args.max_per_event if args.max_per_event > 0 else None
    train_dataset = GloballySortedSequentialDataset(
        cache_dir=args.cache_dir,
        split='train',
        seq_len=args.seq_len,
        stride=args.stride,
        sort_type=args.sort_type,
        max_per_event=max_per_event
    )
    
    val_dataset = GloballySortedSequentialDataset(
        cache_dir=args.cache_dir,
        split='val',
        seq_len=args.seq_len,
        stride=args.stride,
        sort_type=args.sort_type,
        max_per_event=max_per_event
    )
    
    # Create distributed samplers
    train_sampler = DistributedSampler(
        train_dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=True
    )
    
    val_sampler = DistributedSampler(
        val_dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=False
    )
    
    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        sampler=train_sampler,
        collate_fn=collate_fn,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        sampler=val_sampler,
        collate_fn=collate_fn,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )
    
    if rank == 0:
        logging.info(f"✓ Datasets loaded")
        logging.info(f"  Train batches: {len(train_loader):,}")
        logging.info(f"  Val batches: {len(val_loader):,}")
    
    # Create model
    VOCAB_SIZE = 90
    
    if rank == 0:
        logging.info(f"\\nCreating model (vocab_size={VOCAB_SIZE})...")
    
    model = SequentialFailureTransformer(
        vocab_size=VOCAB_SIZE,
        d_model=args.d_model,
        num_layers=args.num_layers,
        num_heads=args.num_heads,
        max_seq_len=args.seq_len,
        num_time_baskets=1510
    ).to(device)
    
    # Wrap with DDP
    model = DDP(model, device_ids=[0], find_unused_parameters=False)

    
    if rank == 0:
        num_params = sum(p.numel() for p in model.parameters())
        logging.info(f"✓ Model created ({num_params:,} parameters)")
    
    # Optimizer
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.lr,
        betas=(0.9, 0.98),
        eps=1e-9,
        weight_decay=0.01
    )
    
    # Loss function
    # criterion = nn.CrossEntropyLoss(ignore_index=PAD_IDX)
    if args.event_weights and Path(args.event_weights).exists():
        weights = np.load(args.event_weights)
        weight_tensor = torch.zeros(90, dtype=torch.float32)
        weight_tensor[:87] = torch.tensor(weights, dtype=torch.float32)
        weight_tensor[87] = 0.0   # <PAD>
        weight_tensor[88] = 0.0   # <UNK>
        weight_tensor[89] = 0.0   # <MASK>
        criterion = nn.CrossEntropyLoss(
            weight=weight_tensor.to(device),
            ignore_index=87
        )
        if rank == 0:
            logging.info(f"Using balanced loss weights from {args.event_weights}")
            logging.info(f"  Weight range: {weights.min():.4f} - {weights.max():.4f}")
    else:
        criterion = nn.CrossEntropyLoss(ignore_index=87)
        if rank == 0:
            logging.info("Using uniform loss weights")
    
    # Learning rate scheduler
    def lr_lambda(step):
        if step < args.warmup_steps:
            return step / args.warmup_steps
        return max(0.1, 1.0 - (step - args.warmup_steps) / (len(train_loader) * args.epochs))
    
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    
    # Resume from checkpoint
    start_epoch = 1
    start_batch = 0
    best_val_loss = float('inf')
    
    # Auto-resume from latest checkpoint
    if args.auto_resume:
        latest_checkpoint = Path(args.output_dir) / 'latest_checkpoint.pt'
        if latest_checkpoint.exists():
            args.resume = str(latest_checkpoint)
    
    if args.resume and Path(args.resume).exists():
        if rank == 0:
            logging.info(f"\\n{'='*80}")
            logging.info(f"RESUMING FROM CHECKPOINT: {args.resume}")
            logging.info(f"{'='*80}")
        
        checkpoint = load_checkpoint(args.resume, model, optimizer, scheduler)
        
        if checkpoint is not None:
            start_epoch = checkpoint['epoch']
            start_batch = checkpoint.get('batch_idx', 0) + 1
            best_val_loss = checkpoint.get('best_val_loss', float('inf'))
            
            if rank == 0:
                logging.info(f"✓ Resumed from epoch {start_epoch}, batch {start_batch}")
                logging.info(f"  Best val loss so far: {best_val_loss:.4f}")
                logging.info(f"  Previous train loss: {checkpoint.get('train_loss', 0):.4f}")
                logging.info(f"  Previous val loss: {checkpoint.get('val_loss', 0):.4f}")
                logging.info(f"{'='*80}\\n")
            
            # If we finished the epoch, start from next epoch
            if start_batch >= len(train_loader):
                start_epoch += 1
                start_batch = 0
    
    # Training loop
    if rank == 0:
        logging.info("\\n" + "="*80)
        logging.info("STARTING TRAINING")
        logging.info(f"Starting from epoch {start_epoch}/{args.epochs}")
        logging.info("="*80)
    
    for epoch in range(start_epoch, args.epochs + 1):
        # Set epoch for sampler
        train_sampler.set_epoch(epoch)
        
        # Train
        epoch_start_time = time.time()
        train_loss, train_acc = train_epoch(
            model, train_loader, optimizer, criterion,
            device, epoch, rank, world_size, scheduler,
            start_batch=start_batch if epoch == start_epoch else 0,
            output_dir=args.output_dir if rank == 0 else None,
            args=args,
            best_val_loss=best_val_loss
        )
        
        # Reset start_batch after first epoch
        start_batch = 0
        
        # Validate
        val_loss, val_acc = validate(
            model, val_loader, criterion, device, rank, world_size
        )
        dist.barrier()
        epoch_time = time.time() - epoch_start_time
        
        # Log and save (only rank 0)
        if rank == 0:
            logging.info(f"\\nEpoch {epoch}/{args.epochs} ({epoch_time:.1f}s)")
            logging.info(f"  Train loss: {train_loss:.4f} | Train acc: {train_acc:.3f}")
            logging.info(f"  Val loss:   {val_loss:.4f} | Val acc:   {val_acc:.3f}")
            
            # Save checkpoint
            is_best = val_loss < best_val_loss
            if is_best:
                best_val_loss = val_loss
            
            save_checkpoint(
                model, optimizer, scheduler, epoch, len(train_loader) - 1,
                args, train_loss, train_acc, val_loss, val_acc,
                best_val_loss, args.output_dir, is_best=is_best
            )
    
    if rank == 0:
        logging.info("\\n" + "="*80)
        logging.info("TRAINING COMPLETE!")
        logging.info("="*80)
        logging.info(f"Best validation loss: {best_val_loss:.4f}")
        logging.info(f"Model saved to: {Path(args.output_dir) / 'best_model.pt'}")
        logging.info("="*80)
    
    # Cleanup
    dist.destroy_process_group()


if __name__ == "__main__":
    main()