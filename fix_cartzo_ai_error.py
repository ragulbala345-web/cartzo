from pathlib import Path

path = Path("store/ai_views.py")
text = path.read_text(encoding="utf-8-sig")

old = '''    except Exception:
        return JsonResponse(
            {
                "reply": (
                    "Sorry, I could not connect to the AI service. "
                    "Please check the API key, API access, and account usage limits."
                )
            },
            status=502,
        )
'''

new = '''    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Cartzo AI request failed")
        return JsonResponse(
            {"reply": "The AI request failed. Check your VS Code terminal for the error details."},
            status=502,
        )
'''

if old not in text:
    print("Could not find the expected error-handling section. No changes made.")
else:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("Updated chatbot error reporting successfully.")
