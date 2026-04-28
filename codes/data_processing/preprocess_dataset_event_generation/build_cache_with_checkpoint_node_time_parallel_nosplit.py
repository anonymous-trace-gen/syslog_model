"""
Build cache using PySpark - NODE + TIMESTAMP SORTED VERSION.
Sorts data globally by [node (name), timestamp] and converts to NumPy.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf
from pyspark.sql.types import LongType
import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import pickle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, required=True)
    parser.add_argument('--cache_dir', type=str, required=True)
    parser.add_argument('--split', type=str, default='train')
    
    args = parser.parse_args()
    
    # LABEL_MAPPING
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
    
    print("="*80)
    print("PYSPARK CACHE BUILDER - NODE + TIMESTAMP SORTED VERSION")
    print("="*80)
    
    # Initialize Spark
    print("\nInitializing Spark...")
    spark = SparkSession.builder \
        .appName("HPC_Cache_Builder_NodeTimestamp") \
        .config("spark.executor.memory", "200g") \
        .config("spark.driver.memory", "50g") \
        .config("spark.sql.shuffle.partitions", "4096") \
        .config("spark.default.parallelism", "4096") \
        .getOrCreate()
    
    print("✓ Spark initialized")
    
    # Get file paths
    base_dir = Path(args.data_path)
    all_files = []
    
    print("\nScanning data directories...")
    for bdir in ['batch1', 'batch2', 'batch3', 'batch4']:
        path = base_dir / bdir
        if path.exists():
            files = sorted(list(path.glob('*.parquet')))
            all_files.extend([str(f) for f in files])
            print(f"  {bdir}: {len(files)} files")
    
    print(f"\n✓ Found {len(all_files)} total files")
    
    # Split for train/val/test
    num_files = len(all_files)
    if args.split == 'train':
        split_files = all_files[:int(num_files * 1)]
        print("ALL DATA")
    elif args.split == 'val':
        split_files = all_files[int(num_files * 0.8):int(num_files * 0.9)]
    else:
        split_files = all_files[int(num_files * 0.9):]
    
    print(f"✓ {args.split} split: {len(split_files)} files")
    
    # Read all parquet files — include 'name' (node) column
    print("\nReading parquet files in parallel...")
    df = spark.read.parquet(*split_files).select('timestamp', 'name', 'event_token')
    print("✓ Data loaded")
    
    # Get total count
    print("\nCounting events...")
    total_events = df.count()
    print(f"✓ Total events: {total_events:,}")

    # Log unique node count for visibility
    num_nodes = df.select('name').distinct().count()
    print(f"✓ Unique nodes: {num_nodes:,}")
    
    # CRITICAL: Global sort by node first, then timestamp within each node
    print("\nGlobal sorting by [name, timestamp] (this may take ~8-12 minutes)...")
    df_sorted = df.orderBy('name', 'timestamp')
    print("✓ Sorted")
    
    # Coalesce to fewer partitions (maintains sort!)
    print("\nCoalescing to 100 partitions (maintains sort order)...")
    df_sorted = df_sorted.coalesce(100)
    print("✓ Coalesced")
    
    # Tokenize event_token
    print("\nTokenizing events...")
    label_map_broadcast = spark.sparkContext.broadcast(LABEL_MAPPING)
    
    def tokenize(event_token):
        mapping = label_map_broadcast.value
        return mapping.get(event_token, mapping.get("<UNK>"))
    
    tokenize_udf = udf(tokenize, LongType())
    df_tokenized = df_sorted.withColumn('token_id', tokenize_udf(col('event_token')))
    print("✓ Tokenized")
    
    # Write sorted output — include 'name' so we can verify and save it
    cache_dir = Path(args.cache_dir)
    temp_output = cache_dir / 'spark_node_ts_sorted_output'
    
    print(f"\nWriting sorted data to: {temp_output}")
    df_tokenized.select('name', 'timestamp', 'token_id') \
        .write \
        .mode('overwrite') \
        .parquet(str(temp_output))
    print("✓ Written")
    
    spark.stop()
    
    # Verify sort before proceeding
    print("\n" + "="*80)
    print("VERIFYING SORT ORDER")
    print("="*80)
    
    chunk_files = sorted(list(temp_output.glob('*.parquet')))
    print(f"\nFound {len(chunk_files)} partition files")
    
    # Check first and last chunks
    first_chunk = pd.read_parquet(chunk_files[0])
    last_chunk = pd.read_parquet(chunk_files[-1])
    
    first_node = first_chunk['name'].iloc[0]
    last_node = last_chunk['name'].iloc[-1]
    first_ts = pd.to_datetime(first_chunk['timestamp']).min()
    last_ts = pd.to_datetime(last_chunk['timestamp']).max()
    
    print(f"\nFirst chunk — node: {first_node}, earliest ts: {first_ts}")
    print(f"Last chunk  — node: {last_node}, latest ts:   {last_ts}")
    
    duration = (last_ts - first_ts) / pd.Timedelta(hours=1)
    print(f"Duration: {duration:.1f} hours")
    
    if first_node > last_node:
        print("\n❌ ERROR: Node ordering looks reversed (alphabetically)!")
        print("Aborting - something went wrong with Spark sort!")
        import sys
        sys.exit(1)
    else:
        print("\n✅ Data is correctly sorted (node A→Z, then oldest→newest per node)!")
    
    # Convert to NumPy
    print("\n" + "="*80)
    print("CONVERTING TO NUMPY (BATCHED)")
    print("="*80)
    
    # Output filenames reflect the new sort order
    token_file     = cache_dir / f'{args.split}_node_ts_sorted_tokens.npy'
    timestamp_file = cache_dir / f'{args.split}_node_ts_sorted_timestamps.npy'
    node_file      = cache_dir / f'{args.split}_node_ts_sorted_nodes.npy'   # encoded node names
    node_map_file  = cache_dir / f'{args.split}_node_name_map.pkl'          # int -> node string
    
    # Build a node-name → integer mapping (deterministic: sorted alphabetically)
    print("\nBuilding node integer mapping...")
    all_nodes_df = pd.read_parquet(chunk_files[0], columns=['name'])
    # Collect a sample to bootstrap; full mapping built during conversion below
    # We'll finalize after reading all chunks — see note in conversion loop.

    # Create memory-mapped files
    print(f"\nCreating memory-mapped NumPy files...")
    print(f"  Events: {total_events:,}")
    print(f"  Tokens size:     {total_events * 8 / 1024**3:.2f} GB")
    print(f"  Timestamps size: {total_events * 8 / 1024**3:.2f} GB")
    print(f"  Nodes size:      {total_events * 4 / 1024**3:.2f} GB  (int32)")
    
    tokens_mmap = np.lib.format.open_memmap(
        token_file,
        mode='w+',
        dtype=np.int64,
        shape=(total_events,)
    )
    
    timestamps_mmap = np.lib.format.open_memmap(
        timestamp_file,
        mode='w+',
        dtype='datetime64[ns]',
        shape=(total_events,)
    )

    nodes_mmap = np.lib.format.open_memmap(
        node_file,
        mode='w+',
        dtype=np.int32,
        shape=(total_events,)
    )
    
    print("✓ Memory-mapped files created")
    
    # Fill arrays in batches
    print("\nFilling arrays from Spark output (batched for speed)...")
    
    from tqdm import tqdm
    
    # First pass: collect all unique node names to build a stable int mapping
    print("\nPass 1: collecting unique node names for mapping...")
    unique_nodes = set()
    for f in tqdm(chunk_files, desc="Scanning nodes"):
        chunk = pd.read_parquet(f, columns=['name'])
        unique_nodes.update(chunk['name'].dropna().unique().tolist())
    
    node_list = sorted(unique_nodes)           # alphabetical → deterministic
    node_to_int = {n: i for i, n in enumerate(node_list)}
    print(f"✓ Found {len(node_list)} unique nodes")
    
    # Save mapping so downstream code can decode int → node name
    with open(node_map_file, 'wb') as f:
        pickle.dump({'node_to_int': node_to_int, 'int_to_node': node_list}, f)
    print(f"✓ Node map saved → {node_map_file}")
    
    # Second pass: write data to mmap arrays
    print("\nPass 2: writing data to memory-mapped arrays...")
    offset = 0
    BATCH_SIZE = 10  # Process 10 files at a time
    num_batches = (len(chunk_files) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_idx in tqdm(range(num_batches), desc="Converting"):
        batch_start = batch_idx * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(chunk_files))
        batch_files = chunk_files[batch_start:batch_end]
        
        # Read batch
        batch_dfs = [pd.read_parquet(f) for f in batch_files]
        batch_combined = pd.concat(batch_dfs, ignore_index=True)
        del batch_dfs
        
        # Extract arrays
        timestamps_chunk = pd.to_datetime(batch_combined['timestamp']).values
        tokens_chunk     = batch_combined['token_id'].values.astype(np.int64)
        nodes_chunk      = batch_combined['name'].map(node_to_int).values.astype(np.int32)
        del batch_combined
        
        chunk_len = len(tokens_chunk)
        
        # Write to memory-mapped files
        tokens_mmap[offset:offset+chunk_len]     = tokens_chunk
        timestamps_mmap[offset:offset+chunk_len] = timestamps_chunk
        nodes_mmap[offset:offset+chunk_len]      = nodes_chunk
        
        offset += chunk_len
        
        # Flush periodically
        if batch_idx % 5 == 0:
            tokens_mmap.flush()
            timestamps_mmap.flush()
            nodes_mmap.flush()
    
    # Final flush
    tokens_mmap.flush()
    timestamps_mmap.flush()
    nodes_mmap.flush()
    
    print(f"\n✓ Converted {offset:,} events")
    
    # Save metadata
    print("\nSaving metadata...")
    
    metadata_file = cache_dir / f'{args.split}_node_ts_metadata.pkl'
    done_flag     = cache_dir / f'{args.split}_node_ts_done.flag'
    
    with open(metadata_file, 'wb') as f:
        pickle.dump({
            'num_events':     offset,
            'time_start':     str(first_ts),
            'time_end':       str(last_ts),
            'duration_hours': float(duration),
            'num_nodes':      len(node_list),
            'sort_order':     'node_then_timestamp',
        }, f)
    print(f"  ✓ {metadata_file}")
    
    done_flag.touch()
    print(f"  ✓ {done_flag}")
    
    # Cleanup
    print("\nCleaning up temporary files...")
    import shutil
    shutil.rmtree(temp_output)
    print("  ✓ Removed spark_node_ts_sorted_output/")
    
    print("\n" + "="*80)
    print("BUILD COMPLETE!")
    print("="*80)
    print(f"Split:      {args.split}")
    print(f"Events:     {offset:,}")
    print(f"Nodes:      {len(node_list)}")
    print(f"Time range: {first_ts} to {last_ts}")
    print(f"Duration:   {duration:.1f} hours ({duration/24:.1f} days)")
    print(f"\nFiles created:")
    print(f"  {token_file}     ({token_file.stat().st_size / 1024**3:.2f} GB)")
    print(f"  {timestamp_file} ({timestamp_file.stat().st_size / 1024**3:.2f} GB)")
    print(f"  {node_file}      ({node_file.stat().st_size / 1024**3:.2f} GB)")
    print(f"  {node_map_file}  (node name ↔ int mapping)")
    print("="*80)


if __name__ == "__main__":
    main()