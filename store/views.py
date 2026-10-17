from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Product
from django.contrib.auth.decorators import login_required


def home(request):
    products = Product.objects.filter(is_active=True)
    return render(request, "store/home.html", {"products": products})


def products(request):
    from decimal import Decimal, InvalidOperation
    from django.db.models import Q

    product_list = Product.objects.filter(is_active=True)

    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if search:
        product_list = product_list.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(category__icontains=search)
        )

    if category:
        product_list = product_list.filter(category__iexact=category)

    filter_error = ""

    if min_price:
        try:
            minimum = Decimal(min_price)
            if not minimum.is_finite() or minimum < 0:
                raise InvalidOperation
            product_list = product_list.filter(price__gte=minimum)
        except (InvalidOperation, ValueError):
            filter_error = "Enter a valid minimum price."

    if max_price:
        try:
            maximum = Decimal(max_price)
            if not maximum.is_finite() or maximum < 0:
                raise InvalidOperation
            product_list = product_list.filter(price__lte=maximum)
        except (InvalidOperation, ValueError):
            filter_error = "Enter a valid maximum price."

    if min_price and max_price and not filter_error:
        try:
            if Decimal(min_price) > Decimal(max_price):
                filter_error = "Minimum price cannot exceed maximum price."
                product_list = Product.objects.filter(is_active=True)
                if search:
                    product_list = product_list.filter(
                        Q(name__icontains=search) |
                        Q(description__icontains=search) |
                        Q(category__icontains=search)
                    )
                if category:
                    product_list = product_list.filter(category__iexact=category)
        except (InvalidOperation, ValueError):
            pass

    sort_options = {
        "newest": "-created_at",
        "price_low": "price",
        "price_high": "-price",
        "name": "name",
    }

    product_list = product_list.order_by(
        sort_options.get(sort, "-created_at")
    )

    categories = (
        Product.objects.filter(is_active=True)
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    return render(request, "store/products.html", {
        "products": product_list,
        "categories": categories,
        "search": search,
        "selected_category": category,
        "min_price": min_price,
        "max_price": max_price,
        "selected_sort": sort,
        "filter_error": filter_error,
    })

def product_detail(request, slug):
    product = get_object_or_404(
        Product,
        slug=slug,
        is_active=True,
    )
    return render(request, "store/product_detail.html", {
        "product": product,
    })


def about(request):
    return render(request, "store/about.html")


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        message = request.POST.get("message", "").strip()

        if name and email and message:
            messages.success(
                request,
                "Thank you! Your message was received by this demo form."
            )
        else:
            messages.error(request, "Please complete every field.")

    return render(request, "store/contact.html")


def faq(request):
    return render(request, "store/faq.html")


def privacy(request):
    return render(request, "store/privacy.html")


def terms(request):
    return render(request, "store/terms.html")


def refund_policy(request):
    return render(request, "store/refund-policy.html")

def add_to_cart(request, product_id):
    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True,
    )

    quantity = request.session.get("cart", {})
    product_key = str(product.id)
    current_quantity = int(quantity.get(product_key, 0))

    if product.stock <= current_quantity:
        messages.error(request, "Sorry, this product is out of stock.")
        return redirect("store:products")

    quantity[product_key] = current_quantity + 1
    request.session["cart"] = quantity
    request.session.modified = True

    messages.success(request, f"{product.name} added to your cart!")
    return redirect("store:products")




@login_required
def wishlist_view(request):
    from .models import Wishlist

    items = Wishlist.objects.filter(
        user=request.user
    ).select_related("product")

    return render(request, "store/wishlist.html", {"wishlist_items": items})


@login_required
def wishlist_add(request, product_id):
    from .models import Wishlist

    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True,
    )

    _, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product,
    )

    if created:
        messages.success(request, f"{product.name} added to your wishlist.")
    else:
        messages.info(request, f"{product.name} is already in your wishlist.")

    return redirect("store:wishlist")


@login_required
def wishlist_remove(request, product_id):
    from .models import Wishlist

    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])

    Wishlist.objects.filter(
        user=request.user,
        product_id=product_id,
    ).delete()

    messages.success(request, "Product removed from your wishlist.")
    return redirect("store:wishlist")

# Cartzo customer dashboard
def dashboard(request):
    from .models import Product

    product_count = Product.objects.count()
    latest_products = list(
        Product.objects.all().order_by("-id")[:6]
    )

    # Use uploaded images when available; otherwise use static images.
    image_extensions = {
        5: "webp",
        71: "png",
        107: "png",
    }

    for product in latest_products:
        if product.image:
            product.static_image = None
        else:
            image_number = ((product.id - 1) % 120) + 1
            extension = image_extensions.get(image_number, "jpg")
            product.static_image = (
                f"images/cartzo-real-{image_number:03d}.{extension}"
            )

    return render(
        request,
        "store/dashboard.html",
        {
            "product_count": product_count,
            "latest_products": latest_products,
        },
    )

