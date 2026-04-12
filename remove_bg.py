from rembg import remove
from PIL import Image

input_img = Image.open("teeth-upper-input.png")
output_img = remove(input_img)
output_img.save("teeth_no_bg.png")
