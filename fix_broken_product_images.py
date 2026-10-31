from store.models import Product

updates = {
    "BLACK SHIRT": "images/cartzo-fashion-01.jpg",
    "BLACK COAT": "images/cartzo-fashion-02.jpg",
    "spiderman tshirt": "images/cartzo-fashion-03.jpg",
}

for name, image_path in updates.items():
    products = Product.objects.filter(name=name)

    if not products.exists():
        print(f"NOT FOUND: {name}")
        continue

    for product in products:
        product.static_image = image_path
        product.save(update_fields=["static_image"])
        print(f"UPDATED: {product.name} -> {product.static_image}")

print("\nFinished updating product image paths.")
