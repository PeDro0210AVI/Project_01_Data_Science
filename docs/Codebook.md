# Codebook
## Establecimientos de Nivel Diversificado — Guatemala

**Proyecto:** Project_01_Data_Science
Fuente de los datos: MINEDUC — Buscador de Establecimientos ([http://www.mineduc.gob.gt/BUSCAESTABLECIMIENTO_GE/](http://www.mineduc.gob.gt/BUSCAESTABLECIMIENTO_GE/))
Método de obtencion: Web scraping por departamento (22 páginas HTML) con scripts/web_scrapping/scrapping_sat_csv.py, consolidado en data/raw/consolidado_diversificado.csv
Fecha de extraccion: 2026-07-21
**Notebook de limpieza:** `notebooks/data_cleaning.ipynb`
Archivo limpio final: `data/clean/establecimientos_diversificado_limpio.csv`

---

## 1. Resumen del pipeline

1. Extracción (scraping): `scripts/web_scrapping/scrapping_sat_csv.py` recorre las 22 páginas HTML de departamentos guardadas en `data/paginas_departamentos/` y consolida los establecimientos de nivel DIVERSIFICADO en `data/raw/consolidado_diversificado.csv`.
2. Diagnóstico: conteo de registros/variables, tipos de dato, faltantes, valores únicos, duplicados exactos, valores fuera de dominio y formatos inconsistentes (`notebooks/data_cleaning.ipynb`, secciones 3.a–3.h).
3. Plan de limpieza: tabla variable por variable con problema, regla de corrección, justificación y riesgos, documentada antes de tocar los datos.
4. Implementación: normalización de texto, unificación de categorías, tipado correcto, separación de teléfonos, marcado (no eliminación) de duplicados.
5. Validación automática: batería de pruebas (assert) sobre el conjunto limpio.
6. Exportación: tres archivos en data/clean/:
   - `establecimientos_diversificado_limpio.csv` — datos limpios
   - `registro_transformaciones.csv` — log de cada transformación aplicada
   - `informe_calidad_antes_despues.csv` — métricas de calidad antes/después

---

## 2. Variables originales (crudo -> limpio)

| # | Variable (cruda) | Tipo pandas crudo | Variable en el limpio | Tipo final | Descripción | Dominio / formato |
|---|---|---|---|---|---|---|
| 1 | `CODIGO` | object | `CODIGO` | texto | Identificador único del establecimiento | `XX-XX-XXXX-XX` (100% de filas cumple el formato) |
| 2 | `DISTRITO` | object | `DISTRITO` | texto | Código del distrito escolar de supervisión | Dos esquemas válidos coexisten: `XX-XXX` y `XX-XX-XXXX`; códigos truncados → NA |
| 3 | `DEPARTAMENTO` | object | `DEPARTAMENTO` | category | Departamento del establecimiento | 22 departamentos oficiales de Guatemala (ver §3) |
| 4 | `MUNICIPIO` | object | `MUNICIPIO` | category | Municipio del establecimiento | 330 municipios observados tras la limpieza |
| 5 | `ESTABLECIMIENTO` | object | `ESTABLECIMIENTO` | texto | Nombre del establecimiento educativo | Texto libre, espacios normalizados |
| 6 | `DIRECCION` | object | `DIRECCION` | texto | Dirección física | Texto libre; centinelas (`"--"`, `"."`) → NA |
| 7 | `TELEFONO` | object | *(eliminada, ver §4)* | — | Teléfono(s) de contacto en un solo campo, formato heterogéneo | Reemplazada por `TELEFONO_PRINCIPAL`, `TELEFONO_SECUNDARIO`, `TELEFONO_VALIDO` |
| 8 | `SUPERVISOR` | object | `SUPERVISOR` | texto | Nombre del supervisor educativo | Texto libre, espacios normalizados |
| 9 | `DIRECTOR` | object | `DIRECTOR` | texto | Nombre del director del establecimiento | Texto libre; ~14.6% NA reales + centinelas → NA |
| 10 | `NIVEL` | object | `NIVEL` | category | Nivel educativo | Constante: `"DIVERSIFICADO"` (100% de filas, define el alcance del dataset) |
| 11 | `SECTOR` | object | `SECTOR` | category | Sector administrativo | `OFICIAL`, `PRIVADO`, `MUNICIPAL`, `COOPERATIVA` |
| 12 | `AREA` | object | `AREA` | category | Área geográfica | `URBANA`, `RURAL`, `SIN ESPECIFICAR` |
| 13 | `STATUS` | object | `STATUS` | category | Estado operativo del establecimiento | `ABIERTA`, `CERRADA DEFINITIVAMENTE`, `CERRADA TEMPORALMENTE`, `TEMPORAL NOMBRAMIENTO`, `TEMPORAL TITULOS` |
| 14 | `MODALIDAD` | object | `MODALIDAD` | category | Modalidad de enseñanza | `MONOLINGUE`, `BILINGUE` |
| 15 | `JORNADA` | object | `JORNADA` | category | Jornada / turno | `MATUTINA`, `VESPERTINA`, `NOCTURNA`, `INTERMEDIA`, `DOBLE`, `SIN JORNADA` |
| 16 | `PLAN` | object | `PLAN` | category | Plan de estudios | `DIARIO(REGULAR)`, `SABATINO`, `DOMINICAL`, `FIN DE SEMANA`, `A DISTANCIA`, `VIRTUAL A DISTANCIA`, `SEMIPRESENCIAL` (y variantes), `INTERCALADO`, `IRREGULAR`, `MIXTO` |
| 17 | `DEPARTAMENTAL` | object | `DEPARTAMENTAL` | category | Departamento según el sitio de origen (con tildes; subdivide Guatemala en zonas de supervisión) | Variable auxiliar/redundante — **no usar para invalidar `DEPARTAMENTO`** |
| 18 | `__DEPTO_CODE` | int64 | `COD_DEPARTAMENTO_ORIGEN` | texto (2 dígitos) | Código numérico de departamento tal como lo usó el formulario del scraper | `"01"`–`"22"`, con cero a la izquierda preservado |

---

## 3. Variables derivadas (creadas durante la limpieza)

| Variable | Tipo | Descripción | Regla de generación | Cobertura |
|---|---|---|---|---|
| `ZONA_CIUDAD_GUATEMALA` | texto (dígitos) | Número de zona de la ciudad de Guatemala, cuando aplica | Extraída de `MUNICIPIO` cuando el valor original era `"ZONA n"` (antes clasificado bajo el pseudo-departamento `"CIUDAD CAPITAL"`) | Solo establecimientos de la ciudad de Guatemala (9,707 NA / 11,868) |
| `TELEFONO_PRINCIPAL` | texto (7–8 dígitos) | Primer número telefónico válido extraído del campo original `TELEFONO` | Regex `\d{7,8}` sobre el campo crudo; primera coincidencia | 973 NA |
| `TELEFONO_SECUNDARIO` | texto (dígitos, separados por `;`) | Número(s) telefónicos adicionales, cuando el campo original traía más de uno | Coincidencias adicionales del mismo regex | 11,698 NA (solo aplica a registros con 2+ números) |
| `TELEFONO_VALIDO` | booleano | `True` si `TELEFONO_PRINCIPAL` tiene exactamente 8 dígitos (formato guatemalteco vigente) | `len(TELEFONO_PRINCIPAL) == 8` | Sin NA |
| `DUPLICADO_EXACTO_SIN_CODIGO` | booleano | `True` si la fila es idéntica a otra en todas las columnas excepto `CODIGO` | `duplicated(subset=todas menos CODIGO, keep=False)` | Sin NA — **no se elimina automáticamente, requiere revisión manual** |
| `POSIBLE_DUPLICADO_PARCIAL` | booleano | `True` si el nombre del establecimiento es muy similar (≥0.90) al de otro dentro del mismo departamento/municipio | `difflib.SequenceMatcher` sobre nombre normalizado (sin tildes/mayúsculas), agrupado por `DEPARTAMENTO`+`MUNICIPIO` | Sin NA — **no se fusiona automáticamente, requiere revisión manual** |

---

## 4. Transformaciones aplicadas por variable

| Variable | Problema detectado | Transformación aplicada | Justificación | Riesgo documentado |
|---|---|---|---|---|
| `CODIGO` | Ninguno relevante (formato consistente en 100%) | Se mantiene como texto (no numérico) | Evita perder ceros a la izquierda | Ninguno |
| `DISTRITO` | Dos esquemas de código (`XX-XXX` vs `XX-XX-XXXX`) + ~70 códigos truncados (`"01-"`) | Truncados → NA; los dos formatos válidos se conservan tal cual | Un código incompleto no identifica un distrito real; inventar el segmento sería fabricar datos | Se pierde el dato en ~70 filas (0.6%) en vez de adivinarlo |
| `DEPARTAMENTO` | 23 categorías en vez de 22 oficiales; `"CIUDAD CAPITAL"` no es un departamento | `"CIUDAD CAPITAL"` → `"GUATEMALA"` | Catálogo oficial (INE/MINEDUC) tiene 22 departamentos | Se pierde la distinción capital/resto; mitigado con `COD_DEPARTAMENTO_ORIGEN` |
| `MUNICIPIO` | Para ex-`CIUDAD CAPITAL`, traía zona (`"ZONA 1"`) en vez de municipio | `MUNICIPIO = "GUATEMALA"` + nueva variable `ZONA_CIUDAD_GUATEMALA` | El municipio real es Guatemala; la zona se preserva como dato derivado | Si se necesitara zona para todos los municipios, la variable queda mayormente vacía |
| `ESTABLECIMIENTO` | Espacios dobles/múltiples; ~5 NA; posibles duplicados parciales de nombre | Normalización de espacios; similitud de cadenas para *marcar* (no fusionar) | Los espacios no aportan información; nombres con comillas son válidos en español | Umbral bajo generaría falsos positivos en nombres genéricos |
| `DIRECCION` | Espacios múltiples; centinelas (`"--"`, `"."`) | Normalización de espacios; centinelas → NA | Una dirección `"--"` no es una dirección real | Se pierde el matiz "no se sabe" vs "no existe" |
| `TELEFONO` | Longitudes heterogéneas (2–30 caracteres), varios números en un campo, texto mezclado (`"FAX"`, `"Y"`, `"AL"`) | Extracción por regex de secuencias de 7–8 dígitos → `TELEFONO_PRINCIPAL`, `TELEFONO_SECUNDARIO`, `TELEFONO_VALIDO`; columna original eliminada | Un teléfono guatemalteco válido tiene 8 dígitos; separar evita perder contactos adicionales | Números de 7 dígitos (formato antiguo) quedan marcados como no válidos |
| `SUPERVISOR` / `DIRECTOR` | Espacios múltiples; `DIRECTOR` con ~14.6% NA reales + centinelas | Normalización de espacios; centinelas → NA | Mismo criterio que `DIRECCION` | Ninguno significativo |
| `NIVEL` | Constante (`"DIVERSIFICADO"`) | Tipado como `category`; se conserva | Documenta el alcance del dataset | Ninguno |
| `SECTOR`, `AREA`, `STATUS`, `MODALIDAD`, `JORNADA`, `PLAN` | Vocabularios pequeños, ya consistentes | Tipado como `category`; verificación de variantes may/min o espacios | Cardinalidad baja y consistente en la fuente | Ninguno significativo |
| `DEPARTAMENTAL` | Redundante con `DEPARTAMENTO`, difiere en 6,095 filas (tildes + subdivisión por zonas en Guatemala) | Se conserva como variable auxiliar documentada, sin usarla para invalidar `DEPARTAMENTO` | Contiene información útil (zona de supervisión) | Puede interpretarse erróneamente como el nombre "correcto" del departamento |
| `__DEPTO_CODE` | Tipo entero para un código categórico (pierde cero a la izquierda) | Renombrado a `COD_DEPARTAMENTO_ORIGEN`; convertido a texto de 2 dígitos | Es un identificador, no una cantidad | Ninguno |
| Toda columna de texto | Espacios NBSP, caracteres de control invisibles, espacios dobles/bordes | `strip()` + colapso de espacios + remoción de caracteres de control | Uniformiza texto para comparaciones/joins | Ninguno |
| Toda columna de texto | Valores centinela de faltante escritos como texto (`"--"`, `"---"`, `"."`, `"SIN DATO"`, `"N/A"`, etc.) | Reemplazo por `NA` real (vía regex `PLACEHOLDER_RE`) | Estos tokens no son datos válidos | Ninguno |
| (fila completa) | 181–385 filas idénticas en todo excepto `CODIGO` | Se marcan con `DUPLICADO_EXACTO_SIN_CODIGO = True`, **no se eliminan** | Podría ser el mismo establecimiento con dos códigos administrativos vigentes | Eliminar sin revisar podría borrar oferta educativa real distinta |
| (fila completa) | Nombres de establecimiento muy similares dentro del mismo depto/municipio | Similitud de cadenas (umbral 0.90); se marcan con `POSIBLE_DUPLICADO_PARCIAL = True`, **no se fusionan** | Permite detectar variantes de escritura sin catálogo externo | Nombres institucionales genéricos generan coincidencias que no son duplicados reales |

> El detalle fila por fila de cada transformación (con conteo exacto de registros afectados) está en `data/clean/registro_transformaciones.csv`.

---

## 5. Catálogo de dominios controlados

DEPARTAMENTO (22 valores oficiales):
ALTA VERAPAZ, BAJA VERAPAZ, CHIMALTENANGO, CHIQUIMULA, EL PROGRESO, ESCUINTLA, GUATEMALA, HUEHUETENANGO, IZABAL, JALAPA, JUTIAPA, PETEN, QUETZALTENANGO, QUICHE, RETALHULEU, SACATEPEQUEZ, SAN MARCOS, SANTA ROSA, SOLOLA, SUCHITEPEQUEZ, TOTONICAPAN, ZACAPA

SECTOR: COOPERATIVA, MUNICIPAL, OFICIAL, PRIVADO

AREA: RURAL, URBANA, SIN ESPECIFICAR

STATUS: ABIERTA, CERRADA DEFINITIVAMENTE, CERRADA TEMPORALMENTE, TEMPORAL NOMBRAMIENTO, TEMPORAL TITULOS

MODALIDAD: BILINGUE, MONOLINGUE

JORNADA: DOBLE, INTERMEDIA, MATUTINA, NOCTURNA, SIN JORNADA, VESPERTINA

`PLAN`:** A DISTANCIA, DIARIO(REGULAR), DOMINICAL, FIN DE SEMANA, INTERCALADO, IRREGULAR, MIXTO, SABATINO, SEMIPRESENCIAL, SEMIPRESENCIAL (DOS DÍAS A LA SEMANA), SEMIPRESENCIAL (FIN DE SEMANA), SEMIPRESENCIAL (UN DÍA A LA SEMANA), VIRTUAL A DISTANCIA

**`MUNICIPIO`:** sin catálogo oficial embebido en el proyecto (330 valores observados tras la limpieza). Se validó ausencia de errores tipográficos mediante similitud de cadenas (>0.85) dentro de cada departamento; no se encontraron variantes, salvo el caso ya corregido de `"ZONA n"`. **Limitación conocida:** el catálogo de referencia es el conjunto de valores observados, no una fuente oficial externa.

---

## 6. Validaciones automáticas aplicadas al conjunto limpio

- CODIGO es único (sin duplicados exactos por identificador).
- Ninguna columna de texto tiene espacios al inicio/fin.
- TELEFONO_PRINCIPAL contiene solo 7–8 dígitos numéricos (o NA).
- DEPARTAMENTO tiene exactamente los 22 departamentos oficiales.
- MUNICIPIO ya no contiene valores tipo "ZONA n".
- Todas las variables categóricas están tipadas como category.
- COD_DEPARTAMENTO_ORIGEN es texto de 2 dígitos.
- No hay categorias duplicadas por diferencias de mayúsculas/minúsculas o espacios en las variables de dominio controlado.

---

## 7. Informe de calidad — antes vs. despues

| Metrica | Antes | Despues |
|---|---|---|
| Registros | 11,868 | 11,868 |
| Variables | 18 | 23 |
| Variables con formato inconsistente corregido | 3 | 0 |
| Variables con tipo incorrecto corregido | 2 | 0 |
| Categorías inconsistentes unificadas | 1 | 0 |
| Duplicados exactos (fila completa) | 0 | 0 (por unicidad de `CODIGO`) |
| Duplicados exactos excluyendo `CODIGO` | ver `informe_calidad_antes_despues.csv` | marcados en `DUPLICADO_EXACTO_SIN_CODIGO`, no eliminados |
| Posibles duplicados parciales (nombre similar) | no evaluado | marcados en `POSIBLE_DUPLICADO_PARCIAL`, no fusionados |

Nota sobre el aumento de valores faltantes tras la limpieza: el número de celdas NA sube, no porque se pierda información, sino porque (1) se destaparon faltantes disfrazados como texto (`"--"`, `"SIN DATO"`) que antes contaban como "presentes", y (2) se crearon variables derivadas inherentemente dispersas (`ZONA_CIUDAD_GUATEMALA`, `TELEFONO_SECUNDARIO`). El dato real disponible no disminuyó: se volvió más honesto y granular. El detalle numérico completo está en `data/clean/informe_calidad_antes_despues.csv`.

---

## 8. Advertencia sobre tipos de dato al releer el CSV

CSV es texto plano y no conserva el `dtype` de pandas. Al releer `establecimientos_diversificado_limpio.csv`, las siguientes columnas pueden inferirse erróneamente como numéricas (perdiendo ceros a la izquierda) si no se fuerza el tipo:

```python
DTYPE_AL_RELEER = {
    "CODIGO": str,
    "DISTRITO": str,
    "COD_DEPARTAMENTO_ORIGEN": str,
    "ZONA_CIUDAD_GUATEMALA": str,
    "TELEFONO_PRINCIPAL": str,
    "TELEFONO_SECUNDARIO": str,
}
df = pd.read_csv("establecimientos_diversificado_limpio.csv", dtype=DTYPE_AL_RELEER, encoding="utf-8")
```

Esto **no** es una pérdida de calidad de los datos: es una limitación del formato CSV.


