from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from hashlib import sha256
from django.db import transaction
from django.utils.text import slugify
from store.models import Product
import json, csv, time, re

folder = Path("static/images")
folder.mkdir(parents=True, exist_ok=True)

# The script previously stopped at 103. Reuse photos already downloaded.
catalog = list(Product.objects.all().order_by("id"))

extras = [
("Grocery","Organic Basmati Rice",249),("Grocery","Whole Wheat Flour",85),
("Grocery","Brown Rice",179),("Grocery","Toor Dal",145),
("Grocery","Green Moong Dal",119),("Grocery","Premium Oats",159),
("Grocery","Organic Honey",299),("Grocery","Peanut Butter",199),
("Grocery","Olive Oil",449),("Grocery","Mixed Dry Fruits",399),
("Grocery","Green Tea",179),("Grocery","Breakfast Cereal",229),
("Grocery","Pasta",129),("Grocery","Tomato Sauce",99),
("Grocery","Corn Flakes",199),("Grocery","Coconut Oil",249),
("Grocery","Chickpeas",109),("Grocery","Organic Sugar",89),
("Electronics","Wireless Keyboard",1299),("Electronics","Portable Power Bank",1499),
("Electronics","Bluetooth Earbuds",1799),("Electronics","USB C Charger",699),
("Electronics","Mechanical Keyboard",2499),("Electronics","Portable Projector",6999),
("Fashion","Cotton Kurta",899),("Fashion","Summer Shirt",699),
("Fashion","Womens Cardigan",1299),("Fashion","Denim Shorts",799),
("Fashion","Cotton Nightwear",649),("Fashion","Formal Blazer",2499),
("Footwear","White Casual Sneakers",1799),("Footwear","Leather Ankle Boots",2299),
("Footwear","Walking Shoes",1499),("Footwear","Ballet Flats",999),
("Footwear","Training Shoes",1999),("Footwear","Everyday Flip Flops",399),
("Beauty","Vitamin C Serum",499),("Beauty","Gentle Face Wash",249),
("Beauty","Hydrating Face Cream",399),("Beauty","Matte Lip Colour",349),
("Beauty","Aloe Vera Gel",199),("Beauty","Nourishing Hair Oil",299),
("Home and Furniture","Modern Bookshelf",3499),("Home and Furniture","Wooden Side Table",1799),
("Home and Furniture","Decorative Table Lamp",999),("Home and Furniture","Soft Throw Blanket",899),
("Home and Furniture","Ceramic Dinner Set",1599),("Home and Furniture","Kitchen Storage Jars",499),
("Accessories","Canvas Tote Bag",499),("Accessories","Travel Duffel Bag",1299),
("Accessories","Leather Card Holder",599),("Accessories","Polarized Sunglasses",899),
("Sports","Yoga Mat",799),("Sports","Adjustable Dumbbells",2499),
("Sports","Insulated Water Bottle",499),("Sports","Skipping Rope",249),
]

known = {p.name.strip().casefold() for p in catalog}
for category, name, price in extras:
    if name.casefold() not in known and len(catalog) < 120:
        catalog.append({"name": name, "category": category, "price": price, "new": True})
    else:
        pass

# Normalize catalog to dictionaries.
normalized = []
for item in catalog:
    if isinstance(item, dict):
        normalized.append(item)
    else:
        normalized.append({
            "name": item.name,
            "category": str(item.category),
            "product": item,
            "new": False,
        })
catalog = normalized[:120]

used = set()
assignments = []
credits = []

def search(q):
    params = {
        "action":"query","generator":"search","gsrsearch":q,
        "gsrnamespace":6,"gsrlimit":10,"prop":"imageinfo",
        "iiprop":"url|mime|extmetadata","iiurlwidth":900,"format":"json"
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
    req = Request(url,headers={"User-Agent":"CartzoStore/1.0 contact: site administrator"})
    with urlopen(req,timeout=30) as response:
        data = json.loads(response.read().decode())
    return data.get("query",{}).get("pages",{}).values()

extensions = {"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}

for i,item in enumerate(catalog,1):
    print(f"Checking {i}/120: {item['name']}")
    target = next(iter(sorted(folder.glob(f"cartzo-real-{i:03d}.*"))),None)

    # Reuse existing numbered files when available.
    if target and target.is_file() and target.stat().st_size > 8000:
        digest = sha256(target.read_bytes()).hexdigest()
        if digest not in used:
            used.add(digest)
            assignments.append((item,target.name))
            continue

    # If the file is missing, search with broader terms and retry slowly.
    found = None
    terms = [
        item["name"] + " product",
        item["category"] + " product photography",
        item["name"].split()[0] + " product photograph",
    ]

    for term in terms:
        for attempt in range(3):
            try:
                pages = list(search(term))
                break
            except Exception as e:
                print("Search temporarily failed:",e)
                time.sleep(30 * (attempt + 1))
        else:
            continue

        for page in pages:
            infos = page.get("imageinfo",[])
            if not infos:
                continue
            info = infos[0]
            mime = info.get("mime","")
            if mime not in extensions:
                continue
            image_url = info.get("thumburl") or info.get("url")
            if not image_url:
                continue
            try:
                req = Request(image_url,headers={"User-Agent":"CartzoStore/1.0"})
                with urlopen(req,timeout=35) as response:
                    data = response.read()
                if len(data) < 8000:
                    continue
                digest = sha256(data).hexdigest()
                if digest in used:
                    continue
                filename = f"cartzo-real-{i:03d}{extensions[mime]}"
                (folder/filename).write_bytes(data)
                used.add(digest)
                meta = info.get("extmetadata",{})
                artist = re.sub("<[^>]+>","",meta.get("Artist",{}).get("value",""))
                lic = re.sub("<[^>]+>","",meta.get("LicenseShortName",{}).get("value",""))
                found = (filename,page.get("title",""),artist,lic)
                break
            except Exception:
                continue
        if found:
            break
        time.sleep(15)

    if not found:
        # Do not stop just because one search term is unavailable.
        # Reuse another existing photo only as a last resort.
        print("No new image found for",item["name"])
        continue

    assignments.append((item,found[0]))
    credits.append([found[0],item["name"],item["category"],found[1],found[2],found[3]])
    time.sleep(10)

# Only update products for which a file exists.
updated = 0
created = 0
with transaction.atomic():
    for item,filename in assignments:
        if item.get("new"):
            base = slugify(item["name"]) or "product"
            slug = base
            n = 2
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            Product.objects.create(
                name=item["name"], slug=slug,
                description=f"{item['name']} from Cartzo's {item['category']} collection.",
                category=item["category"], price=item["price"],
                stock=25, static_image=filename, is_active=True
            )
            created += 1
        else:
            p = item.get("product")
            if p:
                p.static_image = filename
                p.save(update_fields=["static_image"])
                updated += 1

with open("cartzo_image_credits.csv","a",newline="",encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerows(credits)

print("\nFINISHED AS FAR AS AVAILABLE PHOTOS")
print("Updated existing products:",updated)
print("New products added:",created)
print("Current total products:",Product.objects.count())
print("Images folder:",folder.resolve())
print("Note: any products without a new photo were left unchanged.")
