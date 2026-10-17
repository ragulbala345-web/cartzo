from pathlib import Path

path = Path("cartzo/settings.py")
text = path.read_text(encoding="utf-8-sig")

if "from dotenv import load_dotenv" not in text:
    lines = text.splitlines()
    insert_at = 0

    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1

    lines.insert(insert_at, "from dotenv import load_dotenv")
    text = "\n".join(lines) + "\n"

if "load_dotenv()" not in text:
    lines = text.splitlines()
    insert_at = 0

    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1

    lines.insert(insert_at, "")
    lines.insert(insert_at + 1, "load_dotenv()")
    text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("Updated Django settings to load .env")
