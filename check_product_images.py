from pathlib import Path
from django.conf import settings
from store.models import Product

base = Path(settings.BASE_DIR)
static_dir = base / "static"
products = list(Product.objects.exclude(static_image="").exclude(static_image__isnull=True))

found = []
missing = []

for product in products:
    image = product.static_image.replace("\\", "/").lstrip("/")
    candidates = [
        static_dir / image,
        static_dir / "images" / image,
        base / "staticfiles" / image,
        base / "media" / image,
    ]

    if any(p.is_file() for p in candidates):
        found.append((product.name, image))
    else:
        missing.append((product.name, image))

print("\n========== CARTZO IMAGE REPORT ==========")
print("Total products:", Product.objects.count())
print("Products with static image paths:", len(products))
print("Image files found locally:", len(found))
print("Image files missing locally:", len(missing))

print("\n--- FOUND IMAGE EXAMPLES ---")
for name, image in found[:10]:
    print(name, "->", image)

print("\n--- MISSING IMAGE EXAMPLES ---")
for name, image in missing[:20]:
    print(name, "->", image)

print("\n--- IMAGE DIRECTORIES ---")
for folder in [base / "static" / "images", base / "media" / "products"]:
    print(folder, "| exists:", folder.exists())
    if folder.exists():
        print("Image files:", sum(1 for p in folder.rglob("*") if p.is_file()))

print("=========================================")
