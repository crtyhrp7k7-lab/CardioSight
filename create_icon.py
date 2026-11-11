"""
Create icon for CardioSight Shunt Digital Twin
"""
from PIL import Image, ImageDraw, ImageFont

# Create image with white background
size = 256
image = Image.new('RGBA', (size, size), (255, 255, 255, 255))
draw = ImageDraw.Draw(image)

# Draw heart shape background (red)
heart_color = (220, 50, 50, 255)  # Red

# Left side of heart (circle)
draw.ellipse([40, 50, 140, 150], fill=heart_color)
# Right side of heart (circle)
draw.ellipse([116, 50, 216, 150], fill=heart_color)
# Bottom triangle of heart
draw.polygon([40, 100, 128, 200, 216, 100], fill=heart_color)

# Draw shunt device (white rectangle with arrow)
shunt_color = (255, 255, 255, 255)
arrow_color = (100, 150, 255, 255)  # Light blue for flow

# Vertical shunt device
draw.rectangle([110, 90, 146, 160], fill=shunt_color, outline=(50, 50, 50, 255), width=3)

# Arrow showing left-to-right flow
arrow_width = 8
arrow_y = 125
# Arrow shaft
draw.rectangle([115, arrow_y-arrow_width//2, 141, arrow_y+arrow_width//2], fill=arrow_color)
# Arrow head
draw.polygon([141, arrow_y-12, 141, arrow_y+12, 155, arrow_y], fill=arrow_color)

# Add small "LA" and "RA" labels
try:
    from PIL import ImageFont
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # LA (left atrium) - left side
    draw.text((65, 100), "LA", fill=(255, 255, 255, 255), font=font)
    # RA (right atrium) - right side
    draw.text((165, 100), "RA", fill=(255, 255, 255, 255), font=font)
except:
    pass

# Draw border
draw.rectangle([0, 0, size-1, size-1], outline=(50, 50, 50, 255), width=2)

# Save as ICO
image.save('cardiosight_icon.ico', format='ICO',
          sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

print("CardioSight icon created successfully!")
