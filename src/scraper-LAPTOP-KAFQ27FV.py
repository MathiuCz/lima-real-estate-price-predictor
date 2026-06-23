jimport pandas as pd
import time
import random
import json
import logging
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import (
    DISTRICTS, BASE_URL, MIN_DELAY, MAX_DELAY, RAW_DATA_PATH
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
]


def create_browser():
    p = sync_playwright().start()
    user_agent = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)

    browser = p.chromium.launch(
        headless=False,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ]
    )
    context = browser.new_context(
        user_agent=user_agent,
        viewport=viewport,
        locale="es-PE",
        timezone_id="America/Lima",
    )
    page = context.new_page()

    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    return p, browser, page


def resolve_cloudflare(page, max_wait=20):
    """Espera hasta que el challenge de Cloudflare desaparezca."""
    for i in range(max_wait):
        content = page.content()
        if "cf-browser-verification" not in content and "challenge-platform" not in content:
            if i > 0:
                logger.info(f"Challenge de Cloudflare resuelto en ~{i}s")
            return True
        if i == 0:
            logger.info("Cloudflare detectado, esperando resolución...")
        time.sleep(1)
    logger.warning(f"Cloudflare no se resolvió después de {max_wait}s")
    return False


def get_page(page, url):
    try:
        page.goto(url, wait_until="load", timeout=60000)
        resolve_cloudflare(page)
        page.wait_for_selector("[data-posting-type]", timeout=15000)
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        return BeautifulSoup(page.content(), "lxml")
    except Exception as e:
        logger.error(f"Error al obtener {url}: {e}")
        return None


def parse_price_from_card(card):
    data = {"price_pen": None, "price_usd": None, "maintenance_fee": None}

    price_tag = card.find("h2", {"data-qa": "POSTING_CARD_PRICE"})
    if price_tag:
        text = price_tag.get_text(strip=True)
        parts = text.split("·")
        for part in parts:
            part = part.strip()
            digits = "".join(c for c in part if c.isascii() and c.isdigit())
            if not digits:
                continue
            if "S/" in part:
                data["price_pen"] = int(digits)
            elif "USD" in part:
                data["price_usd"] = int(digits)

    maint_tag = card.find("h2", {"data-qa": "expensas"})
    if maint_tag:
        text = maint_tag.get_text(strip=True)
        digits = "".join(c for c in text if c.isascii() and c.isdigit())
        data["maintenance_fee"] = int(digits) if digits else None

    return data


def parse_features_from_card(card):
    data = {
        "area_total": None,
        "bedrooms": None,
        "bathrooms": None,
        "parking_spaces": None,
    }

    features_tag = card.find("h3", {"data-qa": "POSTING_CARD_FEATURES"})
    if not features_tag:
        return data

    spans = features_tag.find_all("span")
    for span in spans:
        text = span.get_text(strip=True).lower()
        digits = "".join(c for c in text if c.isascii() and c.isdigit())
        if not digits:
            continue
        value = int(digits)
        if "m²" in text or "m2" in text:
            data["area_total"] = value
        elif "dorm" in text:
            data["bedrooms"] = value
        elif "baño" in text:
            data["bathrooms"] = value
        elif "estac" in text:
            data["parking_spaces"] = value

    return data


def parse_location_from_card(card):
    data = {"address": None, "district": None, "urbanization": None}

    address_tag = card.find(
        "h4", class_=lambda c: c and "location-address" in c
    )
    if address_tag:
        data["address"] = address_tag.get_text(strip=True)

    location_tag = card.find("h4", {"data-qa": "POSTING_CARD_LOCATION"})
    if location_tag:
        text = location_tag.get_text(strip=True)
        parts = text.split(",")
        if len(parts) >= 2:
            data["urbanization"] = parts[0].strip()
            data["district"] = parts[1].strip()
        else:
            data["district"] = text.strip()

    return data


def parse_photos_count(card):
    gallery = card.find("div", {"data-qa": "POSTING_CARD_GALLERY"})
    if not gallery:
        return None
    imgs = gallery.find_all("img")
    return len(imgs)


def parse_json_ld(card):
    script = card.find("script", {"type": "application/ld+json"})
    if not script:
        return {}
    try:
        data = json.loads(script.string)
        return {"json_name": data.get("name", None)}
    except Exception:
        return {}


def is_project(card):
    posting_type = card.get("data-posting-type", "")
    if posting_type == "DEVELOPMENT":
        return True
    features_tag = card.find("h3", {"data-qa": "POSTING_CARD_FEATURES"})
    if features_tag:
        text = features_tag.get_text().lower()
        if " a " in text or "un." in text or "desde" in text:
            return True
    return False


def parse_card(card, district):
    record = {
        "listing_id": card.get("data-id"),
        "listing_url": "https://urbania.pe" + card.get("data-to-posting", ""),
        "scraping_date": datetime.now().strftime("%Y-%m-%d"),
        "district_scraped": district,
        "source": "urbania",
    }

    record.update(parse_price_from_card(card))
    record.update(parse_features_from_card(card))
    record.update(parse_location_from_card(card))
    record["photos_count"] = parse_photos_count(card)
    record.update(parse_json_ld(card))

    return record


def scrape_district(page, district, max_pages=10):
    logger.info(f"Iniciando scraping de distrito: {district}")
    all_records = []
    seen_ids = set()

    for page_num in range(1, max_pages + 1):
        url = BASE_URL.format(district=district) + f"?page={page_num}"
        logger.info(f"Scraping listado: {url}")
        soup = get_page(page, url)

        if not soup:
            logger.info(f"Sin respuesta en página {page_num} de {district}. Fin.")
            break

        cards = soup.find_all("div", attrs={"data-posting-type": True})

        if not cards:
            logger.info(f"Sin tarjetas en página {page_num} de {district}. Fin.")
            break

        new_cards = 0
        for card in cards:
            if is_project(card):
                continue
            listing_id = card.get("data-id")
            if listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)
            record = parse_card(card, district)
            all_records.append(record)
            new_cards += 1
            logger.info(f"Extraído ID: {listing_id}")

        logger.info(f"Página {page_num}: {new_cards} propiedades nuevas")

        if page_num < max_pages:
            pause = random.uniform(8, 15)
            logger.info(f"Esperando {pause:.1f}s antes de siguiente página...")
            time.sleep(pause)

    logger.info(f"Distrito {district}: {len(all_records)} propiedades extraídas")
    return all_records


def scrape_all():
    all_data = []
    os.makedirs(RAW_DATA_PATH, exist_ok=True)

    playwright_obj, browser, page = create_browser()

    try:
        logger.info("Iniciando sesión en Urbania...")
        page.goto("https://urbania.pe", wait_until="load", timeout=60000)
        resolve_cloudflare(page)
        time.sleep(random.uniform(4, 7))

        for i, district in enumerate(DISTRICTS):
            records = scrape_district(page, district)
            all_data.extend(records)

            if records:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                df_district = pd.DataFrame(records)
                csv_path = os.path.join(
                    RAW_DATA_PATH, f"{district}_{timestamp}.csv"
                )
                df_district.to_csv(csv_path, index=False, encoding="utf-8-sig")
                logger.info(f"Guardado: {csv_path}")

            if i < len(DISTRICTS) - 1:
                pause = random.uniform(15, 25)
                logger.info(f"Pausa entre distritos: {pause:.1f}s")
                page.goto("https://urbania.pe", wait_until="load", timeout=60000)
                time.sleep(pause)

    finally:
        browser.close()
        playwright_obj.stop()

    df_final = pd.DataFrame(all_data)
    final_path = os.path.join(RAW_DATA_PATH, "lima_properties_raw.csv")
    df_final.to_csv(final_path, index=False, encoding="utf-8-sig")
    logger.info(f"Scraping completo. Total registros: {len(df_final)}")
    return df_final


if __name__ == "__main__":
    scrape_all()
