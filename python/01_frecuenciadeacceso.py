import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "inputs" / "01_frecuenciadeacceso"
OUTPUT_DIR = BASE_DIR / "outputs" / "01_frecuenciadeacceso"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

json_files = sorted(INPUT_DIR.glob("*.json"))

if not json_files:
    raise FileNotFoundError(f"No JSON files found in {INPUT_DIR}")

path = json_files[0]  # toma el primero (orden alfabético)

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

"""## Arreglar formato"""

# arreglar anidamiento doble
if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
    records = data[0]
else:
    records = data

df = pd.json_normalize(records)

df.head()

"""### Convertir formato de fecha"""

df["hora"] = pd.to_datetime(
    df["hora"],
    format="%d/%m/%y, %H:%M:%S",
    errors="coerce"
)

"""## Extraer fechas"""

df["fecha"] = df["hora"].dt.date

daily_frequency = (
    df.groupby(
        ["fecha", "nombrecompletodelusuario", "nombredelevento"]
    )
    .size()
    .reset_index(name="frecuencia")
)

daily_frequency.head()

"""## Formato legible (Usuario - Eventos)"""

pivot_frequency = daily_frequency.pivot_table(
    index=["fecha", "nombrecompletodelusuario"],
    columns="nombredelevento",
    values="frecuencia",
    fill_value=0
).reset_index()

pivot_frequency.head(200)

# Crear pivot
pivot_frequency = daily_frequency.pivot_table(
    index=["fecha", "nombrecompletodelusuario"],
    columns="nombredelevento",
    values="frecuencia",
    fill_value=0
).reset_index()

pivot_frequency.columns.name = None

"""## Exportar a excel"""

pivot_frequency.to_excel(OUTPUT_DIR / "daily_frequency_pivot.xlsx", index=False)

"""## Opciones display"""

## mostrar tamaño del JSON
df.shape

df

"""## Exportar"""

# Export a Excel
daily_frequency.to_excel(OUTPUT_DIR / "daily_frequency.xlsx", index=False)