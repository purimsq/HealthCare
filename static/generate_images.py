import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random

def generate_hospital_logo():
    """Generate a simple hospital logo"""
    # Create a blank image with a white background
    width, height = 400, 400
    image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a medical cross
    cross_color = (52, 152, 219)  # Blue
    margin = 100
    
    # Horizontal line
    draw.rectangle(
        [(margin, height//2 - 30), (width - margin, height//2 + 30)],
        fill=cross_color
    )
    
    # Vertical line
    draw.rectangle(
        [(width//2 - 30, margin), (width//2 + 30, height - margin)],
        fill=cross_color
    )
    
    # Add a circle around the cross
    draw.ellipse(
        [(margin - 20, margin - 20), (width - margin + 20, height - margin + 20)],
        outline=cross_color,
        width=8
    )
    
    # Add hospital text
    try:
        # Try to use a font if available
        font = ImageFont.truetype("Arial", 40)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    draw.text((width//2, height - 50), "ST MARY'S HOSPITAL", fill=(70, 70, 70), font=font, anchor="ms")
    
    # Save the logo
    image.save('hospital_logo.png')
    print("Hospital logo generated")

def generate_hospital_background():
    """Generate a hospital hallway background with staff"""
    # Create a blank image with a white background
    width, height = 1200, 800
    background = Image.new('RGB', (width, height), (240, 240, 245))
    draw = ImageDraw.Draw(background)
    
    # Draw floor
    draw.rectangle([(0, height//2), (width, height)], fill=(220, 220, 220))
    
    # Draw ceiling
    draw.rectangle([(0, 0), (width, height//6)], fill=(230, 230, 235))
    
    # Draw walls
    for x in range(0, width, 200):
        # Wall panels
        draw.rectangle([(x, height//6), (x+190, height//2)], fill=(245, 245, 250))
    
    # Draw doors
    for x in range(100, width, 300):
        door_color = (220, 220, 225)
        door_height = height//2 - height//6 - 20
        door_y = height//6 + 10
        draw.rectangle([(x, door_y), (x+80, door_y+door_height)], fill=door_color, outline=(200, 200, 205))
    
    # Add floor tiles
    for y in range(height//2, height, 50):
        for x in range(0, width, 50):
            if (x + y) % 100 == 0:
                draw.rectangle([(x, y), (x+50, y+50)], fill=(210, 210, 210))
    
    # Draw simple figures representing medical staff (stick figures)
    for _ in range(8):
        x = random.randint(100, width-100)
        y = random.randint(height//2 - 150, height - 100)
        person_color = (
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(200, 255) if random.random() > 0.5 else random.randint(100, 200)
        )
        
        # Head
        head_size = random.randint(15, 25)
        draw.ellipse([(x-head_size, y-head_size*2-50), (x+head_size, y-50)], fill=person_color)
        
        # Body
        draw.line([(x, y-50), (x, y)], fill=person_color, width=5)
        
        # Arms
        arm_length = random.randint(20, 30)
        draw.line([(x, y-40), (x-arm_length, y-30)], fill=person_color, width=3)
        draw.line([(x, y-40), (x+arm_length, y-30)], fill=person_color, width=3)
        
        # Legs
        draw.line([(x, y), (x-15, y+40)], fill=person_color, width=4)
        draw.line([(x, y), (x+15, y+40)], fill=person_color, width=4)
    
    # Apply a slight blur to simulate depth and make it appear "faded"
    background = background.filter(ImageFilter.GaussianBlur(radius=1.5))
    
    # Lower the opacity by creating a white overlay with partial transparency
    overlay = Image.new('RGBA', (width, height), (255, 255, 255, 170))
    background = background.convert('RGBA')
    background = Image.alpha_composite(background, overlay)
    
    # Save the background
    background.convert('RGB').save('hospital_background.jpg')
    print("Hospital background generated")

if __name__ == "__main__":
    generate_hospital_logo()
    generate_hospital_background()