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

