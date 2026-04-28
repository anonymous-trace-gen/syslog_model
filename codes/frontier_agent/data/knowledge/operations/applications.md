# Applications

Workloads, science domains, and program allocations running on the OLCF Frontier supercomputer.

## Science Domains

Frontier supports scientific research across multiple domains:

- **Earth System and Climate**: Climate modeling, subsurface carbon capture simulations, global atmospheric simulation at 1-km grid spacing, weather forecasting collaboration with ECMWF
- **Energy Security**: Power grid planning, wind turbine optimization (ExaWind), small modular reactor design, turbine blade energy loss analysis (GE Aviation)
- **Health Care and Biomedical**: Cancer research (NIH), AI for precision drug therapy, SARS-CoV-2 variant analysis, biomedical knowledge graph analytics (SPOKE database)
- **Scientific Discovery**: Cosmological probes, materials discovery, protein structure analysis, fusion plasma control, quantum chemistry
- **Economic Security**: Additive manufacturing, biofuel catalyst design, seismic hazard assessment

## CAAR Applications

The Center for Accelerated Application Readiness (CAAR) program prepared scientific applications for Frontier through collaboration between OLCF, HPE, and AMD, achieving 4-7.5x speedups over Summit.

### Application Portfolio

| Application | Domain | Language | Programming Model | Computational Motif |
|-------------|--------|----------|-------------------|---------------------|
| **Cholla** | Astrophysics | C++ | MPI+HIP | Finite volume hydrodynamics |
| **NAMD** | Molecular dynamics | C++ | CHARM++/HIP | Molecular dynamics |
| **LSMS** | Materials science | F90/C++ | MPI+HIP | Dense linear solvers, Monte Carlo |
| **CoMet** | Genomics/Climate | C++ | MPI+HIP | Correlation analysis (GEMM-dominated) |
| **GESTS** | Turbulence | F95 | MPI+OpenMP 4.5 | Fourier pseudo-spectral (3D FFT) |
| **NuCCOR** | Nuclear physics | F90+F2008/C | MPI+OpenMP/HIP | Quantum chemistry (coupled-cluster) |
| **PIConGPU** | Plasma physics | C++ | Alpaka | Particle-in-cell methods |
| **LBPM** | Porous media | C++ | MPI+HIP | Lattice Boltzmann methods |
| **GAMESS** | Quantum chemistry | Fortran/C++ | MPI+HIP | Dense linear algebra (BLAS/LAPACK) |

### Measured Speedups (Frontier vs Summit)

| Application | Speedup Factor | Notes |
|-------------|----------------|-------|
| GAMESS | 5x | Fragment-level HIP RI-MP2 code |
| LSMS | 7.5x | Per-GPU performance for FePt systems |
| GESTS | 5x | FOM improvement on 4096 nodes |
| ExaSky (HACC) | 4.2x | Weak scaling benchmark at 8,192 nodes |
| CoMet | 5.2x | Achieved 6.71 exaflops mixed precision |
| NuCCOR | 6.1x | Coupled-cluster calculations |
| Pele | 4.2x | Combustion simulations |
| COAST | 7.4x | Knowledge graph analytics |

## ECP Applications

The Exascale Computing Project (ECP) contributed applications through Application Development (AD) and Software Technology (ST) portfolios.

**E3SM-MMF** (Energy Exascale Earth System Model): Throughput target 1,000-2,000x realtime. Highly sensitive to latency. Uses Kokkos and YAKL. Weak scaling efficiency >80% from 1 to 4096 nodes.

**ExaSky (HACC)**: Particle-based cosmology framework. Hybrid MPI-OpenMP. Achieved 230x FOM vs original Theta baseline.

**Pele** (Combustion): Reactive flow with adaptive mesh refinement on AMReX. 75x speedup over project lifetime. Weak scaling efficiency >80% on 4096 nodes.

**LAMMPS/ReaxFF**: Classical molecular dynamics with Kokkos backend targeting HIP. Required extensive compiler debugging for register spills.

## Allocation Programs

OLCF provides compute time through three primary programs:

### INCITE (Innovative and Novel Computational Impact on Theory and Experiment)

Large-scale, computationally intensive research. Largest allocations available (millions to hundreds of millions of node-hours). Peer-reviewed proposals, annual call (typically spring), 1-3 year awards.

### ALCC (ASCR Leadership Computing Challenge)

High-risk, high-payoff simulations in DOE mission areas. Annual cycle, medium to large allocations. Focus areas: energy science, climate, materials, nuclear physics, fusion energy.

### Director's Discretionary (DD)

Small allocations for startup projects, code development, and benchmarking. Flexible application, rapid turnaround. Used for porting, scaling studies, and preparing INCITE/ALCC proposals.

## Workload Characteristics

### Compute-Bound Workloads

High arithmetic intensity (FLOPS per byte), limited by peak GPU compute throughput. Benefits from mixed-precision arithmetic. Examples: CoMet (GEMM-dominated), COAST (Floyd-Warshall), dense linear algebra (GAMESS, LSMS). CoMet achieved 6.71 exaflops using mixed FP16/FP32 on 9,074 nodes.

### Memory-Bound Workloads

Low arithmetic intensity, performance scales with HBM bandwidth (3.2 TB/s per node). Examples: sparse matrix-vector multiplication (LAMMPS), stencil operations, data-intensive analytics.

### Communication-Bound Workloads

Strong scaling limited by Amdahl's law, sensitive to network latency/bandwidth. Benefits from GPU-aware MPI and asynchronous communication. Examples: GESTS (global FFT transposes), E3SM-MMF (kernel launch latency), distributed graph algorithms.

### Mixed-Precision Workloads

Uses FP16, INT8, or other reduced precision types for higher effective FLOPS. Examples: CoMet (binary data encoding, mixed FP16/FP32), deep learning inference, genomics analysis.

## Power Profiles by Application Type

| Workload | Power Characteristic | Notes |
|----------|---------------------|-------|
| HPL (Linpack) | ~15-16 MW swing | 2h 38min duration, PUE 1.06 |
| DGEMM | ~18 MW swing | Sustained dense compute load |
| Pennant | Intermittent spikes | Sharp, irregular load pattern |
| Idle | ~8 MW baseline | Minimal GPU activity |

Power swing range up to 18 MW. CPU-GPU alternation creates "warble" effect (beat frequency) affecting power quality. LinPack power draw: 294-300 kW per node.

## Gordon Bell Prize Applications

### 2022 Gordon Bell Finalists

**COAST (Knowledge Graph Analytics)**: Achieved 1.004 exaflops on biomedical knowledge graph analysis using Floyd-Warshall all-pairs shortest path on SPOKE database (50+ million vertices). 7x performance increase from Summit.

**WarpX (Laser-Plasma Acceleration)**: Mesh-refined particle-in-cell simulations at groundbreaking resolution for laser-based electron accelerators.

### Notable Science Achievements

- **CoMet**: 6.6 exaflops mixed precision (3-way DUO method), SARS-CoV-2 variant analysis, near-perfect weak scaling to full system
- **Weather Forecasting (ECMWF+ORNL)**: Global atmospheric simulation at 1-km resolution, full 4-month season simulation
- **GE Aviation**: High-pressure turbine blade energy loss analysis, eddies down to tens of microns, 1% fuel efficiency = $1B/year savings

## Programming Models and Portability

| Approach | Description | Performance Level |
|----------|-------------|-------------------|
| HIP | AMD's portability layer (CUDA-like) | Highest performance |
| OpenMP Offload | Directive-based GPU acceleration | Good, simplified maintenance |
| Kokkos/RAJA | C++ portability abstractions | Good, multi-vendor portable |
| YAKL | Fortran-friendly C++ launcher | Good for climate codes |

**CUDA to HIP**: hipify tool converts bulk of code automatically, 99.8% normalized performance vs CUDA on SHOC benchmarks.

**Common Optimizations**: Kernel fusion/fission, asynchronous launches, vendor-optimized libraries (rocBLAS, rocSOLVER), pool allocators for device memory.

## Application Readiness Process

The Frontier Center of Excellence (COE) pooled expertise from HPE, AMD, and ORNL. Activities included hackathons, dedicated liaisons for CAAR/ECP projects, and training workshops.

### Early Access Systems Timeline

| System | GPUs | Timeline | Purpose |
|--------|------|----------|---------|
| Poplar/Tulip | MI60 | 2019 | Initial porting, HIP evaluation |
| Spock/Birch | MI100 | 2020 | Scaling studies, interconnect testing |
| Crusher | MI250X | Jan 2022 | Final tuning, production readiness |

Readiness tracked via challenge problems and Figures of Merit (FOM) against Summit baselines, with mid-project and final reviews by the COE Management Council.

## Related Notes

- [[hub]] - Frontier Supercomputer main hub
- [[overview/overview]] - System specifications and architecture
- [[operations/job-scheduling]] - Slurm configuration and allocation policies
- [[operations/compute]] - CPU/GPU architecture and operational details
- [[operations/power]] - Power profiles by workload type
