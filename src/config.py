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
    "User-Agent" : (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" #navegador y sistema operativo
        "AppleWebKit/537.36 (KHTML, like Gecko) " 
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9", #idioma
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" #tipo de contenido que acepta el cliente
}

#Pausas entre los requests

MIN_DELAY = 2
MAX_DELAY = 5

#cARPETA DE SALIDA DE DATOS
RAW_DATA_PATH = "data/raw/"
