"""Instrumental beds for narrated videos with ACE-Step 1.5 (references/music-gen.md).

    cd <ACE-Step-1.5 checkout> && uv run python <skill>/scripts/ace_bed.py --caption "..." --duration 150 --bpm 100 --key "C Major" --n 3 --seed 7 --out out/ttt
"""
import argparse
import os

from acestep.handler import AceStepHandler
from acestep.inference import GenerationConfig, GenerationParams, generate_music
from acestep.llm_inference import LLMHandler

ap = argparse.ArgumentParser()
ap.add_argument("--caption", required=True)
ap.add_argument("--duration", type=float, required=True)
ap.add_argument("--bpm", type=int)
ap.add_argument("--key", default="")
ap.add_argument("--n", type=int, default=2)
ap.add_argument("--seed", type=int, default=-1)
ap.add_argument("--dit", default="acestep-v15-turbo")
ap.add_argument("--lm", default="acestep-5Hz-lm-1.7B")
ap.add_argument("--out", required=True)
a = ap.parse_args()

root = os.getcwd()  # run from the ACE-Step-1.5 checkout: its checkpoints/ live there
dit, llm = AceStepHandler(), LLMHandler()
dit.initialize_service(project_root=root, config_path=a.dit, device="cuda")
llm.initialize(checkpoint_dir=os.path.join(root, "checkpoints"), lm_model_path=a.lm, backend="pt", device="cuda")
params = GenerationParams(task_type="text2music", caption=a.caption, lyrics="[Instrumental]", instrumental=True,
                          duration=a.duration, bpm=a.bpm, keyscale=a.key, seed=a.seed, shift=3.0)
res = generate_music(dit, llm, params, GenerationConfig(batch_size=a.n, audio_format="wav"), save_dir=a.out)
if not res.success:
    raise SystemExit(f"generation failed: {res.error}")
for x in res.audios:
    print(x["path"], x.get("key"), x["params"].get("seed"))
