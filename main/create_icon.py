from PIL import Image, ImageDraw

# Create a 256x256 icon
size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Draw a film reel icon
# Background circle
draw.ellipse([20, 20, 236, 236], fill='#007AFF')

# Film holes
hole_size = 30
holes = [
    (40, 40), (186, 40), (40, 186), (186, 186),
    (113, 40), (40, 113), (186, 113), (113, 186)
]
for x, y in holes:
    draw.ellipse([x, y, x+hole_size, y+hole_size], fill='white')

# Center circle
draw.ellipse([88, 88, 168, 168], fill='white')
draw.ellipse([98, 98, 158, 158], fill='#007AFF')

# Save as ICO
img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
print("Icon created successfully!")
