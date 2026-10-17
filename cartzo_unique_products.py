from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from hashlib import sha256
from decimal import Decimal
from django.db import transaction
from django.utils.text import slugify
from store.models import Product
import csv
import time

IMAGE_DIR = Path("static/images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# 56 additional products, organized by category.
NEW_PRODUCTS = [
    ("Grocery", "Organic Basmati Rice", 249),
    ("Grocery", "Whole Wheat Flour", 85),
    ("Grocery", "Organic Brown Rice", 179),
    ("Grocery", "Toor Dal", 145),
    ("Grocery", "Green Moong Dal", 119),
    ("Grocery", "Premium Oats", 159),
    ("Grocery", "Organic Honey", 299),
    ("Grocery", "Peanut Butter", 199),
    ("Grocery", "Extra Virgin Olive Oil", 449),
    ("Grocery", "Mixed Dry Fruits", 399),
    ("Grocery", "Green Tea", 179),
    ("Grocery", "Wholegrain Breakfast Cereal", 229),

    ("Electronics", "Wireless Keyboard", 1299),
    ("Electronics", "Portable Power Bank", 1499),
    ("Electronics", "Bluetooth Earbuds", 1799),
    ("Electronics", "USB-C Charger", 699),
    ("Electronics", "Mechanical Keyboard", 2499),
    ("Electronics", "Portable Projector", 6999),

    ("Fashion", "Cotton Kurta", 899),
    ("Fashion", "Casual Summer Shirt", 699),
    ("Fashion", "Women's Cardigan", 1299),
    ("Fashion", "Denim Shorts", 799),
    ("Fashion", "Cotton Nightwear", 649),
    ("Fashion", "Formal Blazer", 2499),

    ("Footwear", "White Casual Sneakers", 1799),
    ("Footwear", "Leather Ankle Boots", 2299),
    ("Footwear", "Comfort Walking Shoes", 1499),
    ("Footwear", "Classic Ballet Flats", 999),
    ("Footwear", "Sports Training Shoes", 1999),
    ("Footwear", "Everyday Flip Flops", 399),

    ("Beauty", "Vitamin C Face Serum", 499),
    ("Beauty", "Gentle Face Wash", 249),
    ("Beauty", "Hydrating Face Cream", 399),
    ("Beauty", "Matte Lip Colour", 349),
    ("Beauty", "Aloe Vera Gel", 199),
    ("Beauty", "Nourishing Hair Oil", 299),

    ("Home and Furniture", "Modern Bookshelf", 3499),
    ("Home and Furniture", "Wooden Side Table", 1799),
    ("Home and Furniture", "Decorative Table Lamp", 999),
    ("Home and Furniture", "Soft Throw Blanket", 899),
    ("Home and Furniture", "Ceramic Dinner Set", 1599),
    ("Home and Furniture", "Kitchen Storage Jars", 499),

    ("Accessories", "Canvas Tote Bag", 499),
    ("Accessories", "Travel Duffel Bag", 1299),
    ("Accessories", "Leather Card Holder", 599),
    ("Accessories", "Polarized Sunglasses", 899),

    ("Sports", "Yoga Mat", 799),
    ("Sports", "Adjustable Dumbbells", 2499),
    ("Sports", "Insulated Water Bottle", 499),
    ("Sports", "Skipping Rope", 249),

    ("Kitchen", "Nonstick Frying Pan", 999),
    ("Kitchen", "Electric Kettle", 1299),
    ("Kitchen", "Stainless Steel Lunch Box", 599),
    ("Kitchen", "Hand Blender", 1499),
    ("Kitchen", "Reusable Food Containers", 699),
]

# Existing products are preserved; new names are added only if missing.
existing = list(Product.objects.all().order_by("id"))
existing_names = {p.name.strip().casefold() for p in existing}
additions = [
    item for item in NEW_PRODUCTS
    if item[1].strip().casefold() not in existing_names
]

# Aim for 120 total products. If the store already has more than 120,
# do not delete any products.
target_additions = max(0, 120 - len(existing))
additions = additions[:target_additions]
total = len(existing) + len(additions)

if total < 120:
    print(f"Note: only {len(additions)} additional products are available.")
    print(f"Total planned: {total}. Add more product names if needed.")

def category_for(product):
    category = str(getattr(product, "category", "")).lower()
    name = str(getattr(product, "name", "")).lower()
    text = category + " " + name

    rules = [
        ("Grocery", ["grocery", "rice", "flour", "dal", "oats", "honey", "butter", "olive oil", "dry fruits", "green tea", "cereal"]),
        ("Footwear", ["shoe", "sneaker", "trainer", "boot", "sandal", "slides", "slipper", "footwear", "loafers", "trainers"]),
        ("Beauty", ["beauty", "skin", "serum", "cleanser", "lotion", "perfume", "makeup", "lipstick", "moisturizer", "sunscreen", "haircare", "face wash", "cream", "aloe", "hair oil"]),
        ("Home and Furniture", ["furniture", "chair", "desk", "sofa", "table", "lamp", "cushion", "clock", "vase", "bedding", "organizer", "bookshelf", "blanket"]),
        ("Accessories", ["accessories", "backpack", "bag", "wallet", "sunglasses", "necklace", "bracelet", "scarf", "cap", "watch", "card holder"]),
        ("Fashion", ["fashion", "clothing", "apparel", "shirt", "dress", "jeans", "trousers", "jacket", "hoodie", "kurta", "cardigan", "shorts", "nightwear", "blazer"]),
        ("Kitchen", ["kitchen", "frying pan", "kettle", "lunch box", "blender", "food containers", "dinner set"]),
        ("Sports", ["sports", "yoga", "dumbbell", "water bottle", "skipping rope"]),
        ("Electronics", ["electronics", "phone", "smartphone", "laptop", "computer", "camera", "headphone", "speaker", "smartwatch", "mouse", "tablet", "keyboard", "charger", "projector", "power bank", "earbuds"]),
    ]

    for group, words in rules:
        if any(word in text for word in words):
            return group

    return category.title() if category else "Electronics"

def image_keyword(category, name):
    text = (category + " " + name).lower()
    if any(w in text for w in ["rice", "flour", "dal", "oats", "honey", "butter", "olive oil", "dry fruits", "tea", "cereal", "grocery"]):
        return "grocery,food"
    if any(w in text for w in ["shoe", "sneaker", "trainer", "boot", "sandal", "slipper", "footwear", "loafers"]):
        return "shoes,sneakers"
    if any(w in text for w in ["beauty", "skin", "serum", "cleanser", "lotion", "perfume", "makeup", "lipstick", "moisturizer", "sunscreen", "haircare", "cream", "aloe"]):
        return "skincare,cosmetics"
    if any(w in text for w in ["chair", "desk", "sofa", "table", "lamp", "cushion", "clock", "vase", "bedding", "bookshelf", "blanket", "furniture"]):
        return "furniture,interior"
    if any(w in text for w in ["backpack", "bag", "wallet", "sunglasses", "necklace", "bracelet", "scarf", "cap", "watch", "accessories"]):
        return "fashion,accessories"
    if any(w in text for w in ["shirt", "dress", "jeans", "trousers", "jacket", "hoodie", "kurta", "cardigan", "shorts", "nightwear", "blazer", "fashion"]):
        return "clothing,fashion"
    if any(w in text for w in ["kitchen", "frying pan", "kettle", "lunch box", "blender", "food containers", "dinner set"]):
        return "kitchen,cookware"
    if any(w in text for w in ["sports", "yoga", "dumbbell", "skipping rope"]):
        return "fitness,sports"
    return "electronics,gadgets"

def download_unique(index, category, name, used_hashes):
    keywords = image_keyword(category, name)

    for attempt in range(1, 16):
        # Different lock values request different photos.
        lock = index * 100 + attempt
        url = (
            "https://loremflickr.com/800/900/"
            + quote(keywords, safe=",")
            + "?lock=" + str(lock)
        )
        try:
            req = Request(url, headers={"User-Agent": "CartzoStore/1.0"})
            with urlopen(req, timeout=35) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "")

            if "image/" not in content_type or len(data) < 5000:
                continue

            digest = sha256(data).hexdigest()
            if digest in used_hashes:
                print(f"Repeated image rejected for {name}; retrying...")
                continue

            filename = f"cartzo-unique-{index:03d}.jpg"
            (IMAGE_DIR / filename).write_bytes(data)
            used_hashes.add(digest)
            print(f"[{index}/{total}] {category}: {name} -> {filename}")
            return filename

        except Exception as exc:
            print(f"Attempt {attempt} failed for {name}: {exc}")
            time.sleep(0.5)

    raise RuntimeError(
        f"Could not obtain a unique photo for '{name}'. "
        "No product records have been changed."
    )

# Back up original product image assignments.
backup = Path("cartzo_image_backup_before_unique.csv")
with backup.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "name", "category", "old_static_image", "uploaded_image"])
    for p in existing:
        writer.writerow([
            p.pk, p.name, str(getattr(p, "category", "")),
            getattr(p, "static_image", ""), str(getattr(p, "image", ""))
        ])

# Download and validate every image before modifying product records.
used_hashes = set()
planned = []

for index, product in enumerate(existing, start=1):
    category = category_for(product)
    filename = download_unique(index, category, product.name, used_hashes)
    planned.append(("existing", product, category, filename, None))

for offset, (category, name, price) in enumerate(additions, start=len(existing) + 1):
    filename = download_unique(offset, category, name, used_hashes)
    planned.append(("new", None, category, filename, (name, price)))

# Save all database changes together.
def field_named(model, name):
    try:
        return model._meta.get_field(name)
    except Exception:
        return None

def category_value(field, category):
    if not field.is_relation:
        return category

    related_model = field.remote_field.model
    for candidate in ("name", "title", "category_name"):
        try:
            related_field = related_model._meta.get_field(candidate)
            if related_field:
                obj, _ = related_model.objects.get_or_create(**{candidate: category})
                return obj
        except Exception:
            continue

    raise RuntimeError(
        f"Cannot safely create category '{category}' for related field."
    )

created = 0
updated = 0

with transaction.atomic():
    for kind, product, category, filename, details in planned:
        if kind == "existing":
            product.static_image = filename
            product.save(update_fields=["static_image"])
            updated += 1
            continue

        name, price = details
        fields = {f.name: f for f in Product._meta.fields}
        kwargs = {}

        if "name" not in fields:
            raise RuntimeError("Product model has no name field.")

        kwargs["name"] = name

        if "slug" in fields:
            base_slug = slugify(name) or f"product-{created+1}"
            slug = base_slug
            counter = 2
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            kwargs["slug"] = slug

        if "price" in fields:
            kwargs["price"] = Decimal(str(price))

        if "category" in fields:
            kwargs["category"] = category_value(fields["category"], category)

        if "static_image" in fields:
            kwargs["static_image"] = filename

        for field_name in ("description", "details"):
            if field_name in fields:
                kwargs[field_name] = f"{name} from Cartzo's {category} collection."

        for field_name in ("stock", "quantity", "inventory"):
            if field_name in fields:
                kwargs[field_name] = 25
                break

        for field_name in ("is_active", "active", "available", "is_available"):
            if field_name in fields:
                kwargs[field_name] = True

        for field in Product._meta.fields:
            if field.primary_key or field.name in kwargs:
                continue
            if field.name == "image" or field.name == "created_at" or field.name == "updated_at":
                continue
            if field.has_default() or field.null or field.blank:
                continue
            if field.is_relation:
                continue
            if field.get_internal_type() in ("CharField", "TextField"):
                kwargs[field.name] = ""
            elif field.get_internal_type() in ("IntegerField", "PositiveIntegerField", "PositiveSmallIntegerField", "BigIntegerField"):
                kwargs[field.name] = 0
            elif field.get_internal_type() in ("BooleanField",):
                kwargs[field.name] = True
            elif field.get_internal_type() in ("DecimalField", "FloatField"):
                kwargs[field.name] = Decimal("0")

        Product.objects.create(**kwargs)
        created += 1

print("\nSUCCESS")
print("Existing products updated:", updated)
print("New products added:", created)
print("Total products now:", Product.objects.count())
print("Unique image files downloaded:", len(used_hashes))
print("Backup:", backup)
print("Images folder:", IMAGE_DIR.resolve())
