from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from hashlib import sha256
from urllib.error import HTTPError
import json
import csv
import time
import re

from django.db import transaction
from django.utils.text import slugify
from store.models import Product

IMAGE_DIR = Path("static/images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# Additional products to help build a 120-product store.
EXTRA_PRODUCTS = [
    ("Grocery", "Organic Basmati Rice", 249),
    ("Grocery", "Whole Wheat Flour", 85),
    ("Grocery", "Brown Rice", 179),
    ("Grocery", "Toor Dal", 145),
    ("Grocery", "Green Moong Dal", 119),
    ("Grocery", "Premium Oats", 159),
    ("Grocery", "Organic Honey", 299),
    ("Grocery", "Peanut Butter", 199),
    ("Grocery", "Olive Oil", 449),
    ("Grocery", "Mixed Dry Fruits", 399),
    ("Grocery", "Green Tea", 179),
    ("Grocery", "Breakfast Cereal", 229),
    ("Grocery", "Pasta", 129),
    ("Grocery", "Tomato Sauce", 99),
    ("Grocery", "Corn Flakes", 199),
    ("Grocery", "Coconut Oil", 249),
    ("Grocery", "Chickpeas", 109),
    ("Grocery", "Organic Sugar", 89),
    ("Electronics", "Wireless Keyboard", 1299),
    ("Electronics", "Portable Power Bank", 1499),
    ("Electronics", "Bluetooth Earbuds", 1799),
    ("Electronics", "USB C Charger", 699),
    ("Electronics", "Mechanical Keyboard", 2499),
    ("Electronics", "Portable Projector", 6999),
    ("Fashion", "Cotton Kurta", 899),
    ("Fashion", "Summer Shirt", 699),
    ("Fashion", "Womens Cardigan", 1299),
    ("Fashion", "Denim Shorts", 799),
    ("Fashion", "Cotton Nightwear", 649),
    ("Fashion", "Formal Blazer", 2499),
    ("Footwear", "White Casual Sneakers", 1799),
    ("Footwear", "Leather Ankle Boots", 2299),
    ("Footwear", "Walking Shoes", 1499),
    ("Footwear", "Ballet Flats", 999),
    ("Footwear", "Training Shoes", 1999),
    ("Footwear", "Everyday Flip Flops", 399),
    ("Beauty", "Vitamin C Serum", 499),
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
]

def image_search(query):
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 12,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 900,
        "format": "json",
    }

    request = Request(
        api + "?" + urlencode(params),
        headers={"User-Agent": "CartzoImageDownloader/1.0 (local ecommerce project)"},
    )

    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    pages = result.get("query", {}).get("pages", {})
    return sorted(
        pages.values(),
        key=lambda page: page.get("index", 9999),
    )

def get_photo(category, name, used_hashes, used_pages, index):
    search_terms = [
        name.replace("-", " ") + " product photograph",
        category + " product photograph",
        category + " " + name.split()[0] + " photograph",
    ]

    for term in search_terms:
        try:
            pages = image_search(term)
        except Exception as error:
            print("Search issue:", error)
            time.sleep(1)
            continue

        for page in pages:
            page_id = str(page.get("pageid", ""))

            if not page_id or page_id in used_pages:
                continue

            infos = page.get("imageinfo", [])
            if not infos:
                continue

            info = infos[0]
            mime = info.get("mime", "")

            if not mime.startswith("image/"):
                continue

            image_url = info.get("thumburl") or info.get("url")
            if not image_url:
                continue

            try:
                req = Request(
                    image_url,
                    headers={"User-Agent": "CartzoImageDownloader/1.0"},
                )
                with urlopen(req, timeout=40) as response:
                    data = response.read()

                if len(data) < 8000:
                    continue

                digest = sha256(data).hexdigest()
                if digest in used_hashes:
                    continue

                extensions = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/webp": ".webp",
                    "image/gif": ".gif",
                }
                ext = extensions.get(mime)
                if not ext:
                    continue

                filename = f"cartzo-real-{index:03d}{ext}"
                (IMAGE_DIR / filename).write_bytes(data)

                used_hashes.add(digest)
                used_pages.add(page_id)

                metadata = info.get("extmetadata", {})
                license_name = metadata.get("LicenseShortName", {}).get("value", "")
                artist = metadata.get("Artist", {}).get("value", "")
                description = page.get("title", "")

                return {
                    "filename": filename,
                    "page": page_id,
                    "title": description,
                    "license": re.sub("<[^>]+>", "", license_name),
                    "artist": re.sub("<[^>]+>", "", artist),
                    "source": image_url,
                }

            except Exception as error:
                print("Photo download issue:", error)

        time.sleep(0.3)

    return None

# Read current products. Never delete existing product records.
products = list(Product.objects.all().order_by("id"))
known_names = {p.name.strip().casefold() for p in products}

new_products = [
    item for item in EXTRA_PRODUCTS
    if item[1].strip().casefold() not in known_names
]

# Keep the existing products and aim for 120 total.
new_products = new_products[:max(0, 120 - len(products))]

catalog = []
for product in products:
    catalog.append({
        "kind": "existing",
        "product": product,
        "name": product.name,
        "category": str(getattr(product, "category", "Electronics")),
        "price": None,
    })

for category, name, price in new_products:
    catalog.append({
        "kind": "new",
        "product": None,
        "name": name,
        "category": category,
        "price": price,
    })

# Download every photograph before changing the database.
used_hashes = set()
used_pages = set()
downloads = []
attributions = []

print(f"Preparing {len(catalog)} product photographs...")
print("This may take several minutes; please keep the terminal open.")

for index, item in enumerate(catalog, start=1):
    print(f"\nSearching {index}/{len(catalog)}: {item['name']}")

    photo = get_photo(
        item["category"],
        item["name"],
        used_hashes,
        used_pages,
        index,
    )

    if not photo:
        raise SystemExit(
            f"\nSTOPPED: Could not find a unique photograph for "
            f"{item['name']}. No product records were changed. "
            "Some downloaded files may remain in static/images."
        )

    item["photo"] = photo
    downloads.append(item)

    attributions.append([
        photo["filename"],
        item["name"],
        item["category"],
        photo["title"],
        photo["artist"],
        photo["license"],
        photo["source"],
    ])

# Save image credits for reference.
with open("cartzo_image_credits.csv", "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.writer(file)
    writer.writerow([
        "Local filename", "Product", "Category",
        "Commons file", "Artist", "License", "Image URL"
    ])
    writer.writerows(attributions)

def find_field(model, field_name):
    try:
        return model._meta.get_field(field_name)
    except Exception:
        return None

def make_category(field, category_name):
    if not field.is_relation:
        return category_name

    model = field.remote_field.model
    possible_names = ["name", "title", "category_name"]

    for key in possible_names:
        try:
            model._meta.get_field(key)
            kwargs = {key: category_name}
            if any(f.name == "slug" for f in model._meta.fields):
                kwargs["slug"] = slugify(category_name)

            obj, _ = model.objects.get_or_create(**kwargs)
            return obj
        except Exception:
            continue

    raise RuntimeError(
        "Cannot safely create category " + category_name +
        ". The images were downloaded, but products were not updated."
    )

# Update images and add new product records inside one database transaction.
updated = 0
created = 0

with transaction.atomic():
    for item in downloads:
        filename = item["photo"]["filename"]

        if item["kind"] == "existing":
            product = item["product"]
            product.static_image = filename
            product.save(update_fields=["static_image"])
            updated += 1
            continue

        fields = {f.name: f for f in Product._meta.fields}
        kwargs = {"name": item["name"]}

        if "slug" in fields:
            base = slugify(item["name"]) or "product"
            slug = base
            counter = 2
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            kwargs["slug"] = slug

        if "price" in fields:
            kwargs["price"] = item["price"]

        if "category" in fields:
            kwargs["category"] = make_category(
                fields["category"], item["category"]
            )

        if "static_image" in fields:
            kwargs["static_image"] = filename

        for field_name in ("description", "details"):
            if field_name in fields:
                kwargs[field_name] = (
                    f"{item['name']} from Cartzo's {item['category']} collection."
                )

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
            if field.name in ("image", "created_at", "updated_at"):
                continue
            if field.has_default() or field.null or field.blank or field.is_relation:
                continue

            kind = field.get_internal_type()
            if kind in ("CharField", "TextField"):
                kwargs[field.name] = ""
            elif kind in (
                "IntegerField", "PositiveIntegerField",
                "PositiveSmallIntegerField", "BigIntegerField",
            ):
                kwargs[field.name] = 0
            elif kind == "BooleanField":
                kwargs[field.name] = True
            elif kind in ("DecimalField", "FloatField"):
                kwargs[field.name] = 0

        Product.objects.create(**kwargs)
        created += 1

print("\n========================================")
print("PHOTO DOWNLOAD AND DATABASE UPDATE COMPLETE")
print("Unique photo files:", len(used_hashes))
print("Existing products updated:", updated)
print("New products added:", created)
print("Total products:", Product.objects.count())
print("Image folder:", IMAGE_DIR.resolve())
print("Image credits: cartzo_image_credits.csv")
print("========================================")
