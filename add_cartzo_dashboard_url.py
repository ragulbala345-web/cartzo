from pathlib import Path
import re

url_file = Path("store/urls.py")

if not url_file.exists():
    print("ERROR: store/urls.py was not found. No URL changes were made.")
    raise SystemExit(1)

content = url_file.read_text(encoding="utf-8-sig")

if 'name="dashboard"' not in content and "name='dashboard'" not in content:
    if "from django.urls import" not in content:
        content = "from django.urls import path\n" + content
    elif not re.search(r"from django\.urls import .*?\bpath\b", content):
        content = re.sub(
            r"from django\.urls import ([^\n]+)",
            lambda m: m.group(0) + ", path",
            content,
            count=1,
        )

    if "from . import views" not in content:
        content += "\nfrom . import views\n"

    content += '\nurlpatterns += [path("dashboard/", views.dashboard, name="dashboard")]\n'
    url_file.write_text(content, encoding="utf-8")
    print("Dashboard URL added to store/urls.py")
else:
    print("Dashboard URL already exists; no duplicate added.")
