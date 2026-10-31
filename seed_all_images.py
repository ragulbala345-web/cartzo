from pathlib import Path
from store.models import Product

image_folder = Path("static") / "images"
extensions = {".jpg", ".jpeg", ".png", ".webp"}

category_map = {
    "electronics": "Electronics",
    "smartphone": "Electronics",
    "camera": "Electronics",
    "smartwatch": "Electronics",
    "fashion": "Fashion",
    "footwear": "Footwear",
    "sneakers": "Footwear",
    "running-shoes": "Footwear",
    "sandals": "Footwear",
    "beauty": "Beauty",
    "skincare": "Beauty",
    "accessories": "Accessories",
    "home": "Home",
}

created = 0
skipped = 0

if not image_folder.exists():
    print("ERROR: static/images folder was not found.")
else:
    image_files = sorted(
        file for file in image_folder.iterdir()
        if file.is_file() and file.suffix.lower() in extensions
    )

    print("Image files found:", len(image_files))

    for index, file in enumerate(image_files, start=1):
        image_path = f"images/{file.name}"

        # Skip images already assigned to existing products.
        if Product.objects.filter(static_image=image_path).exists():
            skipped += 1
            continue

        # Create a readable placeholder name from the filename.
        name = file.stem.replace("-", " ").replace("_", " ").title()
        category = "General"

        for keyword, mapped_category in category_map.items():
            if keyword in file.stem.lower():
                category = mapped_category
                break

        product = Product.objects.create(
            name=name,
            category=category,
            price=f"{499 + (index % 25) * 250}.00",
            stock=10 + (index % 40),
            description=f"Discover {name} at Cartzo.",
            static_image=image_path,
            is_active=True,
        )

        created += 1
        print("ADDED:", product.name, "->", image_path)

    print("\nFinished!")
    print("New products added:", created)
    print("Images already assigned:", skipped)
    print("Total products in database:", Product.objects.count())
