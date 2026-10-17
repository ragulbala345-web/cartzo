from decimal import Decimal

import razorpay

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from store.models import Product
from .models import Order, OrderItem


def get_razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ValueError("Razorpay credentials are not configured.")

    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


@login_required
def checkout(request):
    cart = request.session.get("cart", {})

    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart:view_cart")

    cart_items = []
    total = Decimal("0.00")

    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(pk=int(product_id), is_active=True)
            quantity = int(quantity)

            if quantity < 1:
                continue

            cart_items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": product.price * quantity,
            })
            total += product.price * quantity

        except (Product.DoesNotExist, ValueError, TypeError):
            continue

    if not cart_items:
        messages.error(request, "Your cart contains no valid products.")
        return redirect("cart:view_cart")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()
        payment_method = request.POST.get("payment_method", "").strip()

        if not all([full_name, email, address, city, postal_code]):
            messages.error(request, "Please complete all delivery fields.")
            return render(request, "orders/checkout.html", {
                "cart_items": cart_items,
                "total": total,
            })

        if payment_method not in ("cod", "razorpay"):
            messages.error(request, "Please select a payment method.")
            return redirect("orders:checkout")

        order = None

        try:
            with transaction.atomic():
                locked_products = {}

                for item in sorted(cart_items, key=lambda x: x["product"].pk):
                    product = Product.objects.select_for_update().get(
                        pk=item["product"].pk,
                        is_active=True,
                    )

                    if product.stock < item["quantity"]:
                        raise ValueError(
                            f"Not enough stock for {product.name}."
                        )

                    locked_products[product.pk] = product

                order = Order.objects.create(
                    user=request.user,
                    full_name=full_name,
                    email=email,
                    address=address,
                    city=city,
                    postal_code=postal_code,
                    total=total,
                )

                for item in cart_items:
                    product = locked_products[item["product"].pk]

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        price=product.price,
                        quantity=item["quantity"],
                    )

                if payment_method == "cod":
                    for item in cart_items:
                        product = locked_products[item["product"].pk]
                        product.stock -= item["quantity"]
                        product.save(update_fields=["stock"])

                    order.status = "confirmed"
                    order.payment_status = "pending"
                    order.save(update_fields=["status", "payment_status"])

        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("cart:view_cart")

        if payment_method == "cod":
            request.session["cart"] = {}
            request.session.modified = True
            messages.success(
                request,
                f"Cash on Delivery order #{order.pk} placed successfully!",
            )
            return redirect("orders:order_detail", order_id=order.pk)

        try:
            client = get_razorpay_client()
            razorpay_order = client.order.create({
                "amount": int(total * 100),
                "currency": "INR",
                "receipt": f"cartzo_{order.pk}",
            })

            order.razorpay_order_id = razorpay_order["id"]
            order.save(update_fields=["razorpay_order_id"])

            return redirect("orders:payment", order_id=order.pk)

        except Exception:
            order.status = "cancelled"
            order.save(update_fields=["status"])
            messages.error(
                request,
                "Could not start Razorpay payment. Please try again.",
            )
            return redirect("orders:checkout")

    return render(request, "orders/checkout.html", {
        "cart_items": cart_items,
        "total": total,
    })


@login_required
def payment(request, order_id):
    order = Order.objects.filter(
        pk=order_id,
        user=request.user,
    ).first()

    if order is None:
        messages.error(request, "Order not found.")
        return redirect("orders:order_list")

    if order.payment_status == "paid":
        return redirect("orders:order_detail", order_id=order.pk)

    if order.status == "cancelled":
        messages.error(request, "This order has been cancelled.")
        return redirect("orders:order_list")

    if not order.razorpay_order_id:
        messages.error(request, "Payment has not been initialized.")
        return redirect("orders:checkout")

    return render(request, "orders/payment.html", {
        "order": order,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    })


@require_POST
@login_required
def verify_payment(request, order_id):
    order = Order.objects.filter(
        pk=order_id,
        user=request.user,
    ).first()

    if order is None:
        messages.error(request, "Order not found.")
        return redirect("orders:order_list")

    if order.payment_status == "paid":
        messages.success(request, "This order has already been paid.")
        return redirect("orders:order_detail", order_id=order.pk)

    payment_id = request.POST.get("razorpay_payment_id", "").strip()
    razorpay_order_id = request.POST.get("razorpay_order_id", "").strip()
    signature = request.POST.get("razorpay_signature", "").strip()

    if (
        not payment_id
        or not razorpay_order_id
        or not signature
        or razorpay_order_id != order.razorpay_order_id
    ):
        messages.error(request, "Invalid payment information.")
        return redirect("orders:payment", order_id=order.pk)

    try:
        client = get_razorpay_client()
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })

        payment_info = client.payment.fetch(payment_id)

        if payment_info.get("order_id") != order.razorpay_order_id:
            messages.error(request, "Payment does not match this order.")
            return redirect("orders:payment", order_id=order.pk)

        if payment_info.get("status") != "captured":
            messages.error(request, "Payment has not been captured.")
            return redirect("orders:payment", order_id=order.pk)

        if int(payment_info.get("amount", 0)) != int(order.total * 100):
            messages.error(request, "Payment amount does not match.")
            return redirect("orders:payment", order_id=order.pk)

        with transaction.atomic():
            locked_order = Order.objects.select_for_update().get(
                pk=order.pk,
                user=request.user,
            )

            if locked_order.payment_status == "paid":
                return redirect("orders:order_detail", order_id=order.pk)

            if locked_order.status == "cancelled":
                messages.error(request, "This order has been cancelled.")
                return redirect("orders:order_list")

            locked_items = list(
                locked_order.items.select_related("product").order_by(
                    "product_id"
                )
            )

            for item in locked_items:
                product = Product.objects.select_for_update().get(
                    pk=item.product_id
                )

                if product.stock < item.quantity:
                    messages.error(
                        request,
                        "Payment succeeded, but stock needs manual review. "
                        "Please contact support.",
                    )
                    return redirect(
                        "orders:order_detail",
                        order_id=locked_order.pk,
                    )

                product.stock -= item.quantity
                product.save(update_fields=["stock"])

            locked_order.payment_status = "paid"
            locked_order.razorpay_payment_id = payment_id
            locked_order.status = "confirmed"
            locked_order.save(update_fields=[
                "payment_status",
                "razorpay_payment_id",
                "status",
            ])

        request.session["cart"] = {}
        request.session.modified = True
        messages.success(request, "Payment successful! Your order is confirmed.")
        return redirect("orders:order_detail", order_id=order.pk)

    except Exception:
        messages.error(
            request,
            "Payment verification failed. Check Razorpay Test Mode "
            "before trying another payment.",
        )
        return redirect("orders:payment", order_id=order.pk)


@login_required
def order_list(request):
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related("items")
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = Order.objects.filter(
        user=request.user,
        pk=order_id,
    ).prefetch_related("items").first()

    if order is None:
        messages.error(request, "Order not found.")
        return redirect("orders:order_list")

    return render(request, "orders/order_detail.html", {"order": order})


@require_POST
@login_required
def cancel_order(request, order_id):
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(
            user=request.user,
            pk=order_id,
        ).first()

        if order is None:
            messages.error(request, "Order not found.")

        elif order.payment_status == "paid":
            messages.error(
                request,
                "This order is paid. Contact support for cancellation "
                "and any applicable refund.",
            )

        elif order.status != "pending":
            messages.error(
                request,
                "This order cannot be cancelled automatically.",
            )

        else:
            order.status = "cancelled"
            order.save(update_fields=["status"])
            messages.success(request, "Your unpaid order was cancelled.")

    return redirect("orders:order_list")
