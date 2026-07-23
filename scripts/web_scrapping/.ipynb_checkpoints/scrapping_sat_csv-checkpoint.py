import os
import time
import random
import shutil
import logging
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://www.mineduc.gob.gt/BUSCAESTABLECIMIENTO_GE/"
OUTPUT_DIR = Path("data/paginas_departamentos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR = Path("data/debug_respuestas")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
CONSOLIDADO_PATH = Path("data/raw/consolidado_diversificado.csv")


NIVEL_DIVERSIFICADO_VALUE = "46"

DEPARTAMENTOS = {
    "16": "ALTA VERAPAZ", "15": "BAJA VERAPAZ", "04": "CHIMALTENANGO",
    "20": "CHIQUIMULA", "00": "CIUDAD CAPITAL", "02": "EL PROGRESO",
    "05": "ESCUINTLA", "01": "GUATEMALA", "13": "HUEHUETENANGO",
    "18": "IZABAL", "21": "JALAPA", "22": "JUTIAPA", "17": "PETEN",
    "09": "QUETZALTENANGO", "14": "QUICHE", "11": "RETALHULEU",
    "03": "SACATEPEQUEZ", "12": "SAN MARCOS", "06": "SANTA ROSA",
    "07": "SOLOLA", "10": "SUCHITEPEQUEZ", "08": "TOTONICAPAN", "19": "ZACAPA",
}

ID_DEPARTAMENTO = "_ctl0_ContentPlaceHolder1_cmbDepartamento"
ID_NIVEL = "_ctl0_ContentPlaceHolder1_cmbNivel"
ID_SECTOR = "_ctl0_ContentPlaceHolder1_cmbSector"
ID_BUSCAR = "_ctl0_ContentPlaceHolder1_IbtnConsultar"
ID_TABLA_RESULTADOS = "_ctl0_ContentPlaceHolder1_dgResultado"
ID_RESUMEN = "_ctl0_ContentPlaceHolder1_lblPie1"

COLUMNAS = [
    "CODIGO", "DISTRITO", "DEPARTAMENTO", "MUNICIPIO", "ESTABLECIMIENTO",
    "DIRECCION", "TELEFONO", "SUPERVISOR", "DIRECTOR", "NIVEL", "SECTOR",
    "AREA", "STATUS", "MODALIDAD", "JORNADA", "PLAN", "DEPARTAMENTAL",
]

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=es-GT")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # En NixOS no usamos webdriver-manager (falla con exit code 127 porque los
    # binarios genéricos que descarga no resuelven libs dinámicas fuera de FHS).
    # En su lugar, usamos chromium/chromedriver del entorno (nix develop / nix-shell),
    # expuestos vía las variables CHROMIUM_BIN / CHROMEDRIVER_BIN o el PATH.
    chromium_binary = (
        os.environ.get("CHROMIUM_BIN")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
    )
    chromedriver_binary = os.environ.get("CHROMEDRIVER_BIN") or shutil.which("chromedriver")

    if not chromium_binary or not os.path.exists(chromium_binary):
        raise RuntimeError(
            "No se encontró el binario de Chromium. "
        )
    if not chromedriver_binary or not os.path.exists(chromedriver_binary):
        raise RuntimeError(
            "No se encontró chromedriver. "
        )

    log.info("Usando chromium: %s", chromium_binary)
    log.info("Usando chromedriver: %s", chromedriver_binary)

    options.binary_location = chromium_binary
    service = Service(executable_path=chromedriver_binary)
    driver = webdriver.Chrome(service=service, options=options)

    # Enmascarar navigator.webdriver antes de que corra cualquier script de la página
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def esperar_carga_completa(driver, timeout=25):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def seleccionar_departamento(driver, dept_code, timeout=25):
    """Selecciona el departamento en el combo; esto dispara el postback (onchange)
    y la página se recarga por completo."""
    select_el = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.ID, ID_DEPARTAMENTO))
    )
    Select(select_el).select_by_value(dept_code)

    # Esperar a que el postback termine: el elemento viejo queda "stale"
    # y luego a que el combo recargado tenga el valor correcto seleccionado.
    WebDriverWait(driver, timeout).until(EC.staleness_of(select_el))
    esperar_carga_completa(driver, timeout)

    WebDriverWait(driver, timeout).until(
        lambda d: Select(d.find_element(By.ID, ID_DEPARTAMENTO))
        .first_selected_option.get_attribute("value") == dept_code
    )


def configurar_filtros_y_buscar(driver, timeout=25):
    nivel_el = driver.find_element(By.ID, ID_NIVEL)
    Select(nivel_el).select_by_value(NIVEL_DIVERSIFICADO_VALUE)

    sector_el = driver.find_element(By.ID, ID_SECTOR)
    Select(sector_el).select_by_value("TODOS")

    resumen_anterior = None
    resumen_els = driver.find_elements(By.ID, ID_RESUMEN)
    if resumen_els:
        resumen_anterior = resumen_els[0].text

    buscar_btn = driver.find_element(By.ID, ID_BUSCAR)
    buscar_btn.click()

    esperar_carga_completa(driver, timeout)

    # Esperar a que el resumen ("N Establecimientos encontrados") cambie o aparezca
    WebDriverWait(driver, timeout).until(
        lambda d: d.find_elements(By.ID, ID_RESUMEN)
        and d.find_element(By.ID, ID_RESUMEN).text != resumen_anterior
        and "Establecimiento" in d.find_element(By.ID, ID_RESUMEN).text
    )


def parsear_tabla_resultados(html: str):
    soup = BeautifulSoup(html, "html.parser")
    tabla = soup.find(id=ID_TABLA_RESULTADOS)
    if tabla is None:
        return None

    filas = tabla.find_all("tr")
    registros = []
    for fila in filas[1:]:  # la primera fila es encabezado
        celdas = fila.find_all("td")
        if len(celdas) < len(COLUMNAS) + 1:
            continue
        # la celda 0 es el ícono/link "Escoger este establecimiento"
        valores = [c.get_text(strip=True) for c in celdas[1:len(COLUMNAS) + 1]]
        codigo = valores[0].replace("\xa0", "").strip()
        if not codigo:
            continue  # fila vacía de relleno
        registros.append(valores)

    if not registros:
        return None
    return pd.DataFrame(registros, columns=COLUMNAS)


def procesar_departamento(driver, dept_code, dept_nombre, timeout=25):
    driver.get(BASE_URL)
    esperar_carga_completa(driver, timeout)

    seleccionar_departamento(driver, dept_code, timeout)
    configurar_filtros_y_buscar(driver, timeout)

    html = driver.page_source

    out_path = OUTPUT_DIR / f"{dept_code}_{dept_nombre.replace(' ', '_')}.html"
    out_path.write_text(html, encoding="utf-8")

    resumen_el = driver.find_elements(By.ID, ID_RESUMEN)
    if resumen_el:
        log.info("%s: %s", dept_nombre, resumen_el[0].text)

    df = parsear_tabla_resultados(html)
    if df is None:
        log.warning("%s: no se pudo extraer la tabla de resultados", dept_nombre)
        (DEBUG_DIR / f"sin_tabla_{dept_code}.html").write_text(html, encoding="utf-8")
        return None

    df["__DEPTO_CODE"] = dept_code
    return df


driver = build_driver(headless=True)
dfs = []
try:
    for dept_code, dept_nombre in DEPARTAMENTOS.items():
        for intento in range(1, 3):  # hasta 2 intentos por departamento
            try:
                df = procesar_departamento(driver, dept_code, dept_nombre)
                if df is not None:
                    dfs.append(df)
                break
            except (TimeoutException, StaleElementReferenceException) as e:
                log.warning("%s intento %d falló: %s", dept_nombre, intento, e)
                time.sleep(3)
        else:
            log.error("%s: se agotaron los intentos", dept_nombre)

        time.sleep(random.uniform(2.5, 5.0))  # pausa entre departamentos
finally:
    driver.quit()

if not dfs:
    log.error("No se extrajo ningún dato; no se generó el consolidado.")

consolidado = pd.concat(dfs, ignore_index=True)
consolidado.to_csv(CONSOLIDADO_PATH, index=False)
log.info("Consolidado final: %s (%d filas)", CONSOLIDADO_PATH, len(consolidado))



