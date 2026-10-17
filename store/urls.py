from . import ai_views
from django.urls import path
from . import views
from django.shortcuts import render

app_name = "store"


def chatbot_page(request):
    return render(request, "store/chatbot.html")


urlpatterns = [
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/add/<int:product_id>/", views.wishlist_add, name="wishlist_add"),
    path("wishlist/remove/<int:product_id>/", views.wishlist_remove, name="wishlist_remove"),
    path('ai-chat/', ai_views.ai_chat_page, name='ai_chat_page'),
    path('ai-chat/reply/', ai_views.ai_chat_reply, name='ai_chat_reply'),
    path("", views.home, name="home"),
    path("products/", views.products, name="products"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("faq/", views.faq, name="faq"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("refund-policy/", views.refund_policy, name="refund_policy"),
    path("chatbot/", chatbot_page, name="chatbot"),
]



urlpatterns += [path("dashboard/", views.dashboard, name="dashboard")]
