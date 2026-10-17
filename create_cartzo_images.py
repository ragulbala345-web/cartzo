from pathlib import Path
from xml.sax.saxutils import escape
import colorsys
import re

from django.db import transaction
from store.models import Product

IMAGE_DIR = Path("static/images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# Product collections used to create 120 individual illustrations.
catalog = {
    "Electronics": [
        "Smartphone Pro", "Smartphone Plus", "Laptop Air", "Laptop Pro",
        "Student Laptop", "Ultra Laptop", "Digital Camera", "Smartwatch",
        "Wireless Headphones", "Gaming Mouse", "Bluetooth Speaker",
        "Studio Headphones", "Wireless Keyboard", "Power Bank",
        "Bluetooth Earbuds", "USB Charger", "Mechanical Keyboard",
        "Portable Projector", "Tablet", "Webcam"
    ],
    "Footwear": [
        "Red Sneakers", "Running Shoes", "Formal Shoes", "Casual Sandals",
        "Sports Shoes", "White Trainers", "Leather Loafers", "Summer Slides",
        "Hiking Boots", "High Top Sneakers", "Walking Shoes", "Ballet Flats",
        "Training Shoes", "Everyday Flip Flops"
    ],
    "Fashion": [
        "Classic T Shirt", "Denim Jacket", "Casual Hoodie", "Summer Dress",
        "Slim Jeans", "Cotton Shirt", "Winter Jacket", "Polo T Shirt",
        "Linen Trousers", "Party Dress", "Cotton Kurta", "Summer Shirt",
        "Womens Cardigan", "Denim Shorts", "Cotton Nightwear",
        "Formal Blazer"
    ],
    "Beauty": [
        "Luxury Perfume", "Skincare Essentials", "Face Moisturizer",
        "Skincare Set", "Serum Bottle", "Makeup Palette", "Lipstick Set",
        "Haircare Kit", "Sunscreen Lotion", "Face Cleanser", "Body Lotion",
        "Vitamin C Serum", "Gentle Face Wash", "Aloe Vera Gel"
    ],
    "Home and Furniture": [
        "Modern Chair", "Accent Chair", "Study Desk", "Table Lamp",
        "Sofa Cushion", "Coffee Table", "Wall Clock", "Ceramic Vase",
        "Bedding Set", "Storage Organizer", "Modern Bookshelf",
        "Wooden Side Table", "Decorative Lamp", "Throw Blanket"
    ],
    "Accessories": [
        "Leather Backpack", "Crossbody Bag", "Sunglasses", "Classic Watch",
        "Gold Necklace", "Minimal Bracelet", "Travel Wallet",
        "Baseball Cap", "Silk Scarf", "Laptop Backpack", "Canvas Tote Bag",
        "Travel Duffel Bag", "Card Holder", "Polarized Sunglasses"
    ],
    "Grocery": [
        "Organic Basmati Rice", "Whole Wheat Flour", "Brown Rice",
        "Toor Dal", "Green Moong Dal", "Premium Oats", "Organic Honey",
        "Peanut Butter", "Olive Oil", "Mixed Dry Fruits", "Green Tea",
        "Breakfast Cereal", "Pasta", "Tomato Sauce", "Corn Flakes",
        "Coconut Oil", "Chickpeas", "Organic Sugar"
    ],
    "Sports": [
        "Yoga Mat", "Adjustable Dumbbells", "Sports Water Bottle",
        "Skipping Rope", "Football", "Basketball", "Tennis Racket",
        "Resistance Bands", "Gym Gloves", "Sports Bag"
    ],
    "Kitchen": [
        "Nonstick Frying Pan", "Electric Kettle", "Steel Lunch Box",
        "Hand Blender", "Food Containers", "Dinner Set",
        "Kitchen Knife Set", "Cutting Board", "Coffee Mug",
        "Water Bottle"
    ],
}

# Generate at least 120 distinct product illustrations.
all_items = []
for category, names in catalog.items():
    for name in names:
        all_items.append((category, name))

# The list contains more than 120 names. Use exactly 120 unique image assets.
all_items = all_items[:120]

def make_svg(index, category, name):
    hue = (index * 0.61803398875) % 1
    r, g, b = colorsys.hsv_to_rgb(hue, 0.70, 0.70)
    accent = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    r2, g2, b2 = colorsys.hsv_to_rgb((hue + 0.18) % 1, 0.48, 0.95)
    pale = f"#{int(r2*255):02x}{int(g2*255):02x}{int(b2*255):02x}"

    # Each illustration uses its own background, accent, layout and product label.
    safe_name = escape(name)
    safe_category = escape(category)
    shape = index % 6

    if category == "Grocery":
        drawing = f'''
        <ellipse cx="450" cy="510" rx="150" ry="35" fill="#000" opacity=".09"/>
        <path d="M345 280 Q450 230 555 280 L530 490 Q450 525 370 490 Z"
              fill="{accent}" stroke="#ffffff" stroke-width="8"/>
        <path d="M375 300 Q450 265 525 300 L510 335 Q450 355 390 335 Z"
              fill="#fff" opacity=".8"/>
        <rect x="380" y="370" width="140" height="85" rx="15" fill="#fff" opacity=".94"/>
        <text x="450" y="405" text-anchor="middle" font-size="20" font-weight="bold" fill="#263238">{escape(name[:15])}</text>
        <text x="450" y="435" text-anchor="middle" font-size="15" fill="#52616b">FRESH • QUALITY</text>
        '''
    elif category in ("Fashion", "Accessories", "Footwear"):
        drawing = f'''
        <ellipse cx="450" cy="515" rx="170" ry="30" fill="#000" opacity=".08"/>
        <path d="M365 280 L415 250 L450 280 L485 250 L535 280
                 L590 370 L530 405 L505 365 L505 475
                 L395 475 L395 365 L370 405 L310 370 Z"
              fill="{accent}" stroke="#fff" stroke-width="7" stroke-linejoin="round"/>
        <path d="M415 250 Q450 315 485 250" fill="none" stroke="#fff" stroke-width="8"/>
        <circle cx="{340 + (index%5)*55}" cy="440" r="{15 + index%4*4}" fill="{pale}" opacity=".85"/>
        '''
    elif category == "Beauty":
        drawing = f'''
        <ellipse cx="450" cy="520" rx="135" ry="25" fill="#000" opacity=".09"/>
        <rect x="380" y="300" width="140" height="205" rx="28" fill="{accent}"/>
        <rect x="405" y="255" width="90" height="55" rx="12" fill="#e8d7c8"/>
        <rect x="405" y="375" width="90" height="75" rx="8" fill="#fff" opacity=".95"/>
        <text x="450" y="405" text-anchor="middle" font-size="16" font-weight="bold" fill="#263238">{escape(name[:10])}</text>
        <text x="450" y="430" text-anchor="middle" font-size="13" fill="#52616b">CARE</text>
        '''
    elif category in ("Home and Furniture", "Kitchen"):
        drawing = f'''
        <ellipse cx="450" cy="515" rx="175" ry="28" fill="#000" opacity=".08"/>
        <path d="M330 340 L570 340 L570 465 L330 465 Z" fill="{accent}"/>
        <path d="M350 465 L370 465 L370 505 L350 505 Z M530 465 L550 465 L550 505 L530 505 Z" fill="#70543e"/>
        <rect x="350" y="290" width="200" height="70" rx="15" fill="{pale}"/>
        <path d="M350 360 L550 360 L550 390 L350 390 Z" fill="#fff" opacity=".55"/>
        '''
    elif category == "Sports":
        drawing = f'''
        <ellipse cx="450" cy="515" rx="150" ry="30" fill="#000" opacity=".08"/>
        <circle cx="450" cy="375" r="115" fill="{accent}" stroke="#fff" stroke-width="8"/>
        <path d="M340 375 Q450 310 560 375 M450 260 Q390 375 450 490 M450 260 Q510 375 450 490"
              fill="none" stroke="#fff" stroke-width="8"/>
        '''
    else:
        drawing = f'''
        <ellipse cx="450" cy="515" rx="160" ry="28" fill="#000" opacity=".08"/>
        <rect x="345" y="300" width="210" height="190" rx="28" fill="{accent}"/>
        <rect x="365" y="320" width="170" height="150" rx="18" fill="{pale}"/>
        <circle cx="450" cy="395" r="{35 + index%4*8}" fill="{accent}"/>
        <path d="M410 395 L440 425 L495 360" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round"/>
        '''

    # Add a unique visual pattern to each image.
    decorations = ""
    for j in range(5):
        x = 90 + ((index * 37 + j * 113) % 720)
        y = 80 + ((index * 53 + j * 71) % 140)
        radius = 7 + ((index + j * 3) % 15)
        decorations += f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{accent}" opacity=".17"/>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1100" viewBox="0 0 900 1100">
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="{pale}"/>
        <stop offset="100%" stop-color="#ffffff"/>
      </linearGradient>
    </defs>
    <rect width="900" height="1100" rx="35" fill="url(#bg)"/>
    {decorations}
    <rect x="45" y="45" width="810" height="1010" rx="35" fill="none" stroke="{accent}" stroke-opacity=".25" stroke-width="3"/>
    <text x="75" y="105" font-family="Arial,sans-serif" font-size="26" font-weight="bold" fill="{accent}">CARTZO  /  COLLECTION</text>
    <text x="75" y="155" font-family="Arial,sans-serif" font-size="22" fill="#52616b">{safe_category.upper()}</text>
    <circle cx="450" cy="380" r="240" fill="#fff" opacity=".45"/>
    {drawing}
    <text x="450" y="700" text-anchor="middle" font-family="Arial,sans-serif" font-size="40" font-weight="bold" fill="#1e293b">{safe_name[:26]}</text>
    <text x="450" y="750" text-anchor="middle" font-family="Arial,sans-serif" font-size="22" fill="#52616b">DISCOVER SOMETHING DIFFERENT</text>
    <rect x="300" y="810" width="300" height="64" rx="32" fill="{accent}"/>
    <text x="450" y="850" text-anchor="middle" font-family="Arial,sans-serif" font-size="22" font-weight="bold" fill="#fff">SHOP CARTZO</text>
    <text x="450" y="990" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" fill="#64748b">UNIQUE DESIGN  •  ITEM {index:03d}</text>
    </svg>'''

# Create 120 independent local SVG files; no network calls are needed.
for index, (category, name) in enumerate(all_items, start=1):
    filename = f"cartzo-item-{index:03d}.svg"
    (IMAGE_DIR / filename).write_text(
        make_svg(index, category, name), encoding="utf-8"
    )

print(f"Created {len(all_items)} unique SVG image files in {IMAGE_DIR.resolve()}")

# Update existing products with distinct illustration files.
existing_products = list(Product.objects.all().order_by("id"))
updated = 0

with transaction.atomic():
    for index, product in enumerate(existing_products, start=1):
        if index > len(all_items):
            break
        product.static_image = f"cartzo-item-{index:03d}.svg"
        product.save(update_fields=["static_image"])
        updated += 1

print(f"Updated {updated} existing product image assignments.")
print("New products have NOT been added by this image-only fix.")
print("Refresh the website using Ctrl+F5.")
