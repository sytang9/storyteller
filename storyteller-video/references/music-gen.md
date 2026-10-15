# Generated music (optional): ACE-Step 1.5

`scripts/music.py` is the default bed: free, instant, and the same every run. When a video needs a real track, generate
one with ACE-Step 1.5 (MIT code and weights; generated music may be used commercially) on a GPU host, then mix it with
`sound.py <teaser> --bed <file>`. The same voice duck, cue levels and loudness apply; a file bed is scaled to the
procedural beds' RMS (a mastered track is denser) and plays at 45% before the first break.

## Setup (once per GPU host)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone --depth 1 https://github.com/ACE-Step/ACE-Step-1.5.git && cd ACE-Step-1.5 && uv sync   # Python 3.11-3.12
```

The first run downloads the weights into `checkpoints/` (about 10 GB).

## Generate

```bash
cd ACE-Step-1.5 && CUDA_VISIBLE_DEVICES=1 uv run python <skill>/scripts/ace_bed.py \
  --caption "instrumental background music for a calm technology explainer video, soft warm synth pads, gentle plucked arpeggio, light electronic percussion, steady and unobtrusive, no vocals, no lead melody" \
  --duration <video s + 4> --bpm 100 --key "C Major" --n 3 --seed 7 --out out/<name>
```

- Write the caption from the mood (`references/direction.md`, Music) and always keep "instrumental", "unobtrusive",
  "no vocals, no lead melody": a lead line competes with the narration.
- 2B turbo DiT with the 1.7B LM: about 13.6 GB peak VRAM for 3 takes of 150 s; diffusion about 1.5 s. Any 16 GB GPU fits.
- Make 3 takes, mix each with `sound.py --bed ... --out music/ace-<n>.mp4`, and let a person pick by ear next to the
  procedural moods (`sound.py --moods`): nobody in the pipeline can hear.
