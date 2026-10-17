import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from store.models import Product


@require_GET
def api_home(request):
    return JsonResponse({
        "name": "Cartzo API",
        "status": "success",
        "endpoints": ["/api/products/", "/api/chat/"],
    })


@require_GET
def products(request):
    product_list = Product.objects.filter(is_active=True)

    data = [
        {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "category": product.category,
            "price": str(product.price),
            "stock": product.stock,
            "description": product.description,
            "image": request.build_absolute_uri(product.image.url)
            if product.image else None,
        }
        for product in product_list
    ]

    return JsonResponse({"products": data})


@csrf_exempt
@require_POST
def chat(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    message = str(body.get("message", "")).strip().lower()

    if not message:
        return JsonResponse({"reply": "Please type a message."})

    if any(word in message for word in ["hello", "hi", "hey"]):
        reply = "Hello! Welcome to Cartzo. How can I help you?"
    elif "product" in message or "shop" in message:
        reply = "Visit the Products page to explore available products."
    elif "cart" in message:
        reply = "Open the Cart page to view your selected products."
    elif "order" in message:
        reply = "Log in and open My Orders to view your orders."
    elif "payment" in message or "pay" in message:
        reply = "This demo currently records orders but does not process payments."
    elif "contact" in message or "support" in message:
        reply = "Visit the Contact page for the demo contact form."
    else:
        reply = "I can help with products, your cart, orders, and store information."

    return JsonResponse({"reply": reply})
