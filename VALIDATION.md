# Validation performed

Prepared on 2026-10-21. Originals were read only. All preparation and validation writes were confined to this development folder.

## Scientific and backend checks

- 17 pytest tests passed, including permuted explicit coordinates, non-divisible edges, smaller-than-target sources, uint32 overflow avoidance through uint64 sums, rejection of normalized float input, missing coverage, cached ion windows, raw/corrected mass bounds, ROI counts, full-channel sums, display scaling/pyramid conservation and Plotly figure serialization.
- Both final packaged NPZ files loaded successfully with `allow_pickle=False` and passed CSR validation.
- Source comparison verified unchanged original QMS values and dtype, unchanged saved calibration coefficients and QC summary, every mass-channel sum, total counts and every independently accumulated spatial TIC bin.
- Both variants retain 362,573 mass channels and exactly 589,699,253 total counts. Source acquired-pixel coverage is 59,392; missing regions stay explicitly marked.
- Source spatial grid 320 × 256 became 256 × 205 for the 256 cap and stayed 320 × 256 for the 512 cap. Integer partitions include all edge pixels. Mass channels were not reduced or interpolated.
- Preserved mask fractions agree with aggregation of the retained source mask. Generation retained the original sample-matched mask array and candidate reference rows.
- Demo SHA-256 hashes agree with `data/dataset_info.json`; original cache hash agrees with the generation record, confirming the selected source was unchanged.
- `scripts/rebin_packaged_demo.py --target 128` was executed successfully and its result passed standalone validation. That temporary variant was excluded from delivery.
- `pip check` reported no broken requirements. Tested Python was 3.12; resolved dependencies are recorded in `data/tested_environment.txt`.
- The ZIP passed its internal CRC check. It was extracted to a separate temporary directory inside the allowed development folder; all 17 tests and standalone dataset validation passed there, and its `main.py` was launched successfully. The extracted GUI loaded both demos and confirmed that the active-dataset selector follows the loaded file.

Machine-readable final comparison results are in `data/validation_report.json`; source/member inventory is in `data/source_inventory.json`.

## Local application and browser checks

The app was launched with `python main.py` and reported ready on port 8080. The local in-app browser loaded the GUI with no startup exception. The following were exercised:

- Automatic 256-demo loading and the initial TIC plot.
- Reference-ion selection (PO3) and Update ion map; confidence fields and the calibration QC warning remained visible.
- Mass-spectrum range update to 78.8–79.2 m/z, producing detailed original-position spectral data.
- Rectangle ROI analysis with bounds `[0, 40, 0, 50]`, returning 2,131,616 counts, 1,984 acquired source pixels and 1,300 covered bins out of 2,000 bins.
- Switching to the 512-cap demo and rendering its native-resolution TIC.
- Narrow-viewport control wrapping and horizontal navigation through the local browser.

Figure axes were adjusted after initial visual inspection to retain source geometry without enlarged automatic coordinate ranges, and the initial intensity scale was aligned with its control. The active-dataset selector was also corrected to follow the loaded file. Automated scientific/figure checks were rerun after edits.

Browser file downloads were not exercised because the preparation task restricts writes to this development folder. Export implementations are included; inspect downloaded CSV/PNG results during the actual tablet smoke test. No files were uploaded or pushed to GitHub.

## Limits of this validation

The devcontainer JSON, dependency specification, bind address and forwarded-port configuration were inspected. A real Linux Codespace was not created, and physical Android touch, GitHub authentication/forwarding and tablet downloads were not tested. A private forwarded-port smoke test on the intended account/device remains necessary. The local application is stopped after validation and is launched normally from the extracted package.

**Scientific warning:** the source's saved whole-image correction failed its existing QC threshold (277.54 ppm mean absolute residual versus 45 ppm). Retention is not approval. Raw acquisition masses remain the default, and corrected output is explicitly labelled. The full metadata, coefficients, calibration matches and original summary are preserved.
