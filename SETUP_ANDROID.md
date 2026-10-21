# Set up on an Android tablet

## 1. Create a private repository

Sign in to [GitHub](https://github.com), choose **New repository**, enter a name such as `tofsims-cloud-dev`, select **Private**, and create it with a README so a default branch exists. Use a current Chrome or Edge browser on Android, landscape orientation and **Desktop site** if controls are hidden. A keyboard is helpful but optional. Check your account's Codespaces quota and spending settings before travelling; available machine types and allowances depend on your account.

## 2. Transfer the package before travel

Unzip `tofsims_cloud_dev.zip` on your laptop. Upload the **contents of its `tofsims_cloud_dev/` folder** so `main.py`, `requirements.txt` and `.devcontainer/` are at the repository root, without another enclosing folder. Include both demos, data metadata/reports, core/, gui/, scripts/, tests/, documentation, `.gitignore` and `pytest.ini`. Exclude work/, ZIP files, virtual environments and original raw data. Enable hidden-file display to include `.devcontainer` and `.gitignore`.

Use **Add file → Upload files**, choose the extracted contents, and commit. Each demo is below 25 MiB. If the uploader does not preserve `.devcontainer`, use **Add file → Create new file**, enter `.devcontainer/devcontainer.json`, and paste its contents from the extracted copy. Do the same for `.gitignore` if necessary. Verify these files in the repository before continuing. Uploading the ZIP alone does not install the project; extract it first.

Alternatively, for an **empty** repository without an initial README, use a Git-enabled terminal in the extracted package, replacing the URL with your own:

```bash
git init
git add .
git commit -m "Add portable ToF-SIMS development package"
git branch -M main
git remote add origin https://github.com/YOUR-USER/YOUR-REPO.git
git push -u origin main
```

Use GitHub's normal sign-in flow; do not put credentials in source files. See [GitHub file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) for browser and Git upload limits.

## 3. Start a Codespace

Open the repository and choose **Code → Codespaces → Create codespace on main**. If offered a machine choice, start with 2 cores / 4 GB. Wait for setup and automatic dependency installation. `.devcontainer/devcontainer.json` supplies Python 3.12 and forwards 8080. If added after the Codespace was created, use the Command Palette and choose **Codespaces: Rebuild Container**.

## 4. Open the editor on Android

Visit [Your Codespaces](https://github.com/codespaces), select the existing Codespace and open it in the browser. VS Code web provides the explorer, editor and terminal. Use landscape mode and Desktop site if necessary. Popup rules may require you to tap the forwarded-port link yourself.

## 5. Open a terminal

Choose **Terminal → New Terminal** in the VS Code menu, sometimes inside the menu button on a small screen. Type `ls` and confirm `main.py`, `requirements.txt` and `data/` appear. If everything is inside an extra folder, `cd tofsims_cloud_dev` works for the current session; correct the repository-root arrangement before recreating a Codespace so the devcontainer is detected.

## 6. Run the application

```bash
python main.py
```

Wait for **NiceGUI ready to go** on port 8080. Leave that terminal running. Use a second terminal for tests or Git. If packages were not installed automatically:

```bash
python -m pip install -r requirements-dev.txt
python main.py
```

## 7. Open private port 8080

Open **Ports** beside Terminal, or use the Command Palette and **Ports: Focus on Ports View**. Find 8080; if absent, choose **Forward a Port** and enter `8080`. Keep **Port Visibility: Private**. Tap the globe/Open in Browser action or forwarded address and sign in to GitHub if requested.

Use the `https://…app.github.dev` forwarded address. `localhost:8080` on your tablet means the tablet, not the Codespace. Private is GitHub's default; the configuration never requests Public visibility. A private repository alone does not protect a port manually made Public. See [port forwarding](https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace) and [Codespaces security](https://docs.github.com/en/codespaces/reference/security-in-github-codespaces).

## 8. Edit, save and test

Tap a file in the explorer, edit it and choose **File → Save**, or Ctrl+S with a keyboard. Layout lives in `gui/layout.py`, plotting in `gui/components.py`, and scientific operations in `core/`. Press Ctrl+C in the server terminal and rerun `python main.py`, then refresh the application tab. Python changes do not reload automatically.

Run checks in another terminal:

```bash
python -m pytest -q
python scripts/validate_demo_data.py
```

Select a reference ion, adjust scaling/colormap, and tap Update ion map. ROI controls use integer start/end bounds and Analyze ROI. CSV/PNG exports go to the browser's Downloads location.

## 9. Commit and push

In Source Control review changed files, stage the intended changes, enter a commit message, choose Commit, then Sync/Push. Or use:

```bash
git status
git add main.py core gui scripts tests README.md SETUP_ANDROID.md ARCHITECTURE.md
git commit -m "Refine ToF-SIMS GUI"
git push
```

Stage other changed files deliberately. work/ is ignored. Saving a file does not push it to GitHub. Make a useful commit before ending your session.

## 10. Stop when finished

Stop the server with Ctrl+C, save/commit/push, then visit [Your Codespaces](https://github.com/codespaces). Choose **… → Stop codespace** for this Codespace. Closing tabs alone does not stop it. Stopped Codespaces can still incur storage charges; inspect your account's usage and delete old Codespaces only after required work is pushed. See [GitHub's stop/restart guide](https://docs.github.com/en/codespaces/developing-in-a-codespace/stopping-and-starting-a-codespace).

## 11. Resume later

Open Your Codespaces, select the existing one, wait for it to resume and run `python main.py` in its terminal. Reopen private port 8080. Creating a new Codespace gives a fresh GitHub checkout, without unpushed changes from the old one.

## Troubleshooting

- **No port / connection refused:** inspect the Python terminal and Ready message. Keep the server running, forward 8080 manually, check Private visibility and sign into the same GitHub account. Use the forwarded HTTPS address. Stop an old server if it occupies 8080 instead of starting duplicate copies.
- **Certificate warning:** use the normal GitHub forwarded URL and account; do not bypass browser certificate warnings.
- **Package install failure:** run `python --version` (expected 3.12), then `python -m pip install -r requirements-dev.txt`. Read the first actual install error. Rebuild the container if its configuration was missed. Installation requires internet access and disk space.
- **Missing dataset:** run `ls -lh data/`. Both demos must be extracted/uploaded as files. Automatic loading expects `data/tofsims_demo_256.npz`. If only the 512 demo is present, run `python scripts/rebin_packaged_demo.py --target 256`, then validate. If both are absent, upload them from the ZIP.
- **Unsupported NPZ:** source caches require the companion QMS and converter in README. Arbitrary cubes and normalized ion maps are not inferred.
- **Empty ion image:** check mass bounds and acquisition/corrected mass choice. The saved correction failed QC; a reference candidate may have no detectable signal. Unacquired regions stay blank.
- **Simplified spectrum after zoom:** enter narrower numerical mass bounds and press Update spectrum. Zoom alone does not request a finer spectrum.
- **Awkward gestures:** use landscape/full browser view and numerical ROI bounds. Keep separate editor and app tabs. Full-spectrum exports may take a moment.
