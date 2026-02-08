import json
import os
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "qianxin_apt_dump")
TARGET_URL = "https://ti.qianxin.com/apt/apt?type=map"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_json(name, data):
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[+] Saved {path}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context()
        page = context.new_page()

        responses = []

        def handle_response(response):
            try:
                if "application/json" in response.headers.get("content-type", ""):
                    url = response.url
                    data = response.json()
                    responses.append((url, data))
            except Exception:
                pass

        page.on("response", handle_response)

        print("[*] Loading APT map…")
        page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

        # Give late JS calls time to finish
        page.wait_for_timeout(5000)

        # Dump captured responses
        for i, (url, data) in enumerate(responses):
            safe_name = (
                url.replace("https://", "")
                .replace("/", "_")
                .replace("?", "_")
                .replace("=", "_")
            )
            save_json(f"{i:02d}_{safe_name}.json", data)

        # Try grabbing any global JS state objects
        state = page.evaluate(
            """
            () => {
                return {
                    vue_state: window.__INITIAL_STATE__ || null,
                    store: window.store || null,
                    app: window.__APP__ || null
                }
            }
        """
        )
        save_json("global_state.json", state)

        browser.close()

    print(f"[*] Done. Captured {len(responses)} API responses.")


if __name__ == "__main__":
    main()
