from PIL import Image
import numpy as np

img = Image.open("teeth-upper-rmbg.png").convert("RGBA")
data = np.array(img)

# Threshold the alpha channel — anything > 128 becomes fully opaque
alpha = data[:, :, 3]
data[:, :, 3] = np.where(alpha > 128, 255, 0)

Image.fromarray(data).save("teeth-upper-rmbg_opaque.png")
