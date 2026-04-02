# -*- coding: utf-8 -*-
"""03. Patron Temporal."""

import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "inputs" / "03_patrón_temporal"
OUTPUT_DIR = BASE_DIR / "outputs" / "03_patrón_temporal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

json_files = sorted(INPUT_DIR.glob("*.json"))
if not json_files:
    raise FileNotFoundError(f"No JSON files found in {INPUT_DIR}")

PATH_JSON = json_files[0]
OUT_CSV = OUTPUT_DIR / "patron_temporal_resultados.csv"
OUT_XLSX = OUTPUT_DIR / "patron_temporal_resultados.xlsx"

# Formato tipico de Moodle (ejemplo: "20/02/26, 19:44:01")
FORMATO_HORA = "%d/%m/%y, %H:%M:%S"

# Ventana nocturna (incluye 0 a 5)
NIGHT_START = 0
NIGHT_END = 5

# Percentil para definir "picos" de actividad diaria (0.90 = top 10%)
PICO_Q = 0.90

# Columnas esperadas en el DataFrame
COL_TIME = "hora"
COL_ACTOR = "nombrecompletodelusuario"


def assert_file_exists(path: Path) -> None:
    if not path.exists():
        available = sorted(p.name for p in INPUT_DIR.glob("*"))
        raise FileNotFoundError(
            f"No se encontro el archivo: {path}\n"
            f"Contenido de {INPUT_DIR}: {available if available else '[]'}"
        )


def load_moodle_json(path: Path) -> list:
    """Carga JSON y corrige el anidamiento doble si existe."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
        return data[0]
    return data


def normalize_records(records: list) -> pd.DataFrame:
    """Convierte lista de dicts a DataFrame."""
    df = pd.json_normalize(records)

    missing = [c for c in [COL_TIME, COL_ACTOR] if c not in df.columns]
    if missing:
        raise KeyError(
            f"Faltan columnas esperadas: {missing}\n"
            f"Columnas disponibles: {list(df.columns)}\n"
            "Solucion: revisa df.columns y ajusta COL_TIME / COL_ACTOR."
        )

    return df


def parse_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte la columna de tiempo a datetime y crea variables temporales."""
    df = df.copy()

    df[COL_TIME] = pd.to_datetime(
        df[COL_TIME],
        format=FORMATO_HORA,
        errors="coerce",
    )

    df = df.dropna(subset=[COL_TIME])
    df["semana"] = df[COL_TIME].dt.isocalendar().week.astype(int)
    df["hora_num"] = df[COL_TIME].dt.hour.astype(int)
    df["fecha"] = df[COL_TIME].dt.date

    return df


def calcular_patron_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula variables de patron temporal por actor."""
    resultados = []

    for actor, grupo in df.groupby(COL_ACTOR):
        actividad_semanal = grupo.groupby("semana").size()
        media_semanal = actividad_semanal.mean()
        desviacion_semanal = actividad_semanal.std(ddof=1)

        cv_semanal = (
            desviacion_semanal / media_semanal
            if media_semanal and media_semanal > 0
            else 0.0
        )

        eventos_nocturnos = grupo[
            (grupo["hora_num"] >= NIGHT_START) & (grupo["hora_num"] <= NIGHT_END)
        ]
        proporcion_nocturna = len(eventos_nocturnos) / len(grupo) if len(grupo) > 0 else 0.0

        actividad_diaria = grupo.groupby("fecha").size()
        if len(actividad_diaria) > 0:
            umbral_pico = actividad_diaria.quantile(PICO_Q)
            dias_pico = actividad_diaria[actividad_diaria >= umbral_pico]
            intensidad_picos = dias_pico.sum() / actividad_diaria.sum()
        else:
            intensidad_picos = 0.0

        desviacion_horaria = float(grupo["hora_num"].std(ddof=1)) if len(grupo) > 1 else 0.0

        resultados.append(
            {
                "actor": actor,
                "eventos_total": int(len(grupo)),
                "semanas_con_actividad": int(actividad_semanal.shape[0]),
                "cv_semanal": float(cv_semanal),
                "proporcion_nocturna": float(proporcion_nocturna),
                "intensidad_picos": float(intensidad_picos),
                "desviacion_horaria": float(desviacion_horaria),
            }
        )

    return pd.DataFrame(resultados).sort_values("actor").reset_index(drop=True)


def main() -> pd.DataFrame:
    assert_file_exists(PATH_JSON)

    records = load_moodle_json(PATH_JSON)
    df_raw = normalize_records(records)

    print("Columnas detectadas:")
    print(list(df_raw.columns))

    df = parse_datetime(df_raw)

    print("\nPreview (df procesado):")
    print(df.head().to_string(index=False))

    patron_temporal_df = calcular_patron_temporal(df)

    print("\nPreview (patron_temporal_df):")
    print(patron_temporal_df.head().to_string(index=False))

    patron_temporal_df.to_csv(OUT_CSV, index=False, encoding="utf-8")
    patron_temporal_df.to_excel(OUT_XLSX, index=False)

    print(f"\nArchivo CSV generado: {OUT_CSV}")
    print(f"Archivo Excel generado: {OUT_XLSX}")

    return patron_temporal_df


if __name__ == "__main__":
    main()
