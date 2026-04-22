import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import scrape_all
import logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    print("Iniciando scraping de propiedades en Lima...")
    print("Esto puede tomar varios minutos. No cierres la terminal.")
    print("-" * 50)
    df = scrape_all()
    print("-" * 50)
    print(f"Scraping finalizado. Total de propiedades: {len(df)}")
    print(f"Archivo guardado en: data/raw/lima_properties_raw.csv")