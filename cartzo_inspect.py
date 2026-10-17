from pathlib import Path

files = [
    "accounts/urls.py",
    "accounts/models.py",
    "accounts/views.py",
    "cart/urls.py",
    "cart/models.py",
    "cart/views.py",
    "orders/urls.py",
    "orders/models.py",
    "orders/views.py",
    "api/urls.py",
    "api/views.py",
    "store/urls.py",
]

for name in files:
    path = Path(name)
    print("\n" + "=" * 70)
    print("FILE:", name)
    print("=" * 70)

    if path.exists():
        content = path.read_text(encoding="utf-8-sig")
        print(content[:5000])
    else:
        print("FILE NOT FOUND")
