1. Generate strip (TeethDreamer)
python TeethDreamer.py \
  -b configs/TeethDreamer.yaml \
  --gpus 0 \
  --test ckpt/TeethDreamer.ckpt \
  --output results \
  data.params.test_dir=example/teeth

This gives you:

results/1832_upper_cond_000_000_000_000.png
results/1832_lower_cond_000_000_000_000.png


Run NeUS with rembg

Go into the folder:

cd instant-nsr-pl

Run:

python run.py \
  --img ../results/1832_upper_cond_000_000_000_000.png \
  --cpu 4 \
  --dir ../results/reconstruction \
  --normal \
  --rembg

For lower:

python run.py \
  --img ../results/1832_lower_cond_000_000_000_000.png \
  --cpu 4 \
  --dir ../results/reconstruction \
  --normal \
  --rembg