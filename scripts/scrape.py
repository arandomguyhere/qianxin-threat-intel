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

        print(f"[*] Captured {len(responses)} API responses from page load.")

        # ─── Fetch actor detail pages for full data ──────────
        # The actor/all endpoint only returns name+alias. Detail data
        # (country, TTPs, targets, malware) comes from per-actor API calls.
        actor_ids = []
        for url, data in responses:
            if "actor" in url and "all" in url:
                payload = data.get("data", data)
                if isinstance(payload, list):
                    for record in payload:
                        if isinstance(record, dict) and "name" in record:
                            actor_ids.append({
                                "id": record["name"],
                                "actorName": record.get("actorName", record["name"]),
                            })

        if actor_ids:
            print(f"[*] Fetching detail for {len(actor_ids)} actors...")
            detail_results = []

            for idx, actor in enumerate(actor_ids):
                aid = actor["id"]
                aname = actor["actorName"]
                # Try known QiAnxin detail endpoint patterns
                detail = page.evaluate(
                    """
                    async (actorId) => {
                        const urls = [
                            `/alpha-api/v2/apt-dossier/actor/${actorId}?lang=en-US&source=apt`,
                            `/alpha-api/v2/apt-dossier/actor/detail?name=${actorId}&lang=en-US&source=apt`,
                            `/alpha-api/v2/apt-dossier/actor/info?name=${actorId}&lang=en-US&source=apt`,
                        ];
                        for (const url of urls) {
                            try {
                                const resp = await fetch(url);
                                if (resp.ok) {
                                    const json = await resp.json();
                                    if (json && json.status !== undefined) {
                                        return { url: url, data: json, ok: true };
                                    }
                                }
                            } catch (e) {}
                        }
                        return { ok: false };
                    }
                    """,
                    aid,
                )

                if detail and detail.get("ok"):
                    safe_name = aname.replace(" ", "_").replace("/", "_").replace(".", "")
                    save_json(f"actor_{safe_name}.json", detail["data"])
                    detail_results.append(detail)
                    if idx == 0:
                        print(f"[+] Detail endpoint found: {detail.get('url', '?')}")
                elif idx == 0:
                    # First actor failed - try clicking in the UI to discover the endpoint
                    print(f"[!] Direct fetch failed for {aname}, trying UI click...")
                    pre_count = len(responses)
                    try:
                        # Try clicking on a map marker or sidebar item
                        actor_el = page.locator(f'text="{aname}"').first
                        if actor_el.is_visible(timeout=3000):
                            actor_el.click()
                            page.wait_for_timeout(3000)
                            # Check if new API calls were captured
                            if len(responses) > pre_count:
                                new_urls = [r[0] for r in responses[pre_count:]]
                                print(f"[+] Click triggered {len(new_urls)} new API calls:")
                                for u in new_urls:
                                    print(f"    {u}")
                    except Exception as e:
                        print(f"[!] Click approach also failed: {e}")
                    break  # Don't spam if endpoint doesn't exist

                if (idx + 1) % 10 == 0:
                    print(f"    ... {idx + 1}/{len(actor_ids)} actors fetched")

            print(f"[*] Fetched detail for {len(detail_results)} actors")

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

    total = len(responses)
    print(f"[*] Done. Captured {total} API responses total.")


if __name__ == "__main__":
    main()
