"""
Carga y validación de la base de datos de defectos.

Lee el archivo (por el momento) CSV y devuelve un DataFrame de pandas.
Entrega el archivo de estructura asociado a un defecto, si existe.
"""

# IMPORTS Y CONFIGURACIONES
from pathlib import Path
import pandas as pd
import streamlit as st
import ast

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "defects.csv"

REQUIRED_COLUMNS = [
    "ID",
    "Defecto",
    "Tipo",
    "Carga"
]
NUMERIC_COLUMNS = [
    "Carga",
    "Mutiplicidad de espín",
    "ZPL (eV)",
    "ZPL (nm)",
    "1er PSB (meV)",
    "Factor de HR",
    "Factor de intercambio",
    "Nº de átomos",
    "Región de vacío (Å)",
    "VB",
    "CB"
]

RELEVANT_COLUMNS = [
    "ID",
    "Defecto",
    "Tipo",
    "Carga",
    "ZPL (eV)",
    "structure_file"
]
MAIN_TABLA_COLUMNS = [
    "Defecto",
    "Estructura",
    "Tipo",
    "Carga",
    "Multiplicidad de espín",
    "Transición de espín",
    "ZPL (eV)",
    "ZPL (nm)",
    "1er PSB (meV)",
    "Simetría",
    "Factor de HR"
]

PARAM_TABLA_COLUMNS = [
    "DFT software",
    "Pseudopotenciales",
    "Funcional",
    "Factor de intercambio",
    "Estructura",
    "Tamaño supercelda",
    "N de átomos",
    "Región de vacío (Å)",
    "Malla puntos k",
    "Puntos k HSE"
]

LIST_COLUMNS = [
    "levels up occ", 
    "levels up unocc",
    "levels dw occ",
    "levels dw unocc",
    "PSB (eV)"
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

    for col in LIST_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(_parse_list)

    return df


def get_file_path(row: pd.Series, column: str) -> Path | None:
    """Devuelve la ruta absoluta a un archivo asociado a un defecto (estructura, orbital, etc.), si existe."""
    value = row.get(column)
    if pd.isna(value) or not str(value).strip():
        return None
    path = DATA_DIR / str(value)
    return path if path.exists() else None
 
 
def get_structure_path(row: pd.Series) -> Path | None:
    """Devuelve la ruta absoluta al archivo de estructura de un defecto, si existe."""
    return get_file_path(row, "structure_file")
 
 
def get_orbital_path(row: pd.Series, orbital: str) -> Path | None:
    """Devuelve la ruta absoluta al archivo .png del HOMO o LUMO de un defecto, si existe.
 
    orbital debe ser "homo" o "lumo".
    """
    column = f"{orbital.lower()}_file"
    return get_file_path(row, column)


def get_pl_path(row: pd.Series) -> Path | None:
    """Devuelve la ruta absoluta al archivo de fotoluminiscencia (E vs PL) de un defecto, si existe."""
    return get_file_path(row, "pl_file")


def _parse_list(value):
    """Convierte un string tipo '[1.2, 2.3, 3.1]' en una lista real de floats.
    Devuelve lista vacía si está vacío, mal formado, o es NaN."""
    if pd.isna(value) or not str(value).strip():
        return []
    try:
        parsed = ast.literal_eval(str(value))
        return [float(x) for x in parsed]
    except (ValueError, SyntaxError):
        return []