import torch
import numpy as np
from PIL import Image
from sam2.build_sam import build_sam2_hf
from sam2.sam2_image_predictor import SAM2ImagePredictor

image_path = "teeth-upper-input.png"
image_pil = Image.open(image_path).convert("RGB")
image = np.array(image_pil)
h, w = image.shape[:2]

predictor = SAM2ImagePredictor.from_pretrained("facebook/sam2-hiera-large")

# Foreground points — middle row hitting each arch
xs_fg = np.linspace(w * 0.03, w * 0.97, 20).astype(int)
ys_fg = np.full_like(xs_fg, h // 2)

# Background points — top and bottom edges (pure white)
xs_bg = np.linspace(0, w, 10).astype(int)
ys_bg_top = np.zeros_like(xs_bg)
ys_bg_bot = np.full_like(xs_bg, h - 1)

input_points = np.concatenate([
    np.stack([xs_fg, ys_fg], axis=1),
    np.stack([xs_bg, ys_bg_top], axis=1),
    np.stack([xs_bg, ys_bg_bot], axis=1),
])
input_labels = np.array([
    *[1] * len(xs_fg),   # foreground
    *[0] * len(xs_bg),   # background top
    *[0] * len(xs_bg),   # background bottom
])

with torch.inference_mode():
    predictor.set_image(image)
    masks, scores, _ = predictor.predict(
        point_coords=input_points,
        point_labels=input_labels,
        multimask_output=False
    )

print(f"Score: {scores}")

combined = masks[0] if masks.ndim == 3 else masks
rgba = np.dstack([image, (combined * 255).astype(np.uint8)])
Image.fromarray(rgba).save("output_sam2.png")
