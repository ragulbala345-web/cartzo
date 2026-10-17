from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from hashlib import sha256
from django.db import transaction
from django.utils.text import slugify
from store.models import Product
import json, csv, time, re

IMAGE_DIR = Path("static/images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
USER_AGENT = "CartzoEducationalStore/1.0 (product photo downloader)"

EXTRA = [
("Grocery","Organic Basmati Rice",249),
("Grocery","Whole Wheat Flour",85),
("Grocery","Brown Rice",179),
("Grocery","Toor Dal",145),
("Grocery","Green Moong Dal",119),
("Grocery","Premium Oats",159),
("Grocery","Organic Honey",299),
("Grocery","Peanut Butter",199),
("Grocery","Olive Oil",449),
("Grocery","Mixed Dry Fruits",399),
("Grocery","Green Tea",179),
("Grocery","Breakfast Cereal",229),
("Grocery","Pasta",129),
("Grocery","Tomato Sauce",99),
("Grocery","Corn Flakes",199),
("Grocery","Coconut Oil",249),
("Grocery","Chickpeas",109),
("Grocery","Organic Sugar",89),
("Electronics","Wireless Keyboard",1299),
("Electronics","Portable Power Bank",1499),
("Electronics","Bluetooth Earbuds",1799),
("Electronics","USB C Charger",699),
("Electronics","Mechanical Keyboard",2499),
("Electronics","Portable Projector",6999),
("Fashion","Cotton Kurta",899),
("Fashion","Summer Shirt",699),
("Fashion","Womens Cardigan",1299),
("Fashion","Denim Shorts",799),
("Fashion","Cotton Nightwear",649),
("Fashion","Formal Blazer",2499),
("Footwear","White Casual Sneakers",1799),
("Footwear","Leather Ankle Boots",2299),
("Footwear","Walking Shoes",1499),
("Footwear","Ballet Flats",999),
("Footwear","Training Shoes",1999),
("Footwear","Everyday Flip Flops",399),
("Beauty","Vitamin C Serum",499),
("Beauty","Gentle Face Wash",249),
("Beauty","Hydrating Face Cream",399),
("Beauty","Matte Lip Colour",349),
("Beauty","Aloe Vera Gel",199),
("Beauty","Nourishing Hair Oil",299),
("Home and Furniture","Modern Bookshelf",3499),
("Home and Furniture","Wooden Side Table",1799),
("Home and Furniture","Decorative Table Lamp",999),
("Home and Furniture","Soft Throw Blanket",899),
("Home and Furniture","Ceramic Dinner Set",1599),
("Home and Furniture","Kitchen Storage Jars",499),
("Accessories","Canvas Tote Bag",499),
("Accessories","Travel Duffel Bag",1299),
("Accessories","Leather Card Holder",599),
("Accessories","Polarized Sunglasses",899),
("Sports","Yoga Mat",799),
("Sports","Adjustable Dumbbells",2499),
("Sports","Insulated Water Bottle",499),
("Sports","Skipping Rope",249),
]

def commons_search(query):
    params = {
        "action":"query", "generator":"search", "gsrsearch":query,
        "gsrnamespace":6, "gsrlimit":12, "prop":"imageinfo",
        "iiprop":"url|mime|extmetadata", "iiurlwidth":900, "format":"json"
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
    for attempt in range(5):
        try:
            req = Request(url, headers={"User-Agent":USER_AGENT})
            with urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            return sorted(result.get("query",{}).get("pages",{}).values(),
                          key=lambda p:p.get("index",9999))
        except HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait = min(60 * (attempt+1), 300)
                print("Server rate limit/busy. Waiting", wait, "seconds.")
                time.sleep(wait)
            else:
                print("Search HTTP error:",e)
                return []
        except Exception as e:
            print("Search issue:",e)
            time.sleep(15)
    return []

products = list(Product.objects.all().order_by("id"))
existing_names = {p.name.strip().casefold() for p in products}
new_items = [x for x in EXTRA if x[1].strip().casefold() not in existing_names]
new_items = new_items[:max(0,120-len(products))]

catalog = [
    {"type":"existing","product":p,"name":p.name,
     "category":str(p.category),"price":None}
    for p in products
]
catalog += [
    {"type":"new","product":None,"name":n,"category":c,"price":price}
    for c,n,price in new_items
]

print("Existing products:",len(products))
print("New products planned:",len(new_items))
print("Total target:",len(catalog))

used_hashes = set()
downloads = []
credits = []
extensions = {"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}

# Reuse valid numbered photos if they exist.
for index,item in enumerate(catalog,1):
    print("\nPhoto",index,"of",len(catalog),":",item["name"])
    found = None

    for old in IMAGE_DIR.glob(f"cartzo-real-{index:03d}.*"):
        if old.is_file() and old.stat().st_size > 8000:
            digest = sha256(old.read_bytes()).hexdigest()
            if digest not in used_hashes:
                used_hashes.add(digest)
                found = (old.name,"","","")
                print("Reusing",old.name)
                break

    if found is None:
        queries = [
            item["name"] + " product photograph",
            item["category"] + " product photograph"
        ]
        for query in queries:
            pages = commons_search(query)
            for page in pages:
                info_list = page.get("imageinfo",[])
                if not info_list:
                    continue
                info = info_list[0]
                mime = info.get("mime","")
                if mime not in extensions:
                    continue
                image_url = info.get("thumburl") or info.get("url")
                if not image_url:
                    continue
                try:
                    req = Request(image_url,headers={"User-Agent":USER_AGENT})
                    with urlopen(req,timeout=40) as response:
                        data = response.read()
                    if len(data) < 8000:
                        continue
                    digest = sha256(data).hexdigest()
                    if digest in used_hashes:
                        continue
                    filename = f"cartzo-real-{index:03d}{extensions[mime]}"
                    (IMAGE_DIR/filename).write_bytes(data)
                    used_hashes.add(digest)
                    meta = info.get("extmetadata",{})
                    artist = re.sub("<[^>]+>","",meta.get("Artist",{}).get("value",""))
                    lic = re.sub("<[^>]+>","",meta.get("LicenseShortName",{}).get("value",""))
                    found = (filename,page.get("title",""),artist,lic)
                    print("Downloaded",filename)
                    break
                except Exception as e:
                    print("Image download issue:",e)
            if found:
                break
            time.sleep(10)

    if not found:
        print("\nSTOPPED: No unique photo found for",item["name"])
        print("Database has NOT been updated.")
        print("Wait before trying again; existing photo files are preserved.")
        raise SystemExit(1)

    item["photo"] = found[0]
    downloads.append(item)
    credits.append([found[0],item["name"],item["category"],found[1],found[2],found[3]])
    time.sleep(5)

with open("cartzo_image_credits.csv","w",newline="",encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["Filename","Product","Category","Commons file","Artist","License"])
    writer.writerows(credits)

updated = 0
created = 0

with transaction.atomic():
    for item in downloads:
        if item["type"] == "existing":
            p = item["product"]
            p.static_image = item["photo"]
            p.save(update_fields=["static_image"])
            updated += 1
        else:
            base = slugify(item["name"]) or "product"
            slug = base
            counter = 2
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            Product.objects.create(
                name=item["name"],
                slug=slug,
                description=f"{item['name']} from Cartzo's {item['category']} collection.",
                category=item["category"],
                price=item["price"],
                stock=25,
                static_image=item["photo"],
                is_active=True
            )
            created += 1

print("\nSUCCESS")
print("Updated existing products:",updated)
print("Created products:",created)
print("Total products:",Product.objects.count())
print("Image folder:",IMAGE_DIR.resolve())
print("Image credits: cartzo_image_credits.csv")
