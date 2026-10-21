# ToF-SIMS cloud development

A portable NiceGUI workspace for developing a ToF-SIMS GUI in a private GitHub Codespace. It uses real sparse mouse-brain counts and preserves the complete acquisition mass axis. A future Windows interface can reuse `core/` independently of NiceGUI.

## Start

Python 3.12 is the tested interpreter. From this directory:

```bash
python -m pip install -r requirements-dev.txt
python main.py
```

Open forwarded port **8080** in Codespaces, or http://localhost:8080 locally. The app binds to `0.0.0.0:8080`. Keep the forwarded port **Private**. Stop with Ctrl+C and restart after Python edits; automatic reload is disabled.

The devcontainer installs dependencies automatically. Start with 2 CPU / 4 GB. Local Windows startup and browser checks are recorded in `VALIDATION.md`; an actual Codespaces/Linux session and physical Android tablet still need testing. For runtime alone use `requirements.txt`; `requirements-dev.txt` adds pytest. Direct dependencies are pinned. `data/tested_environment.txt` records transitive versions for diagnosis, not a cross-platform lock file.

## Included data

Source: `FD_13CFeed_WT_D7_R1_NEG_11pA` from the harmonized acquisition caches. This sample retains a full negative-ion mass axis at a practical size. It does not represent every sample's signal density, layers or calibration quality.

| Dataset | Spatial shape (y, x) | Mass channels | Compressed bytes |
|---|---:|---:|---:|
| Original cache | 320 × 256 | 362,573 | 17,276,740 |
| `data/tofsims_demo_256.npz` | 256 × 205 | 362,573 | 19,242,525 |
| `data/tofsims_demo_512.npz` | 320 × 256 | 362,573 | 19,975,230 |

Original QMS float32 values are embedded unchanged. There is **no analytical mass reduction, interpolation or rounding**. The 512 name means a maximum spatial dimension of 512, so this smaller source stays at native resolution. The 256 cap preserves the field of view and aspect ratio to integer-pixel precision. Variable 1–2 pixel bin widths are explicit in `x_edges`/`y_edges`; plots use these edges, keeping the source extent exactly 256:320. Physical pixel size was unavailable in the inspected cache/manifest; micrometers are not inferred.

Counts are summed with uint64 accumulation. Both demos conserve **589,699,253 counts**, every source mass-channel sum and every independently accumulated spatial TIC bin. The source contains 59,392 acquired pixels in an 81,920-position grid. `coverage` distinguishes unacquired pixels from measured zero signal. Output CSR includes empty rows for the full grid; no dense pixel-by-mass cube is constructed.

The demos are slightly larger than the original compressed cache because they include the QMS axis, wider counts, original summed spectrum, candidate assignments, tissue mask and provenance. Both stay below the browser's 25 MiB upload limit; see [GitHub file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

**Calibration warning:** the saved whole-image polynomial is retained verbatim, but its existing QC failed: mean absolute residual **277.54 ppm**, threshold **45 ppm**. Acquisition QMS masses are the default. The opt-in saved correction evaluates that polynomial at original masses without resampling counts. This is an exploratory development dataset, not a validated calibrated result. Reference-ion candidates retain their original confidence/rationale fields and are not newly identified ions.

The associated automask is retained in original coordinates as `source_tissue_mask`, with `tissue_fraction` for reduced bins. Its existing sample-matched frame is retained without re-registration. No anatomical ROI masks were found in the selected processed sample folder; names in `rois.txt` alone do not define spatial masks.

## Structure

```text
main.py                         server entry point
requirements*.txt               pinned direct dependencies
.devcontainer/devcontainer.json Python Codespaces environment
core/data_loader.py             validated CSR backend and bounded image cache
core/data_processing.py         ROI sums, scaling and display pyramid
core/binning.py                 count-preserving sparse aggregation
gui/layout.py                   client-specific controls and background callbacks
gui/components.py               reusable Plotly figure builders
scripts/generate_demo_data.py   original CSR + QMS converter
scripts/rebin_packaged_demo.py  regenerate using included native-resolution demo
scripts/validate_demo_data.py   provenance and conservation checks
tests/                          backend and scientific tests
data/                           demos, inventory, provenance and validation reports
README.md / SETUP_ANDROID.md / VALIDATION.md / ARCHITECTURE.md
```

Local preparation used `work/` for tools and an isolated validation environment; these temporary files are excluded from delivery and unnecessary at runtime.

## GUI workflows

- **Data Import:** select a converted NPZ beneath `data/`; inspect dimensions and acquisition/reduction/calibration metadata. Reload the browser to discover new files.
- **Ion Maps:** choose TIC, a reference candidate or custom inclusive mass window; choose scaling, colormap, upper display percentile and detail; press **Update ion map**. Unacquired pixels are transparent. Display changes never change analytical counts.
- **Mass Spectra:** interactive Plotly zoom/pan and numerical mass bounds. Set a narrow mass range and press **Update spectrum** for more detail. At most 6,000 peak-preserving points are plotted at original mass positions. Zoom alone does not request new detail. The calibration toggle on Ion Maps also controls updated spectra and exports.
- **ROI Analysis:** enter a rectangle in reduced-grid indices, with exclusive end bounds; press **Analyze ROI** for a TIC overlay, counts and spectrum. Whole reduced bins are selected; native sub-bin boundaries cannot be recovered.
- **Batch Processing:** marked placeholder; generation and validation scripts run in the terminal.
- **Export:** full-channel summed/ROI spectrum CSV, unscaled selected-ion image CSV, ion-window/spatial provenance and dataset metadata JSON. Plotly's toolbar can save PNG plots.

Controls wrap on narrow screens, and ROI input does not require a mouse. See `SETUP_ANDROID.md`.

## Another dataset

The importer accepts the documented sparse count schema. It does not infer arbitrary cube layouts or normalized intensities and uses `allow_pickle=False`. Add a converted file under `data/`, refresh, and select it in Data Import. Use trusted NPZ files. The compressed-size cap of 100 MiB is not a decompressed-memory guarantee.

To convert another original project cache with its companion QMS and optional sidecars:

```bash
python scripts/generate_demo_data.py source/sample.npz --qms source/sample_qms.npy --manifest source/conversion_manifest.json --peaks source/known_peaks.tsv --coefficients source/whole_coefficients.npy --calibration-summary source/whole_calibration_summary.json --mask source/sample_mask.npy --targets 256 512
```

Replace source paths as appropriate. QMS defaults to `<cache_stem>_qms.npy`; other sidecars are optional. Omit both calibration arguments when coefficients are unavailable. Outputs are restricted to this development package. Existing demos require explicit `--overwrite`; never direct output toward originals. The converter validates coordinates/CSR and refuses float or normalized intensities instead of guessing an aggregation rule.

For a source too large after spatial reduction, choose an explicitly described representative acquisition or implement a named mass-window subset adapter. This package silently removes no channels and does not provide mass-axis coarsening.

## Regenerate while travelling

The included 512-cap demo retains native spatial resolution. Rebuild the 256 demo without the original project:

```bash
python scripts/rebin_packaged_demo.py --target 256 --overwrite
python scripts/validate_demo_data.py
```

This leaves the native 512 demo intact and updates `dataset_info.json` and its SHA-256 entry. Provenance changes can change compressed bytes/hash; counts and original mass values remain identical. Other caps, such as `--target 128`, create their own filenames. Caps above 320 preserve the native size.

## Validate

```bash
python -m pytest -q
python scripts/validate_demo_data.py
```

For an independent comparison against the original cache/QMS when available:

```bash
python scripts/validate_demo_data.py --source source/sample.npz --qms source/sample_qms.npy --report data/validation_report.json
```

Checks cover exact original QMS equality, coefficients, every channel sum, total counts, each spatial TIC bin, coverage, edge extent, tissue fractions and saved hashes. The generator checks conservation during creation. `VALIDATION.md` states what was actually run.

## Limitations

NPZ members are eagerly decompressed, with no genuine NPZ memory mapping. The backend interface prepares for HDF5/Zarr, with cached images, a simple summed display pyramid, sparse ROI extraction and worker-thread callbacks. A complete large-data engine, calibration fitting, tile-dependent correction, polygon/atlas ROIs, batch queues, cancellation and Windows packaging remain future work. See `ARCHITECTURE.md`.

Original analysis/conversion modules are not imported at runtime, avoiding their local paths and filesystem side effects. Originals were read without modification.
