from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from store.models import Product


def view_cart(request):
    cart = request.session.get("cart", {})
    cart_items = []
    total = Decimal("0.00")

    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(
                pk=int(product_id),
                is_active=True,
            )
            quantity = int(quantity)

            if quantity < 1:
                continue

            subtotal = product.price * quantity

            cart_items.append({
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "quantity": quantity,
                "subtotal": subtotal,
                "image": product.image.url if product.image else "",
            })

            total += subtotal

        except (Product.DoesNotExist, ValueError, TypeError):
            continue

    return render(request, "cart/cart.html", {
        "cart_items": cart_items,
        "total": total,
    })


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(
        Product,
        pk=product_id,
        is_active=True,
    )

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        messages.error(request, "Enter a valid quantity.")
        return redirect("store:product_detail", slug=product.slug)

    cart = request.session.get("cart", {})
    key = str(product.id)
    current_quantity = int(cart.get(key, 0))

    if current_quantity + quantity > product.stock:
        messages.error(request, "There is not enough stock available.")
        return redirect("store:product_detail", slug=product.slug)

    cart[key] = current_quantity + quantity
    request.session["cart"] = cart

    messages.success(request, f"{product.name} added to your cart.")
    return redirect("cart:view_cart")


@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})
    cart.pop(str(product_id), None)
    request.session["cart"] = cart

    messages.success(request, "Product removed from your cart.")
    return redirect("cart:view_cart")
