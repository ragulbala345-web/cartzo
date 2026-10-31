from store.models import Product

products = [
    {
        "name": "Smartphone Pro",
        "category": "Electronics",
        "price": "24999.00",
        "stock": 25,
        "image": "images/smartphone-1.jpg",
        "description": "A stylish smartphone with modern features.",
    },
    {
        "name": "Smartphone Plus",
        "category": "Electronics",
        "price": "19999.00",
        "stock": 20,
        "image": "images/smartphone-2.jpg",
        "description": "A modern smartphone for everyday use.",
    },
    {
        "name": "Wireless Smartwatch",
        "category": "Electronics",
        "price": "3999.00",
        "stock": 30,
        "image": "images/smartwatch-1.jpg",
        "description": "A smart wearable for your everyday activities.",
    },
    {
        "name": "Digital Camera",
        "category": "Electronics",
        "price": "15999.00",
        "stock": 12,
        "image": "images/camera-1.jpg",
        "description": "Capture your favorite moments with this camera.",
    },
    {
        "name": "Classic Sneakers",
        "category": "Footwear",
        "price": "1999.00",
        "stock": 40,
        "image": "images/sneakers-1.jpg",
        "description": "Comfortable sneakers for everyday wear.",
    },
    {
        "name": "Running Shoes",
        "category": "Footwear",
        "price": "2499.00",
        "stock": 35,
        "image": "images/running-shoes-1.jpg",
        "description": "Lightweight shoes for running and exercise.",
    },
    {
        "name": "Comfort Sandals",
        "category": "Footwear",
        "price": "899.00",
        "stock": 30,
        "image": "images/sandals-1.jpg",
        "description": "Comfortable sandals for daily use.",
    },
    {
        "name": "Skincare Essentials",
        "category": "Beauty",
        "price": "799.00",
        "stock": 25,
        "image": "images/skincare-1.jpg",
        "description": "Everyday skincare essentials.",
    },
    {
        "name": "Beauty Collection",
        "category": "Beauty",
        "price": "1299.00",
        "stock": 20,
        "image": "images/cartzo-beauty-01.jpg",
        "description": "Discover beauty products for your routine.",
    },
    {
        "name": "Fashion Collection",
        "category": "Fashion",
        "price": "1499.00",
        "stock": 20,
        "image": "images/cartzo-fashion-01.jpg",
        "description": "Modern fashion for your wardrobe.",
    },
    {
        "name": "Everyday Accessories",
        "category": "Accessories",
        "price": "599.00",
        "stock": 40,
        "image": "images/cartzo-accessories-01.jpg",
        "description": "Accessories to complement your everyday style.",
    },
    {
        "name": "Home Essentials",
        "category": "Home",
        "price": "999.00",
        "stock": 20,
        "image": "images/cartzo-home-01.jpg",
        "description": "Useful essentials for your home.",
    },
    {
        "name": "Electronics Collection",
        "category": "Electronics",
        "price": "4999.00",
        "stock": 15,
        "image": "images/cartzo-electronics-02.jpg",
        "description": "Explore modern electronics for everyday life.",
    },
    {
        "name": "Premium Product 01",
        "category": "General",
        "price": "1299.00",
        "stock": 15,
        "image": "images/cartzo-product-01.jpg",
        "description": "A featured product from the Cartzo collection.",
    },
    {
        "name": "Premium Product 02",
        "category": "General",
        "price": "1599.00",
        "stock": 15,
        "image": "images/cartzo-product-02.jpg",
        "description": "Discover quality and value with Cartzo.",
    },
    {
        "name": "Premium Product 03",
        "category": "General",
        "price": "1899.00",
        "stock": 15,
        "image": "images/cartzo-product-03.jpg",
        "description": "A stylish addition to your shopping list.",
    },
    {
        "name": "Premium Product 04",
        "category": "General",
        "price": "2199.00",
        "stock": 10,
        "image": "images/cartzo-product-04.jpg",
        "description": "Explore another featured Cartzo product.",
    },
    {
        "name": "Premium Product 05",
        "category": "General",
        "price": "999.00",
        "stock": 20,
        "image": "images/cartzo-product-05.jpg",
        "description": "An everyday product at an attractive price.",
    },
    {
        "name": "Premium Product 06",
        "category": "General",
        "price": "1799.00",
        "stock": 12,
        "image": "images/cartzo-product-06.jpg",
        "description": "Shop more exciting finds from Cartzo.",
    },
    {
        "name": "Premium Product 07",
        "category": "General",
        "price": "2499.00",
        "stock": 10,
        "image": "images/cartzo-product-07.jpg",
        "description": "A featured item in our online collection.",
    },
]

created_count = 0
existing_count = 0

for item in products:
    name = item["name"]
    image_path = item.pop("image")

    product, created = Product.objects.get_or_create(
        name=name,
        defaults={
            **item,
            "static_image": image_path,
            "is_active": True,
        },
    )

    if created:
        created_count += 1
        print("ADDED:", product.name)
    else:
        existing_count += 1
        print("ALREADY EXISTS:", product.name)

    item["image"] = image_path

print("\nProduct seeding complete!")
print("New products added:", created_count)
print("Products already present:", existing_count)
print("Total products in database:", Product.objects.count())
