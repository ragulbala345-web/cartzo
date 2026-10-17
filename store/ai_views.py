import json
import os
import logging

from pathlib import Path
from dotenv import load_dotenv
from google import genai
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import Product

logger = logging.getLogger(__name__)

# Load the API key from the Cartzo project root .env file.
load_dotenv(Path(settings.BASE_DIR) / ".env", override=True)


def ai_chat_page(request):
    return render(request, "store/ai_chat.html")


@require_POST
def ai_chat_reply(request):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not api_key or "PASTE_" in api_key.upper() or "YOUR_" in api_key.upper():
        return JsonResponse(
            {"reply": "Gemini API key is missing. Please configure GEMINI_API_KEY in your Cartzo .env file."},
            status=503,
        )

    try:
        data = json.loads(request.body)
        message = str(data.get("message", "")).strip()

        if not message:
            return JsonResponse(
                {"reply": "Please type a question."},
                status=400,
            )

        if len(message) > 1000:
            return JsonResponse(
                {"reply": "Please keep your question under 1000 characters."},
                status=400,
            )

        products = Product.objects.filter(is_active=True).values(
            "name", "category", "price", "stock"
        )[:50]

        product_lines = []

        for product in products:
            product_lines.append(
                f"Product: {product['name']}; "
                f"Category: {product['category']}; "
                f"Price: Rs. {product['price']}; "
                f"Stock: {product['stock']}"
            )

        catalog = "\n".join(product_lines)

        if not catalog:
            catalog = "The product catalog is currently empty."

        prompt = (
            "You are Cartzo AI, a friendly ecommerce shopping assistant. "
            "Help customers discover products, compare prices, and shop. "
            "Use the supplied product catalog when discussing Cartzo products. "
            "Never invent product names, prices, or stock availability. "
            "If a product is not listed, say you cannot confirm its availability. "
            "Keep answers clear, helpful, and concise. "
            "Do not claim that an order or payment has been completed.\n\n"
            "CARTZO PRODUCT CATALOG:\n"
            f"{catalog}\n\n"
            f"CUSTOMER QUESTION:\n{message}"
        )

        client = genai.Client(api_key=api_key)

        answer = ""
        models_to_try = [
            "gemini-3.5-flash",
            "gemini-3.8-flash",
        ]
        last_error = None

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                answer = (response.text or "").strip()
                if answer:
                    break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Cartzo Gemini model %s failed: %s",
                    model_name,
                    exc,
                )

        if not answer:
            if last_error:
                raise last_error
            answer = "Sorry, I couldn't create an answer. Please try again."

        if not answer:
            answer = "Sorry, I couldn't create an answer. Please try again."

        return JsonResponse({"reply": answer})

    except json.JSONDecodeError:
        return JsonResponse(
            {"reply": "I could not read that message. Please try again."},
            status=400,
        )

    except Exception:
        logger.exception("Cartzo Gemini request failed")
        return JsonResponse(
            {"reply": "Gemini could not answer right now. Check the VS Code terminal for the error details."},
            status=502,
        )


