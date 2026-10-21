# Original project inspection

Original files were read only. The preparation, local validation environment and archive were written exclusively inside the new development folder. Runtime files use package-relative paths and do not import original scripts.

`data/source_inventory.json` lists the 70 main cache files found directly beneath sample folders in `python_data/` and `python_data_harmonized/`, with compressed sizes, spatial shapes and every NPZ member's actual shape/dtype. TIC companions and native layer caches are ancillary files; processed ion-window NPZ files are analysis products, not full source spectra. The project notes identify the harmonized collection as the preferred converted acquisition source, so it was used here. Larger harmonized negative-ion caches reach approximately 826 MB compressed. No raw acquisition files, per-layer caches or processed image trees are copied.

Inspected notes included `python_file_summary.txt`, `conversion_handoff_notes.txt`, and the sparse-loading/calibration/extraction code. The layer handoff explains coordinate-aligned sums across native layers and the significance of explicit pixel coordinates. The selected sample's conversion manifest says two acquisition layers were assigned, with native layer 0000 accepted as already combined; that original statement is retained, not reinterpreted as two separately inspected layers.

## Main existing functionality

| Original module | Relevant functionality |
|---|---|
| `batch_convert_raw_to_python.py` | Preferred harmonized converter; acquisition/layer naming and coordinate-aligned combining |
| `tofsims_to_python.py` | General conversion, QMS extraction and coordinate-aware TIC outputs |
| `tofsims_common.py` | `load_sparse_dataset`, `load_peaks`, `load_mask`, `tic_vector`, `tic_image_from_vector`, `fit_calibration_model`, `save_summed_spectrum_outputs`, `extraction_bin_mask`, `extract_peak_image` |
| `tofsims_calibrate.py` | Calibration workflow and saved coefficients/QC |
| `tofsims_directed_windowing.py` | Directed ion-window extraction using reference peaks and calibration |
| `tofsims_roi_extraction.py` | ROI names, atlas/SVG rasterization and spatial transforms |
| `tofsims_rois_spectra.py` | ROI spectra workflow |
| `tofsims_binning_information_loss.py` | Count-summed ion/TIC spatial bins and fractional ROI-mask information-loss analysis |
| `image_registration_gui.py`, `mask_editor.py`, `frag_window_viewer.py` | Existing local registration, masking and inspection interfaces |

The cloud implementation follows the inspected coordinate/CSR conventions without importing modules whose top-level configuration or output helpers target local project trees.

## Selected source schema

Sample: `FD_13CFeed_WT_D7_R1_NEG_11pA`, harmonized acquisition cache.

| Member | Shape | dtype | Meaning |
|---|---|---|---|
| `indptr` | 59,393 | uint64 | CSR row pointers |
| `indices` | 5,490,535 | uint32 | QMS channel indices |
| `values` | 5,490,535 | uint32 | Positive integer ion counts, observed range 1–4,723 |
| `n_pixels` | 1 | uint32 | 59,392 stored acquisition rows |
| `n_bins` | 1 | uint32 | 362,573 spectral channels |
| `max_value` | 1 | uint32 | 4,723 |
| `shape` | 2 | uint32 | Image shape (y, x): 320 × 256 |
| `tile_grid` | 3 | uint32 | 10 tile rows, 8 tile columns, 32-pixel tile size |
| `pixel_x`, `pixel_y` | 59,392 each | uint32 | Explicit spatial coordinates; row order must not be reshaped blindly |

The companion QMS NPY is a strictly increasing float32 vector of 362,573 values spanning 60.5–3000.4946 m/z. Its NPY file is 1,450,420 bytes. The original CSR matrix is 59,392 × 362,573 and the spatial grid is 320 × 256. Acquisition coverage is incomplete: 22,528 grid positions have no stored acquisition row. Reduced coverage is explicitly retained; unacquired areas are not treated as measured zeros.

The 256-cap output matrix is 52,480 × 362,573 (spatial grid 256 × 205). The 512-cap output matrix is 81,920 × 362,573 (native 320 × 256 grid), including empty rows for missing positions. These matrix row counts differ from the number of acquired source pixels by design.

## Calibration, candidates and masks

The selected sample's saved calibration manifest names only `whole_cal`. Coefficients are `[5.313866366367009e-08, 0.9993460508574556, 0.3274107377166426]`, evaluated using the original `np.polyval` convention. They are not instrumental time-of-flight coefficients inferred from QMS; they are the existing post-acquisition polynomial correction. No earlier instrumental calibration coefficients were present in the inspected cache/manifest. QMS values are therefore preserved directly.

Existing calibration QC says fit_success=true, quality_pass=false, use_for_analysis=true; mean absolute residual 277.5374621806707 ppm exceeds 45 ppm. The package preserves these original flags and exposes a warning, with acquisition masses as default. The matches CSV and summary JSON are copied into data/ for review. It does not refit or silently approve the correction.

All 130 rows of `neg_known_peaks.tsv`, including molecular formula, adduct/ion, exact mass, extraction bounds and confidence/rationale columns, are embedded as reference candidates. No assignment is fabricated or promoted to a stronger confidence level.

The sample-matched `automask/masks/<sample>_mask.npy` has the source spatial shape and is retained verbatim, together with binned tissue-area fractions. The calibration manifest reports mask_present=false, so the package does not claim that this later-discovered mask was used in the saved calibration. No anatomical ROI masks were found under this selected processed sample. `rois.txt` contains names only. Physical pixel pitch was unavailable in the inspected metadata; spatial axes remain source pixel coordinates.

Source SHA-256 hashes, array descriptors, conversion metadata, tile transform, layer information and reduction choices are retained in `data/dataset_info.json` and embedded metadata. Machine-specific source path strings in the acquisition manifest are reduced to filenames; source hashes and relative inventory locations provide traceability without requiring local drives.
