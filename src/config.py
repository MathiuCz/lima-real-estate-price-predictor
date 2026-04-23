DISTRICTS = [ 
    "miraflores",
    "san-isidro",
    "barranco",
    "la-molina",
    "surco",
    "san-borja",
    "jesus-maria",
    "magdalena-del-mar",
    "pueblo-libre",
    "san-miguel",
    "lince",
    "surquillo",
    "chorrillos",
    "los-olivos",
    "san-martin-de-porres",
    "san-juan-de-lurigancho",
    "la-victoria",
    "comas",
    "ate",
    "breña"
]

BASE_URL = "https://urbania.pe/buscar/venta-de-departamentos-en-{district}--lima--lima" #no repetimos URL 20 veces


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

#Pausas entre los requests

MIN_DELAY = 2
MAX_DELAY = 5

#cARPETA DE SALIDA DE DATOS
RAW_DATA_PATH = "data/raw/"

EDGE_DRIVER_PATH = "../drivers/msedgedriver.exe"