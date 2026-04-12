# Project Guidelines

## Code Style
- Keep changes minimal and localized; preserve existing script-style structure and argparse interfaces.
- Prefer Python entrypoints already used in this repo instead of adding new orchestration layers.
- Do not modify generated artifacts or environment folders (`venv/`, `anylabeling-env/`, `labelme-env/`, `results/`, `logs/`, `ckpt/`) unless explicitly asked.
- When searching or refactoring, scope to project code (`*.py`, `configs/`, `instant-nsr-pl/`, `ldm/`) and avoid package files under local virtualenv directories.

## Architecture
- Main generation/training entrypoint: `TeethDreamer.py` using config `configs/TeethDreamer.yaml`.
- Teeth segmentation (interactive SAM clicks): `seg_teeth.py`.
- Optional foreground cleanup for generated images: `seg_foreground.py`.
- 3D reconstruction pipeline is delegated to `instant-nsr-pl/`:
  - `instant-nsr-pl/run.py` prepares data and launches reconstruction.
  - `instant-nsr-pl/tools.py` builds train/val/test image folders and camera transform JSONs.
  - `instant-nsr-pl/launch.py` starts Lightning training/validation/test with YAML configs.
- Model/data config boundaries:
  - TeethDreamer diffusion config: `configs/TeethDreamer.yaml`.
  - NeuS reconstruction configs: `instant-nsr-pl/configs/neus-blender.yaml` and `instant-nsr-pl/configs/neus-blender-normal.yaml`.

## Build And Test
- Environment setup (official repo path):
  - `pip install torch==1.12.0+cu116 torchvision==0.13.0+cu116 torchaudio==0.12.0 --extra-index-url https://download.pytorch.org/whl/cu116`
  - `pip install -r requirements.txt`
- Inference generation:
  - `python TeethDreamer.py -b configs/TeethDreamer.yaml --gpus 0 --test ckpt/TeethDreamer.ckpt --output <out_dir> data.params.test_dir=<segmented_dir>`
- Reconstruction:
  - `cd instant-nsr-pl && python run.py --img <merged_png> --cpu <n> --dir <recon_out> --normal --rembg`
- Command-runner backend for `command-runner.html`:
  - `python runner.py`
  - endpoint: `POST http://127.0.0.1:8787/run` with JSON `{"command": "...", "cwd": "..."}`
- No dedicated unit/integration test suite is defined in this repository. Validate changes with targeted smoke runs of the affected script(s).

## Conventions
- Required checkpoints are expected under `ckpt/` (for example `TeethDreamer.ckpt`, `zero123-xl.ckpt`, `ViT-L-14.pt`, `sam_vit_b_01ec64.pth`).
- `seg_teeth.py` assumes five intra-oral images are numbered `0..4` in a fixed view order before segmentation.
- `instant-nsr-pl/run.py` selects upper/lower camera pose files by checking whether the image filename contains `lower`.
- `instant-nsr-pl/run.py` and `instant-nsr-pl/launch.py` assume CUDA GPU execution (`--gpu 0`); avoid introducing CPU-only defaults unless requested.
- Prefer command-line config overrides instead of hardcoding paths in YAML.
- `command-runner.html` composes three commands (generate, upper NeUS, lower NeUS) and can run them sequentially; keep command arguments/path fields aligned with the current pipeline defaults.

## Pitfalls
- This workspace contains multiple local environments (`venv/`, `anylabeling-env/`, `labelme-env/`) with thousands of third-party files. Exclude them from searches and edits.
- Dependencies include Git-based installs and CUDA extensions (for example `tiny-cuda-nn` in `requirements.txt`), which can fail without a proper compiler/CUDA toolchain.
- README hardware/software notes may differ from local machine setup; preserve compatibility when changing version pins.
- `runner.py` executes shell commands via `subprocess.run(shell=True, ...)`; keep it bound to localhost and preserve workspace-root cwd restrictions (`_resolve_safe_cwd`) and command length/timeout guards.
