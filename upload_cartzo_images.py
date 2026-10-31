import os
from pathlib import Path

from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import django

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env", override=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cartzo.settings")
django.setup()

from store.models import Product

cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
api_key = os.getenv("CLOUDINARY_API_KEY")
api_secret = os.getenv("CLOUDINARY_API_SECRET")

if not all([cloud_name, api_key, api_secret]):
    raise SystemExit("ERROR: One or more Cloudinary environment variables are missing.")

cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret,
    secure=True,
)

products = {
    "BLACK SHIRT": "WhatsApp_Image_2026-10-18_at_6.39.00_PM_1.jpeg",
    "BLACK COAT": "WhatsApp_Image_2026-10-18_at_6.34.39_PM.jpeg",
    "spiderman tshirt": "WhatsApp_Image_2026-10-18_at_6.17.34_PM.jpeg",
}

print("Starting Cartzo product image upload...")
print("Cloudinary storage:", cloud_name)

for name, filename in products.items():
    path = BASE_DIR / "media" / "products" / filename
    product = Product.objects.filter(name__iexact=name).first()

    if not path.is_file():
        print(f"FILE NOT FOUND: {filename}")
        continue

    if product is None:
        print(f"PRODUCT NOT FOUND: {name}")
        continue

    try:
        result = cloudinary.uploader.upload(
            str(path),
            folder="cartzo/products",
            resource_type="image",
        )

        # Save the Cloudinary public ID through Django's configured storage.
        product.image.name = result["public_id"]
        product.save(update_fields=["image"])

        print(f"SUCCESS: {name}")
        print(f"Image URL: {product.image.url}")

    except Exception as error:
        print(f"FAILED: {name}: {error}")

print("Upload script finished.")
