# IMPORTS Y CONFIGURACIONES
import streamlit as st
import pandas as pd
import plotly.express as px
import base64

from utils.data_loader import load_defects, get_structure_path, RELEVANT_COLUMNS

st.set_page_config(
    page_title="hBN Defects Database",
    page_icon="⚛️",
    layout="wide",
)

# TÍTULO -----------------------------------------------------------------------
with open("assets/logoQOM.png", "rb") as f:
    logo_izq_b64 = base64.b64encode(f.read()).decode()
with open("assets/logoPUC.png", "rb") as f:
    logo_der_b64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; width:100%; margin-bottom:1vw;">
    <div style="display:flex; align-items:center; gap:1.5vw;">
        <img src="data:image/png;base64,{logo_izq_b64}" style="height:13vw; min-height:20px">
        <div style="border-left:0.2vw solid #999; height:12vw; min-height:30px;"></div>
        <div>
            <div style="font-size:4vw; font-weight:600; line-height:1.2; color:black">Base de datos de defectos en h-BN</div>
        </div>
    </div>
    <img src="data:image/png;base64,{logo_der_b64}" style="width:20vw; min-width:40px; align-self:flex-start; margin-left:10vw;">
</div>
""", unsafe_allow_html=True)


st.caption("Fondef IDeA Proyecto ID25I10517")



# CARGA DE DATOS ---------------------------------------------------------------
df = load_defects()

if df.empty:
    st.warning("La base de datos está vacía. Agrega filas a data/defects.csv.")
    st.stop()



# SIDEBAR: FILTROS -------------------------------------------------------------
st.sidebar.header("Filtros")

    # Búsqueda por nombre
search_name = st.sidebar.text_input("Buscar por nombre de defecto")

    # Categorías
defect_types = sorted(df["defect_type"].dropna().unique())
selected_types = st.sidebar.multiselect("Tipo de defecto", defect_types, default=defect_types)

charge_states = sorted(df["charge_state"].dropna().unique())
selected_charges = st.sidebar.multiselect("Estado de carga", charge_states, default=charge_states)

    # Filtro por ZPL
zpl_values = df["zpl_energy_eV"].dropna()
if not zpl_values.empty:
    zpl_min, zpl_max = float(zpl_values.min()), float(zpl_values.max())

    if "zpl_range" not in st.session_state:
        st.session_state.zpl_range = (zpl_min, zpl_max)

    def _sync_from_inputs():
        st.session_state.zpl_range = (st.session_state.zpl_low, st.session_state.zpl_high)

    def _sync_from_slider():
        st.session_state.zpl_low, st.session_state.zpl_high = st.session_state.zpl_range

    col_low, col_high = st.sidebar.columns(2)
    col_low.number_input(
        "ZPL mín (eV)", min_value=zpl_min, max_value=zpl_max,
        value=st.session_state.zpl_range[0], key="zpl_low", on_change=_sync_from_inputs,
    )
    col_high.number_input(
        "ZPL máx (eV)", min_value=zpl_min, max_value=zpl_max,
        value=st.session_state.zpl_range[1], key="zpl_high", on_change=_sync_from_inputs,
    )

    selected_zpl_range = st.sidebar.slider(
        "Rango de ZPL (eV)", min_value=zpl_min, max_value=zpl_max,
        key="zpl_range", on_change=_sync_from_slider,
    )
else:
    selected_zpl_range = None

# Solo defectos completos
only_complete = st.sidebar.checkbox("Solo defectos con información completa")

    # DF filtrado
filtered = df[
    df["defect_type"].isin(selected_types)
    & df["charge_state"].isin(selected_charges)
]
if search_name:
    filtered = filtered[filtered["defect_name"].str.contains(search_name, case=False, na=False)]

if only_complete:
    filtered = filtered.dropna(how="any", subset=RELEVANT_COLUMNS)

if selected_zpl_range is not None:
    low, high = selected_zpl_range
    filtered = filtered[filtered["zpl_energy_eV"].between(low, high)]

    # Número de resultados encontrados
st.sidebar.markdown(f"**{len(filtered)}** de {len(df)} defectos")



# TABLA PRINCIPAL --------------------------------------------------------------
st.subheader("Resultados")
st.dataframe(
    filtered.drop(columns=["structure_file"], errors="ignore"),
    use_container_width=True,
    hide_index=True,
)



# GRÁFICO 1: E de formación por defecto ----------------------------------------
if not filtered.empty:
    st.subheader("Energía de formación por defecto")
    fig = px.scatter(
        filtered,
        x="defect_name",
        y="formation_energy_eV",
        color="defect_type",
        symbol="charge_state",
        hover_data=["functional", "supercell", "reference"],
        labels={"formation_energy_eV": "Energía de formación (eV)", "defect_name": "Defecto"},
    )
    st.plotly_chart(fig, use_container_width=True)




# INFORMACIÓN ADICIONAL DEL DEFECTO --------------------------------------------
st.subheader("Detalle del defecto")
options = filtered["defect_name"] + " (q=" + filtered["charge_state"].astype(str) + ")"
if options.empty:
    st.info("No hay defectos que coincidan con los filtros seleccionados.")
    st.stop()

choice = st.selectbox("Selecciona un defecto para ver el detalle", options)
row = filtered.loc[options == choice].iloc[0]

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown(f"### {row['defect_name']} (carga {row['charge_state']})")
    st.write(f"**Tipo:** {row['defect_type']}")
    st.write(f"**Simetría:** {row.get('symmetry', '—')}")
    st.write(f"**Funcional:** {row.get('functional', '—')}")
    st.write(f"**Supercelda:** {row.get('supercell', '—')}")
    st.write(f"**Energía de formación:** {row['formation_energy_eV']} eV")
    if pd.notna(row.get("zpl_energy_eV")):
        st.write(f"**ZPL:** {row['zpl_energy_eV']} eV")
    if pd.notna(row.get("notes")):
        st.write(f"**Notas:** {row['notes']}")
    if pd.notna(row.get("reference")):
        st.write(f"**Referencia:** {row['reference']}")

with col2:
    structure_path = get_structure_path(row)
    if structure_path is not None:
        st.markdown("**Estructura**")
        try:
            import py3Dmol
            from stmol import showmol

            with open(structure_path) as f:
                xyz_data = f.read()

            view = py3Dmol.view(width=400, height=350)
            view.addModel(xyz_data, "xyz")
            view.setStyle({"stick": {}, "sphere": {"scale": 0.3}})
            view.zoomTo()
            showmol(view, height=350, width=400)
        except Exception as e:
            st.info(f"No se pudo renderizar la estructura 3D: {e}")
    else:
        st.info("Este defecto aún no tiene archivo de estructura asociado.")
