# Backend and large-data development

`DatasetBackend` separates ion-image and ROI-spectrum operations from the GUI. `SparseDataset` implements the small-demo format with CSR rows indexed by explicit pixel coordinates and columns indexed by QMS channels. It never constructs a dense hyperspectral cube. Integer reductions conserve counts; uint64 avoids overflowing the original uint32 counter width during aggregation.

Compressed NPZ is a transport format, not a lazy engine. Each requested member is decompressed at load. Pages load through `run.io_bound`, and the process caches one backend by path to avoid repeated loads. Existing browser clients can retain older backend references when another file is opened. This is a single-user development workspace, not a bounded-memory multi-user service. Controls belong to each browser client; datasets are read-only. Restart after replacing a same-path file to invalidate its cache.

The backend caches up to eight ion images and one summed spectrum. Window extraction uses CSR column slices, allowing temporary sparse arrays but no dense cube. ROI extraction selects stored pixel rows and sums whole reduced bins. A summed display pyramid reduces rendered pixels independently of analysis. Explicit spatial edges preserve source extent and variable widths. Display images use floats for NaNs; analytical spectra use integers. Image CSV counts remain exact for this sample, well below float64's exact-integer limit.

Mass plots send at most 6,000 points: each display group contributes its highest count at an original mass position. This changes the visible envelope and connecting lines. It is not integrated analytical mass rebinning. Narrowing the requested mass range restores channel detail. Exports always use full mass positions/counts.

Loading, ion windows, ROI sums and CSV generation use worker threads. A per-client lock serializes expensive callbacks. Initial figure serialization and small transforms still run on the event loop. Cancellation, progress, durable jobs, quotas and out-of-process heavy computation are future work.

A future Zarr/HDF5 backend should implement the same operations and read required chunks while storing m/z, coordinates and coverage separately. Benchmark chunk geometry for ion windows versus ROI spectra. A memory-mapped CSR option could split indptr/indices/values/QMS into uncompressed NPY files with `mmap_mode='r'`. NPZ mmap_mode does not achieve this. Neither backend is implemented here.

Tile-dependent calibration must precede spatial sums crossing calibration domains, or retain separate tile spectra. This sample has one saved whole-image correction, preserved with its failed QC and an unchanged raw QMS axis. No general remapping/interpolation is attempted. Tissue fractions preserve geometry, but multiplying binned spectra by ROI fractions cannot exactly recover heterogeneous sub-bin signals. The GUI therefore uses whole-bin rectangles.

The direct runtime dependencies are NumPy, SciPy, Plotly and NiceGUI. No original pipeline modules are imported, avoiding their paths and filesystem side effects. A future Windows frontend can reuse the core, but desktop packaging remains unimplemented.
