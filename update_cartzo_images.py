from pathlib import Path
from urllib.request import Request, urlopen
import csv
import time

from django.db import transaction
from store.models import Product

IMAGE_DIR = Path("static/images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# Download fresh photos for different product categories.
PHOTO_GROUPS = {
    "electronics": [
        "photo-1511701641625-2b5b4e3a1a12",
        "photo-1517336714731-489689fd1ca8",
        "photo-1496181133206-80ce9b88a853",
        "photo-1505740420928-5e560c06d30e",
        "photo-1516035069371-29a1b244cc32",
        "photo-1523275335684-37898b6baf30",
    ],
    "footwear": [
        "photo-1542291026-7eec264c27ff",
        "photo-1543163521-1bf539c55dd2",
        "photo-1460353581641-37baddab0fa2",
        "photo-1552346154-21d32810aba3",
        "photo-1600185365483-26d7a4cc7519",
    ],
    "fashion": [
        "photo-1521572163474-6864f9cf17ab",
        "photo-1529139574466-a303027c1d8b",
        "photo-1542272604-787c3835535d",
        "photo-1591047139829-d91aecb6caea",
        "photo-1434389677669-e08b4cac3105",
    ],
    "beauty": [
        "photo-1547887538-e3a2f32cb1cc",
        "photo-1608248543803-ba4f8c70ae0b",
        "photo-1556229010-6c3f2c9ca5f8",
        "photo-1596462502278-27bfdc403348",
        "photo-1608571423902-eed4a5ad8108",
    ],
    "home": [
        "photo-1555041469-a586c61ea9bc",
        "photo-1505693416388-ac5ce068fe85",
        "photo-1503602642458-232111445657",
        "photo-1494438639946-1ebd1d20bf85",
        "photo-1616486338812-3dadae4b4ace",
    ],
    "accessories": [
        "photo-1553062407-98eeb64c6a62",
        "photo-1548036328-c9fa89d128fa",
        "photo-1511499767150-a48a237f0083",
        "photo-1584917865442-de89df76afd3",
        "photo-1523381210434-271e8be1f52b",
    ],
}

def download_photo(photo_id, filename):
    destination = IMAGE_DIR / filename

    if destination.exists() and destination.stat().st_size > 5000:
        return True

    url = (
        f"https://images.unsplash.com/{photo_id}"
        "?auto=format&fit=crop&w=800&h=900&q=85"
    )

    try:
        request = Request(
            url,
            headers={"User-Agent": "CartzoProductImageUpdater/1.0"},
        )
        with urlopen(request, timeout=25) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()

        if "image/" not in content_type or len(data) < 5000:
            print(f"Skipped invalid image: {filename}")
            return False

        destination.write_bytes(data)
        print(f"Downloaded: {filename}")
        return True

    except Exception as exc:
        print(f"Download failed for {filename}: {exc}")
        return False


print("\nDownloading new product images...")
available = {}

for group, photo_ids in PHOTO_GROUPS.items():
    available[group] = []

    for number, photo_id in enumerate(photo_ids, start=1):
        filename = f"cartzo-{group}-{number:02d}.jpg"

        if download_photo(photo_id, filename):
            available[group].append(filename)

        time.sleep(0.2)

if not any(available.values()):
    raise SystemExit(
        "\nNo new images could be downloaded. "
        "Check your internet connection. Database was not changed."
    )

# Save a backup before changing any product image assignments.
products = list(Product.objects.all().order_by("id"))
backup_path = Path("cartzo_image_backup.csv")

with backup_path.open("w", newline="", encoding="utf-8-sig") as backup:
    writer = csv.writer(backup)
    writer.writerow(["id", "name", "category", "old_static_image", "uploaded_image"])

    for product in products:
        writer.writerow([
            product.pk,
            product.name,
            str(getattr(product, "category", "")),
            getattr(product, "static_image", ""),
            str(getattr(product, "image", "")),
        ])

def choose_group(product):
    category = str(getattr(product, "category", "")).lower()
    name = str(product.name).lower()
    text = category + " " + name

    if any(word in text for word in [
        "footwear", "shoe", "sneaker", "trainer", "boot", "sandal",
        "slipper", "loafer", "slide"
    ]):
        return "footwear"

    if any(word in text for word in [
        "beauty", "skincare", "skin care", "serum", "cleanser",
        "lotion", "perfume", "makeup", "lipstick", "moisturizer",
        "sunscreen", "haircare", "cosmetic"
    ]):
        return "beauty"

    if any(word in text for word in [
        "home", "furniture", "chair", "desk", "sofa", "table",
        "lamp", "cushion", "clock", "vase", "bedding", "organizer"
    ]):
        return "home"

    if any(word in text for word in [
        "accessories", "backpack", "bag", "wallet", "sunglasses",
        "necklace", "bracelet", "scarf", "cap"
    ]):
        return "accessories"

    if any(word in text for word in [
        "fashion", "clothing", "apparel", "shirt", "dress", "jeans",
        "trousers", "jacket", "hoodie", "t-shirt", "t shirt"
    ]):
        return "fashion"

    if any(word in text for word in [
        "electronics", "electronic", "phone", "smartphone", "laptop",
        "computer", "camera", "headphone", "speaker", "smartwatch",
        "mouse", "tablet", "gaming"
    ]):
        return "electronics"

    return "electronics"

updated = 0
failed = []

with transaction.atomic():
    for product in products:
        group = choose_group(product)
        choices = available.get(group, [])

        # If a category has no downloaded photos, use another available group.
        if not choices:
            choices = next(
                (photos for photos in available.values() if photos),
                [],
            )

        if not choices:
            failed.append(product.name)
            continue

        # Distribute different photos among products in the same category.
        count = sum(
            1 for previous in products[:products.index(product)]
            if choose_group(previous) == group
        )
        filename = choices[count % len(choices)]

        product.static_image = filename
        product.save(update_fields=["static_image"])
        updated += 1

        print(f"Updated: {product.name} -> {filename}")

print("\n===================================")
print(f"Products updated: {updated}")
print(f"Backup saved to: {backup_path}")
print("===================================")
print("\nNext: refresh your Cartzo website using Ctrl + F5.")
