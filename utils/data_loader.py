"""
Carga y validación de la base de datos de defectos.

Lee el archivo (por el momento) CSV y devuelve un DataFrame de pandas.
Entrega el archivo de estructura asociado a un defecto, si existe.
"""

# IMPORTS Y CONFIGURACIONES
from pathlib import Path
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "defects.csv"

REQUIRED_COLUMNS = [
    "id",
    "defect_name",
    "defect_type",
    "charge_state",
    "formation_energy_eV",
]
NUMERIC_COLUMNS = [
    "charge_state",
    "spin_multiplicity",
    "formation_energy_eV",
    "zpl_energy_eV"
]



# FUNCIONES
@st.cache_data
def load_defects(csv_path: Path = CSV_PATH) -> pd.DataFrame:
    """
    Lee el CSV de defectos y devuelve un DataFrame limpio.

    El decorador st.cache_data evita releer el archivo en cada interacción del usuario (cada filtro, cada click). Solo se vuelve a cargar si el archivo cambia.
    """

    if not csv_path.exists():
        st.error(f"No se encontró el archivo de datos en: {csv_path}")
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    df = pd.read_csv(csv_path)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Faltan columnas obligatorias en defects.csv: {missing}")

    # Typos numéricos: fuerza conversión y deja NaN si algo viene mal escrito
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_structure_path(row: pd.Series) -> Path | None:
    """
    Devuelve la ruta absoluta al archivo de estructura de un defecto, si existe."""

    value = row.get("structure_file")
    if pd.isna(value) or not str(value).strip():
        return None
    path = DATA_DIR / str(value)
    return path if path.exists() else None
