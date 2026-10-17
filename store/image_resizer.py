from io import BytesIO

from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product


@receiver(post_save, sender=Product)
def resize_product_image(sender, instance, **kwargs):
    image_field = instance.image

    if not image_field or not image_field.name:
        return

    try:
        with image_field.open("rb") as image_file:
            with Image.open(image_file) as original:
                original.load()

                # Convert the uploaded image into RGB.
                image = ImageOps.exif_transpose(original).convert("RGB")

                # Fit the complete product inside an 800 x 800 canvas.
                image.thumbnail((800, 800), Image.Resampling.LANCZOS)

                canvas = Image.new("RGB", (800, 800), "white")
                x = (800 - image.width) // 2
                y = (800 - image.height) // 2
                canvas.paste(image, (x, y))

                output = BytesIO()
                canvas.save(output, format="JPEG", quality=92, optimize=True)
                output.seek(0)

                path = image_field.name
                storage = image_field.storage

                # Avoid rewriting images already normalized to 800 x 800.
                with storage.open(path, "rb") as saved_file:
                    with Image.open(saved_file) as saved_image:
                        if saved_image.size == (800, 800):
                            return

                storage.delete(path)
                storage.save(path, ContentFile(output.read()))

    except Exception as error:
        print(f"Product image resizing failed: {error}")
