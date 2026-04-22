import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import logging
from datetime import datetime
from config import DISTRICTS, BASE_URL, HEADERS, MIN_DELAY, MAX_DELAY, RAW_DATA_PATH

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getlogger(__name__)

def get_page(url):
    try: 
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la solicitud a {url}: {e}")
        return None

def is_project(features_text):
    indicators = ["a","un.", " desde"]
    return any(indicator in features_text.lower() for indicator in indicators)

def get_listy_urls(district, page=1):
    url = BASE.URL.format(district=district) + f"?page={page}"
    logger.info(f"Scraping listado: {url}")
    soup = get_page(url)
    if not soup:
        return []
    
    urls = []
    cards = soup.find_all("div", {"data-qa" : "POSTING_CARD_FEATURES"})
    for card in cards:
        features_tag = card.find("h3", {"data-qa" : "POSTING_CARD_FEATURES"})
        if features_tag and is_project(features_tag.get_text()):
            continue
        link = card.find("a",href=True)
        if link:
            full_url = "https://urbania.pe" + link["href"]
            urls.append(full_url)
        
    return urls

def parse_features(soup):
    data = {
        "area_total": None,
        "area_built": None,
        "bedrooms": None,
        "bathrooms": None,
        "half_bathrooms": None,
        "parking_spaces": None,
        "age_years": None
    }
    
    features_list = soup.find("ul", {"id": "section-icon-features-property"})
    if not features_list:
        return data

    for item in features_list.find_all("li"):
        text = item.get_text(strip=True).lower()
        value = "".join(filter(str.isdigit, text))
        if not value:
            continue
        value = int(value)

        if "m² tot" in text:
            data["area_total"] = value
        elif "m² cub" in text:
            data["area_built"] = value
        elif "medios baños" in text:
            data["half_bathrooms"] = value
        elif "baños" in text:
            data["bathrooms"] = value
        elif "dorm" in text:
            data["bedrooms"] = value
        elif "estac" in text:
            data["parking_spaces"] = value
        elif "años" in text:
            data["age_years"] = value

    return data


def parse_amenities(soup):
    amenities = {
        "has_pool": False,
        "has_gym": False,
        "has_security": False,
        "has_elevator": False,
        "has_terrace": False,
        "has_grill": False,
        "has_laundry": False,
        "has_sea_view": False,
        "has_green_areas": False,
        "has_cowork": False,
    }

    containers = soup.find_all(
        "div",
        class_=lambda c: c and "generalFeaturesProperty-module__description-container" in c
    )

    all_text = " ".join(
        span.get_text(strip=True).lower()
        for container in containers
        for span in container.find_all("span")
    )

    amenities["has_pool"]        = "piscina" in all_text
    amenities["has_gym"]         = "gimnasio" in all_text
    amenities["has_security"]    = "seguridad" in all_text or "guardianía" in all_text
    amenities["has_elevator"]    = "ascensor" in all_text
    amenities["has_terrace"]     = "terraza" in all_text
    amenities["has_grill"]       = "parrilla" in all_text
    amenities["has_laundry"]     = "lavandería" in all_text
    amenities["has_sea_view"]    = "vista al mar" in all_text or "vista a la playa" in all_text
    amenities["has_green_areas"] = "área verde" in all_text or "areas verdes" in all_text
    amenities["has_cowork"]      = "cowork" in all_text or "co-work" in all_text

    return amenities


def parse_price(soup):
    data = {"price_pen": None, "price_usd": None, "maintenance_fee": None}

    price_tag = soup.find("h2", {"data-qa": "POSTING_CARD_PRICE"})
    if price_tag:
        price_text = price_tag.get_text(strip=True)
        if "S/" in price_text:
            pen = "".join(filter(str.isdigit, price_text.split("·")[0]))
            data["price_pen"] = int(pen) if pen else None
        if "USD" in price_text:
            usd = "".join(filter(str.isdigit, price_text.split("USD")[-1]))
            data["price_usd"] = int(usd) if usd else None

    maintenance_tag = soup.find("h2", {"data-qa": "expensas"})
    if maintenance_tag:
        maint = "".join(filter(str.isdigit, maintenance_tag.get_text()))
        data["maintenance_fee"] = int(maint) if maint else None

    return data


def parse_location(soup):
    data = {"address": None, "district": None, "urbanization": None}

    address_tag = soup.find("h4", class_=lambda c: c and "location-address" in c)
    if address_tag:
        data["address"] = address_tag.get_text(strip=True)

    location_tag = soup.find("h4", {"data-qa": "POSTING_CARD_LOCATION"})
    if location_tag:
        location_text = location_tag.get_text(strip=True)
        parts = location_text.split(",")
        if len(parts) >= 2:
            data["urbanization"] = parts[0].strip()
            data["district"] = parts[1].strip()
        else:
            data["district"] = location_text.strip()

    return data


def scrape_property(url):
    soup = get_page(url)
    if not soup:
        return None

    record = {"listing_url": url, "scraping_date": datetime.now().strftime("%Y-%m-%d")}

    title_tag = soup.find("h1", class_="title-property")
    record["title"] = title_tag.get_text(strip=True) if title_tag else None

    record.update(parse_features(soup))
    record.update(parse_amenities(soup))
    record.update(parse_price(soup))
    record.update(parse_location(soup))

    return record


def scrape_district(district, max_pages=10):
    logger.info(f"Iniciando scraping de distrito: {district}")
    all_records = []
    seen_urls = set()

    for page in range(1, max_pages + 1):
        urls = get_listing_urls(district, page)
        if not urls:
            logger.info(f"Sin resultados en página {page} de {district}. Fin.")
            break

        for url in urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            record = scrape_property(url)
            if record:
                record["district_scraped"] = district
                all_records.append(record)
                logger.info(f"Extraído: {url}")
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    logger.info(f"Distrito {district}: {len(all_records)} propiedades extraídas")
    return all_records


def scrape_all():
    all_data = []

    for district in DISTRICTS:
        records = scrape_district(district)
        all_data.extend(records)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        df_district = pd.DataFrame(records)
        df_district.to_csv(
            f"{RAW_DATA_PATH}{district}_{timestamp}.csv",
            index=False,
            encoding="utf-8-sig"
        )
        time.sleep(random.uniform(5, 10))

    df_final = pd.DataFrame(all_data)
    df_final.to_csv(
        f"{RAW_DATA_PATH}lima_properties_raw.csv",
        index=False,
        encoding="utf-8-sig"
    )
    logger.info(f"Scraping completo. Total registros: {len(df_final)}")
    return df_final

