"""
Common utilities for all training approaches.
Includes label mapping, loss functions, metrics, and distributed setup.
"""

import os
import torch
import torch.nn.functional as F
import torch.distributed as dist
import psutil

# LABEL MAPPING 
# *************

LABEL_MAPPING = {
    # 87 real event tokens (indices 0-86)
    "NET_CXI_RAW_DATA":  0,  "FS_DISK_FULL":       1,  "INFO_NOISE":         2,
    "NET_CXI_TIMEOUT":   3,  "SVC_RSYSLOG_ERR":    4,  "NET_CXI_LINK":       5,
    "FS_DVS_WARN":       6,  "NET_CXI_WARN":       7,  "NET_TCP_FAIL":       8,
    "HW_PCIE_ERR":       9,  "HW_MCE_GENERIC":    10,  "NET_CXI_INT_ERR":   11,
    "HW_MCE_FATAL":     12,  "NET_CXI_HW_ECC":    13,  "APP_INFRA_FAIL":    14,
    "NET_CXI_SVC":      15,  "GPU_MEM_FAULT":     16,  "HW_MCE_CORRECTED":  17,
    "HW_EDAC_ERR":      18,  "FS_CLUSTER_EVICT":  19,  "FS_LUSTRE_SLOW":    20,
    "SVC_SYSTEMD_START":21,  "SVC_CONFIG_ERR":    22,  "GPU_SOFT_LOCK":     23,
    "HW_FABRIC_RTR":    24,  "NET_CONFIG_ERR":    25,  "HW_MEM_DIMM":       26,
    "SEC_AUTH_FAIL":    27,  "GPU_RAS_FAIL":      28,  "HW_IOMMU_ERR":      29,
    "FS_LUSTRE_OST_ERR":30,  "APP_FILE_MISSING":  31,  "SYS_KERNEL_CTX":    32,
    "FS_LUSTRE_ERR":    33,  "GPU_DRIVER_ERR":    34,  "FS_XFS_ERR":        35,
    "GPU_FIRMWARE":     36,  "HW_BMC_WARN":       37,  "APP_JOB_CANCEL":    38,
    "APP_CFG_ERR":      39,  "HW_ACPI_WARN":      40,  "APP_JOB_LATENCY":   41,
    "NET_CXI_FIRMWARE": 42,  "FS_IO_ERR":         43,  "NET_CXI_PHY_ERR":   44,
    "SVC_SYSTEMD_SPEC": 45,  "SYS_OOM_KILL":      46,  "APP_JOB_CGROUP":    47,
    "HW_IF_GPU_LINK":   48,  "FS_GPFS_ERR":       49,  "GPU_HARD_FAULT":    50,
    "HW_USB_FAIL":      51,  "HW_MCE_CPU":        52,  "SYS_WATCHDOG":      53,
    "NET_CXI_MGMT_ERR": 54,  "FS_LUSTRE_MDS_ERR": 55,  "SYS_CONFIG_ERR":    56,
    "SYS_RCU_STALL":    57,  "APP_JOB_ERR":       58,  "NET_RPC_ERR":       59,
    "NET_LNET_ERR":     60,  "GPU_TIMEOUT":       61,  "SYS_SEGFAULT":      62,
    "SVC_SYSTEMD_TIME": 63,  "HW_THERMAL_CRIT":   64,  "CTX_LUSTRE":        65,
    "HW_MCE_DUMP":      66,  "HW_MEM_CORRUPT":    67,  "STO_NVME_STALL":    68,
    "SVC_SYSTEMD_EXIT": 69,  "APP_GITLAB_FAIL":   70,  "SVC_SYSTEMD_KILL":  71,
    "SYS_KERNEL_PANIC": 72,  "CTX_AMDGPU":        73,  "SYS_COREDUMP":      74,
    "HW_CPU_CORE":      75,  "SYS_PROCESS_LIM":   76,  "SYS_X11_NOISE":     77,
    "SYS_CLOCK_SKEW":   78,  "CTX_SCHEDULER":     79,  "NET_LNET_WARN":     80,
    "HW_PCIE_HUB":      81,  "SVC_SYSTEMD_PAM":   82,  "CTX_MEMORY":        83,
    "CTX_SLINGSHOT":    84,  "HW_FABRIC_INT":     85,  "HW_MCE_UNK":        86,
    # Special tokens
    "<PAD>": 87, "<UNK>": 88, "<MASK>": 89,
}

IDX_TO_LABEL = {v: k for k, v in LABEL_MAPPING.items()}


# *************
# DISTRIBUTED SETUP
# *************

def log_affinity(rank, local_rank):
    """Log CPU core and GPU assignment for each rank"""
    core_affinity = psutil.Process().cpu_affinity()
    
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        bus_id = torch.cuda.get_device_properties(0).pci_bus_id
    else:
        gpu_name = "CPU Only"
        bus_id = "N/A"

    print(f"[Rank {rank} | Local {local_rank}] "
          f"GPU: {gpu_name} ({bus_id}) | "
          f"CPU Cores: {min(core_affinity)}-{max(core_affinity)}")


def setup_distributed():
    """Initialize distributed training for Frontier"""
    rank = int(os.environ.get('SLURM_PROCID', 0))
    world_size = int(os.environ.get('SLURM_NTASKS', 1))
    local_rank = int(os.environ.get('SLURM_LOCALID', 0))
    
    if torch.cuda.is_available():
        device = 0 
        torch.cuda.set_device(device)
        
        if rank == 0:
            print(f"World Size: {world_size}")
    else:
        device = 'cpu'
        if rank == 0:
            print("WARNING: No CUDA available!")
    
    if world_size > 1:
        hostnames = os.environ.get('SLURM_JOB_NODELIST')
        master_addr = os.popen(f'scontrol show hostname {hostnames} | head -n1').read().strip()
        
        os.environ['MASTER_ADDR'] = master_addr
        os.environ['MASTER_PORT'] = '29500'
        
        # FIX: Specify device_id to avoid warning
        dist.init_process_group(
            backend='nccl',
            init_method='env://',
            world_size=world_size,
            rank=rank,
            device_id=torch.device(f'cuda:{device}')
        )
    
    log_affinity(rank, local_rank)
    return rank, world_size, device


def cleanup_distributed():
    """Cleanup distributed training"""
    if dist.is_initialized():
        dist.destroy_process_group()


# *************
# LOSS FUNCTION
# *************

def compute_masked_loss(predictions, targets, ignore_indices=[87, 88, 89]):
    """
    Compute CrossEntropy loss while ignoring multiple special tokens.
    
    Args:
        predictions: (N, vocab_size) - Flattened predictions
        targets: (N,) - Flattened targets
        ignore_indices: List of token IDs to ignore (<PAD>, <UNK>, <MASK>)
        
    Returns:
        loss: Scalar tensor
    """
    mask = torch.ones_like(targets, dtype=torch.bool)
    for ignore_idx in ignore_indices:
        mask &= (targets != ignore_idx)
    
    # Handle case where everything is masked
    if mask.sum() == 0:
        # Return a small loss instead of 0 to avoid NaN in backward
        return torch.tensor(0.01, device=predictions.device, requires_grad=True)
    
    valid_predictions = predictions[mask]
    valid_targets = targets[mask]
    
    loss = F.cross_entropy(valid_predictions, valid_targets, reduction='mean')
    
    # Check for NaN
    if torch.isnan(loss):
        print(f"WARNING: NaN loss detected! Valid samples: {mask.sum().item()}")
        return torch.tensor(0.01, device=predictions.device, requires_grad=True)
    
    return loss


# EVALUATION METRICS
# *************

def compute_metrics(predictions, targets, ignore_indices=[87, 88, 89]):
    """
    Compute accuracy and top-5 accuracy.
    
    Args:
        predictions: (N, vocab_size) - Flattened predictions
        targets: (N,) - Flattened targets
        ignore_indices: Tokens to ignore
        
    Returns:
        dict with 'accuracy' and 'top5_accuracy'
    """
    mask = torch.ones_like(targets, dtype=torch.bool)
    for ignore_idx in ignore_indices:
        mask &= (targets != ignore_idx)
    
    if mask.sum() == 0:
        return {'accuracy': 0.0, 'top5_accuracy': 0.0}
    
    # Top-1 accuracy
    pred_classes = predictions.argmax(dim=-1)
    correct = (pred_classes[mask] == targets[mask]).sum().item()
    total = mask.sum().item()
    accuracy = correct / total
    
    # Top-5 accuracy
    top5_preds = predictions.topk(5, dim=-1)[1]
    top5_correct = (top5_preds == targets.unsqueeze(-1)).any(dim=-1)
    top5_acc = top5_correct[mask].float().mean().item()
    
    return {
        'accuracy': accuracy,
        'top5_accuracy': top5_acc
    }


# VOCABULARY BUILDER
# *********************

def build_vocabularies(df, rank):
    """Build node and component vocabularies from sample data"""
    unique_nodes = df['name'].dropna().unique()
    node_to_idx = {node: idx+1 for idx, node in enumerate(unique_nodes)}
    node_to_idx['<UNK>'] = 0
    
    unique_components = df['identifier'].dropna().astype(str).unique()
    component_to_idx = {comp: idx+1 for idx, comp in enumerate(unique_components)}
    component_to_idx['<UNK>'] = 0
    
    if rank == 0:
        print(f"Vocab Built - Nodes: {len(node_to_idx)}, Components: {len(component_to_idx)}")
    
    return node_to_idx, component_to_idx


