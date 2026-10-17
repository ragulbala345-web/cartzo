import os
import re
import time
from io import BytesIO
from pathlib import Path
from decimal import Decimal
from urllib.request import Request, urlopen

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cartzo.settings")

import django
django.setup()

from PIL import Image, ImageOps
from store.models import Product
from django.utils.text import slugify

MEDIA = Path("media/products")
MEDIA.mkdir(parents=True, exist_ok=True)

categories = {
    "Electronics": [
        "Smartphone Pro", "Smartphone Plus", "Ultra Laptop",
        "Student Laptop", "Wireless Headphones", "Studio Headphones",
        "Smartwatch", "Digital Camera", "Bluetooth Speaker", "Gaming Mouse"
    ],
    "Footwear": [
        "Red Sneakers", "Running Shoes", "Formal Shoes",
        "Casual Sandals", "High Top Sneakers", "White Trainers",
        "Sports Shoes", "Leather Loafers", "Summer Slides", "Hiking Boots"
    ],
    "Fashion": [
        "Classic T Shirt", "Denim Jacket", "Casual Hoodie",
        "Summer Dress", "Slim Jeans", "Cotton Shirt",
        "Winter Jacket", "Polo T Shirt", "Linen Trousers", "Party Dress"
    ],
    "Beauty": [
        "Luxury Perfume", "Skincare Set", "Face Moisturizer",
        "Serum Bottle", "Makeup Palette", "Lipstick Set",
        "Haircare Kit", "Sunscreen Lotion", "Face Cleanser", "Body Lotion"
    ],
    "Home and Furniture": [
        "Modern Chair", "Accent Chair", "Study Desk",
        "Table Lamp", "Sofa Cushion", "Coffee Table",
        "Wall Clock", "Ceramic Vase", "Bedding Set", "Storage Organizer"
    ],
    "Accessories": [
        "Leather Backpack", "Crossbody Bag", "Sunglasses",
        "Classic Watch", "Gold Necklace", "Minimal Bracelet",
        "Travel Wallet", "Baseball Cap", "Silk Scarf", "Laptop Backpack"
    ],
}

search_tags = {
    "Electronics": "electronics,gadget",
    "Footwear": "shoes,sneakers",
    "Fashion": "fashion,clothing",
    "Beauty": "beauty,cosmetics",
    "Home and Furniture": "furniture,home",
    "Accessories": "fashion,accessories",
}

base_prices = {
    "Electronics": 2499,
    "Footwear": 999,
    "Fashion": 599,
    "Beauty": 399,
    "Home and Furniture": 799,
    "Accessories": 499,
}

def save_square_image(data, destination):
    with Image.open(BytesIO(data)) as original:
        image = ImageOps.fit(
            original.convert("RGB"),
            (800, 800),
            method=Image.Resampling.LANCZOS
        )
        image.save(destination, "JPEG", quality=92, optimize=True)

def download_image(tags, number, destination):
    url = (
        f"https://loremflickr.com/1000/1000/{tags}"
        f"?lock={number}"
    )
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 CartzoStore/1.0"}
    )
    with urlopen(request, timeout=35) as response:
        data = response.read()

    if len(data) < 5000:
        raise ValueError("Downloaded file is too small to be a product photo")

    save_square_image(data, destination)

# Existing local photos are used as a fallback if a download fails.
existing_images = [
    p for p in MEDIA.glob("*")
    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
]

created = 0
updated = 0
failed = []
number = 0

for category, names in categories.items():
    for position, name in enumerate(names):
        number += 1
        filename = f"cartzo-product-{number:02d}.jpg"
        destination = MEDIA / filename

        tags = search_tags[category]

        print(f"\n[{number}/60] Preparing {name}...")

        try:
            download_image(tags, number + 100, destination)
            print("Photo downloaded and resized to 800 x 800.")
        except Exception as error:
            print("Online download failed:", str(error)[:150])

            if existing_images:
                try:
                    fallback = existing_images[(number - 1) % len(existing_images)]
                    with Image.open(fallback) as original:
                        image = ImageOps.fit(
                            original.convert("RGB"),
                            (800, 800),
                            method=Image.Resampling.LANCZOS
                        )
                        image.save(destination, "JPEG", quality=92)
                    print("Used an existing local photo as fallback:", fallback.name)
                except Exception as fallback_error:
                    print("Could not prepare image:", fallback_error)
                    failed.append(name)
                    continue
            else:
                failed.append(name)
                continue

        slug = slugify(name)
        price = Decimal(str(base_prices[category] + position * 250))

        try:
            product, was_created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": category,
                    "description": (
                        f"Discover the {name} at Cartzo. "
                        "A stylish choice for your everyday needs."
                    ),
                    "price": price,
                    "stock": 10 + position,
                    "image": f"products/{filename}",
                    "is_active": True,
                }
            )

            if was_created:
                created += 1
            else:
                updated += 1

            print("Product connected to database:", name)

        except Exception as error:
            print("Database error for", name, ":", error)
            failed.append(name)

print("\n========== CARTZO RESULTS ==========")
print("New products:", created)
print("Updated products:", updated)
print("Total products in database:", Product.objects.count())
print("Image files created:", len(list(MEDIA.glob("cartzo-product-*.jpg"))))
print("Failed products:", failed)
print("Image folder:", MEDIA.resolve())
print("====================================")
