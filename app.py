# IMPORTS Y CONFIGURACIONES
import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import streamlit.components.v1 as components

from utils.data_loader import load_defects, get_structure_path, get_orbital_path, RELEVANT_COLUMNS, MAIN_TABLA_COLUMNS, PARAM_TABLA_COLUMNS

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
        <div style="border-left:0.2vw solid; height:13vw; min-height:30px;"></div>
        <div>
            <div style="font-size:4vw; font-weight:600; line-height:1.2;">Base de datos de defectos en h-BN</div>
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
structure_types = sorted(df["Estructura"].dropna().unique())
selected_types = st.sidebar.multiselect("Tipo de estructura", structure_types, default=structure_types)

defect_types = sorted(df["Tipo"].dropna().unique())
selected_types = st.sidebar.multiselect("Tipo de defecto", defect_types, default=defect_types)

charge_states = sorted(df["Carga"].dropna().unique())
selected_charges = st.sidebar.multiselect("Estado de carga", charge_states, default=charge_states)

    # Filtro por ZPL
zpl_values = df["ZPL (eV)"].dropna()
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
    df["Tipo"].isin(selected_types)
    & df["Carga"].isin(selected_charges)
]
if search_name:
    filtered = filtered[filtered["Defecto"].str.contains(search_name, case=False, na=False)]

if only_complete:
    filtered = filtered.dropna(how="any", subset=RELEVANT_COLUMNS)

if selected_zpl_range is not None:
    low, high = selected_zpl_range
    filtered = filtered[filtered["ZPL (eV)"].between(low, high)]

    # Número de resultados encontrados
st.sidebar.markdown(f"**{len(filtered)}** de {len(df)} defectos")



# TABLA PRINCIPAL --------------------------------------------------------------
st.subheader("Defectos encontrados")
evento = st.dataframe(
    filtered[[c for c in MAIN_TABLA_COLUMNS if c in filtered.columns]],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)



# INFORMACIÓN ADICIONAL DEL DEFECTO --------------------------------------------
st.subheader("Detalle del defecto")
filas_seleccionadas = evento.selection.rows

if not filas_seleccionadas:
    st.info("Selecciona un defecto en la tabla (marca la casilla a la izquierda de una fila) para ver el detalle.")
    st.stop()

row = filtered.iloc[filas_seleccionadas[0]]

col1, col2, col3 = st.columns([1, 1, 1])

# Estructura
with col1:
    structure_path = get_structure_path(row)
    if structure_path is not None:
        with st.container(border=True):
            try:
                with open(structure_path) as f:
                    xyz_data = f.read()

                # Leyendas
                elem_colors = {"B": "orange", "N": "blue", "C": "black"}
                elements_present = sorted(set(
                    line.split()[0] for line in xyz_data.strip().split("\n")[2:] if line.strip()
                ))
                legend_html = "<div style='display:flex; gap:15px; margin-top:5px; justify-content:flex-end;'>"
                for elem in elements_present:
                    color = elem_colors.get(elem, "black")
                    legend_html += (
                        f"<div style='display:flex; align-items:center; gap:5px;'>"
                        f"<div style='width:12px; height:12px; border-radius:50%; background:{color};'></div>"
                        f"<span>{elem}</span></div>"
                    )
                legend_html += "</div>"

                st.markdown("**Estructura**")

                style_lines = "\n".join(
                    f'viewer.setStyle({{elem:"{elem}"}}, {{stick:{{radius:0.15, color:"{color}"}}, sphere:{{scale:0.25, color:"{color}"}}}});'
                    for elem, color in elem_colors.items()
                )

                # Gráfico con HTML para que se ajuste al tamaño de la ventana
                html_code = f"""
                <div style="width:100%; aspect-ratio:4/3; position:relative;">
                <div id="viewer" style="width:100%; height:100%; position:absolute;"></div>
                <button onclick="reiniciarVista()" title="Reiniciar vista" style="
                    position:absolute; top:8px; right:8px; z-index:10;
                    width:28px; height:28px; padding:0; cursor:pointer;
                    background:rgba(255,255,255,0.85); border:1px solid #ccc;
                    border-radius:50%; font-size:1rem; line-height:1;
                    display:flex; align-items:center; justify-content:center;">
                ↻
                </button>
                </div>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
                <script>
                let viewer = $3Dmol.createViewer(document.getElementById("viewer"), {{backgroundColor:"white"}});
                viewer.addModel(`{xyz_data}`, "xyz");
{style_lines}
                viewer.setHoverable({{}}, true,
                    function(atom, viewer, event, container) {{
                        if (!atom.label) {{
                            atom.label = viewer.addLabel(
                                `${{atom.elem}} (${{atom.x.toFixed(3)}}, ${{atom.y.toFixed(3)}}, ${{atom.z.toFixed(3)}})`,
                                {{position: atom, backgroundColor: "black", fontColor: "white", fontSize: 12}}
                            );
                        }}
                    }},
                    function(atom) {{
                        if (atom.label) {{
                            viewer.removeLabel(atom.label);
                            delete atom.label;
                        }}
                    }}
                );
                viewer.zoomTo();
                viewer.setZoomLimits(10, 80);
                viewer.zoom(1.3);
                viewer.render();
                let vistaInicial = viewer.getView();

                function reiniciarVista() {{
                  viewer.setView(vistaInicial);
                  viewer.render();
                }}

                window.addEventListener("resize", () => {{ viewer.resize(); }});
                </script>
                """

                components.html(html_code, height=220, scrolling=False)

                st.markdown(legend_html, unsafe_allow_html=True)
            except Exception as e:
                st.info(f"No se pudo renderizar la estructura 3D: {e}")
    else:
        st.info("Este defecto aún no tiene archivo de estructura asociado.")

# HOMO
with col2:
    homo_path = get_orbital_path(row, "homo")
    structure_path = get_structure_path(row)
    if homo_path is not None and structure_path is not None:
        with st.container(border=True):
            try:
                with open(structure_path) as f:
                    xyz_data = f.read()
                with open(homo_path) as f:
                    cube_data = f.read()

                elem_colors = {"B": "orange", "N": "blue", "C": "black"}
                style_lines = "\n".join(
                    f'viewer.setStyle({{elem:"{elem}"}}, {{stick:{{radius:0.15, color:"{color}"}}, sphere:{{scale:0.25, color:"{color}"}}}});'
                    for elem, color in elem_colors.items()
                )

                st.markdown("**HOMO**")

                orbital_legend = (
                    "<div style='display:flex; gap:15px; margin-top:5px; justify-content:flex-end;'>"
                    "<div style='display:flex; align-items:center; gap:5px;'>"
                    "<div style='width:12px; height:12px; border-radius:50%; background:#1f77b4;'></div>"
                    "<span>-</span></div>"
                    "<div style='display:flex; align-items:center; gap:5px;'>"
                    "<div style='width:12px; height:12px; border-radius:50%; background:#d62728;'></div>"
                    "<span>+</span></div></div>"
                )

                html_code = f"""
                <div style="width:100%; aspect-ratio:4/3; position:relative;">
                <div id="viewer_homo" style="width:100%; height:100%; position:absolute;"></div>
                <button onclick="reiniciarVista()" title="Reiniciar vista" style="
                    position:absolute; top:8px; right:8px; z-index:10;
                    width:28px; height:28px; padding:0; cursor:pointer;
                    background:rgba(255,255,255,0.85); border:1px solid #ccc;
                    border-radius:50%; font-size:1rem; line-height:1;
                    display:flex; align-items:center; justify-content:center;">
                ↻
                </button>
                </div>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
                <script>
                let viewer = $3Dmol.createViewer(document.getElementById("viewer_homo"), {{backgroundColor:"white"}});
                viewer.addModel(`{xyz_data}`, "xyz");
                {style_lines}
                let voldataHomo = new $3Dmol.VolumeData(`{cube_data}`, "cube");
                viewer.addIsosurface(voldataHomo, {{isoval: 0.0005, color: "#1f77b4", opacity: 0.8}});
                viewer.addIsosurface(voldataHomo, {{isoval: -0.0005, color: "#d62728", opacity: 0.9}});
                viewer.zoomTo();
                viewer.setZoomLimits(10, 80);
                viewer.zoom(1.5);
                viewer.render();
                let vistaInicial = viewer.getView();

                function reiniciarVista() {{
                viewer.setView(vistaInicial);
                viewer.render();
                }}

                window.addEventListener("resize", () => {{ viewer.resize(); }});
                </script>
                """

                components.html(html_code, height=220, scrolling=False)
                st.markdown(orbital_legend, unsafe_allow_html=True)
            except Exception as e:
                st.info(f"No se pudo renderizar el HOMO: {e}")
    else:
        st.info("Este defecto aún no tiene archivo de HOMO asociado.")

# LUMO
with col3:
    lumo_path = get_orbital_path(row, "lumo")
    structure_path = get_structure_path(row)
    if lumo_path is not None and structure_path is not None:
        with st.container(border=True):
            try:
                with open(structure_path) as f:
                    xyz_data = f.read()
                with open(lumo_path) as f:
                    cube_data = f.read()

                elem_colors = {"B": "orange", "N": "blue", "C": "black"}
                style_lines = "\n".join(
                    f'viewer.setStyle({{elem:"{elem}"}}, {{stick:{{radius:0.15, color:"{color}"}}, sphere:{{scale:0.25, color:"{color}"}}}});'
                    for elem, color in elem_colors.items()
                )

                st.markdown("**LUMO**")

                orbital_legend = (
                    "<div style='display:flex; gap:15px; margin-top:5px; justify-content:flex-end;'>"
                    "<div style='display:flex; align-items:center; gap:5px;'>"
                    "<div style='width:12px; height:12px; border-radius:50%; background:#1f77b4;'></div>"
                    "<span>-</span></div>"
                    "<div style='display:flex; align-items:center; gap:5px;'>"
                    "<div style='width:12px; height:12px; border-radius:50%; background:#d62728;'></div>"
                    "<span>+</span></div></div>"
                )

                html_code = f"""
                <div style="width:100%; aspect-ratio:4/3; position:relative;">
                <div id="viewer_lumo" style="width:100%; height:100%; position:absolute;"></div>
                <button onclick="reiniciarVista()" title="Reiniciar vista" style="
                    position:absolute; top:8px; right:8px; z-index:10;
                    width:28px; height:28px; padding:0; cursor:pointer;
                    background:rgba(255,255,255,0.85); border:1px solid #ccc;
                    border-radius:50%; font-size:1rem; line-height:1;
                    display:flex; align-items:center; justify-content:center;">
                ↻
                </button>
                </div>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
                <script>
                let viewer = $3Dmol.createViewer(document.getElementById("viewer_lumo"), {{backgroundColor:"white"}});
                viewer.addModel(`{xyz_data}`, "xyz");
                {style_lines}
                let voldataLumo = new $3Dmol.VolumeData(`{cube_data}`, "cube");
                viewer.addIsosurface(voldataLumo, {{isoval: 0.0005, color: "#1f77b4", opacity: 0.8}});
                viewer.addIsosurface(voldataLumo, {{isoval: -0.0005, color: "#d62728", opacity: 0.9}});
                viewer.zoomTo();
                viewer.setZoomLimits(10, 80);
                viewer.zoom(1.5);
                viewer.render();
                let vistaInicial = viewer.getView();

                function reiniciarVista() {{
                viewer.setView(vistaInicial);
                viewer.render();
                }}

                window.addEventListener("resize", () => {{ viewer.resize(); }});
                </script>
                """

                components.html(html_code, height=220, scrolling=False)
                st.markdown(orbital_legend, unsafe_allow_html=True)
            except Exception as e:
                st.info(f"No se pudo renderizar el LUMO: {e}")
    else:
        st.info("Este defecto aún no tiene archivo de LUMO asociado.")


col4, col5 = st.columns([1, 2])
with col4:
    st.markdown("**Niveles energéticos**")

with col5:
    st.markdown("**ZPL**")

col6, col7 = st.columns([1, 1])

# Parámetros simulaciones
with col6:
    st.markdown("**Parámetros simulaciones**")
    param_data = pd.DataFrame({
        "Campo": PARAM_TABLA_COLUMNS,
        "Valor": [row[c] for c in PARAM_TABLA_COLUMNS],
    })

    st.dataframe(param_data, hide_index=True, use_container_width=True)

# Referencias
with col7:
    with st.container(border=True):
        st.markdown("**Otros estudios sobre este defecto:**")