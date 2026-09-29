# IMPORTS Y CONFIGURACIONES
import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import streamlit.components.v1 as components
import plotly.graph_objects as go
import numpy as np
import re

from utils.data_loader import load_defects, get_file_path, get_structure_path, get_orbital_path, get_pl_path, RELEVANT_COLUMNS, MAIN_TABLA_COLUMNS, PARAM_TABLA_COLUMNS

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
    filtered = filtered[
    filtered["ZPL (eV)"].between(low, high) | filtered["ZPL (eV)"].isna()
    ]

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
filas_seleccionadas = evento.selection.rows

if not filas_seleccionadas:
    st.subheader("Detalle del defecto")
    st.info("Selecciona un defecto en la tabla (marca la casilla a la izquierda de una fila) para ver el detalle.")
    st.stop()

row = filtered.iloc[filas_seleccionadas[0]]

name_defect = re.sub(r'_([a-zA-Z0-9+-•])', r'<sub>\1</sub>', row.get("Defecto", "Desconocido"))
st.markdown(f"<h3>Detalle del defecto {name_defect}:</h3>", unsafe_allow_html=True)

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
    homo_image_path = get_file_path(row, "homo_image")
    if homo_image_path is not None:
        with st.container(border=True):
            coltit, colleg = st.columns([1, 1])
            with coltit:
                st.markdown("**HOMO**")
            with colleg:
                orbital_legend = (
                    "<div style='display:flex; gap:15px; margin-top:5px; justify-content:flex-end;'>"
                    "<div style='display:flex; align-items:center; gap:5px;'>"
                    "<div style='width:12px; height:12px; border-radius:50%; background:#1f77b4;'></div>"
                    "<span>-</span></div>"
                    "<div style='display:flex; align-items:center; gap:5px;'>"
                    "<div style='width:12px; height:12px; border-radius:50%; background:#d62728;'></div>"
                    "<span>+</span></div></div>"
                )
                st.markdown(orbital_legend, unsafe_allow_html=True)
            st.image(str(homo_image_path), use_container_width=True)
    else:
        st.info("Este defecto aún no tiene imagen de HOMO asociada.")

# LUMO
with col3:
    lumo_image_path = get_file_path(row, "lumo_image")
    if lumo_image_path is not None:
        with st.container(border=True):
            coltit, colleg = st.columns([1, 1])
            with coltit:
                st.markdown("**LUMO**")
            with colleg:
                orbital_legend = (
                    "<div style='display:flex; gap:15px; margin-top:5px; justify-content:flex-end;'>"
                    "<div style='display:flex; align-items:center; gap:5px;'>"
                    "<div style='width:12px; height:12px; border-radius:50%; background:#1f77b4;'></div>"
                    "<span>-</span></div>"
                    "<div style='display:flex; align-items:center; gap:5px;'>"
                    "<div style='width:12px; height:12px; border-radius:50%; background:#d62728;'></div>"
                    "<span>+</span></div></div>"
                )
                st.markdown(orbital_legend, unsafe_allow_html=True)
            st.image(str(lumo_image_path), use_container_width=True)
    else:
        st.info("Este defecto aún no tiene imagen de LUMO asociada.")


col4, col5 = st.columns([1, 2])

# Niveles energéticos
with col4:
    st.markdown("**Niveles energéticos**")

    vb = row.get("VB")
    cb = row.get("CB")

    if pd.notna(vb) and pd.notna(cb):

        def dibujar_niveles(fig, niveles, x0, x1, color, simbolo_base, direction, relleno=True, umbral_agrupacion=0.1):
            if not niveles:
                return

            # Agrupa niveles consecutivos (una vez ordenados) que estén a menos de "umbral_agrupacion" eV entre sí — cada grupo se reparte lado a lado
            niveles_ordenados = sorted(niveles)
            grupos = [[niveles_ordenados[0]]]
            for n in niveles_ordenados[1:]:
                if n - grupos[-1][-1] <= umbral_agrupacion:
                    grupos[-1].append(n)
                else:
                    grupos.append([n])

            largo_flecha = 0.3
            ancho_hueco = 0.02

            for grupo in grupos:
                k = len(grupo)
                sub_ancho = (x1 - x0) / k  # cada nivel del grupo se queda con una franja propia

                for i, nivel in enumerate(grupo):
                    xi0 = x0 + i * sub_ancho
                    xi1 = xi0 + sub_ancho
                    x_centro = (xi0 + xi1) / 2

                    fig.add_shape(type="line", x0=xi0, x1=xi1, y0=nivel, y1=nivel,
                                line=dict(color=color, width=1.5))

                    half = largo_flecha / 2
                    y_head = nivel + direction * half
                    y_tail = nivel - direction * half

                    if relleno:
                        fig.add_shape(type="line", x0=x_centro, x1=x_centro, y0=y_tail, y1=y_head,
                                    line=dict(color=color, width=5))
                    else:
                        fig.add_shape(type="rect",
                                    x0=x_centro - ancho_hueco / 2, x1=x_centro + ancho_hueco / 2,
                                    y0=min(y_tail, y_head), y1=max(y_tail, y_head),
                                    line=dict(color=color, width=1.5), fillcolor="rgba(0,0,0,0)")

                    fig.add_trace(go.Scatter(
                        x=[x_centro], y=[y_head + direction * 0.045], mode="markers",
                        marker=dict(symbol=simbolo_base, size=9, color=color,
                                    line=dict(width=1.5, color=color)),
                        showlegend=False, hoverinfo="skip",
                    ))

                    # Capa invisible para hover: cubre la línea del nivel y el cuerpo de la
                    # flecha, con un ancho generoso para que sea fácil acertar con el mouse
                    fig.add_trace(go.Scatter(
                        x=[xi0, xi1, None, x_centro, x_centro],
                        y=[nivel, nivel, None, y_tail, y_head],
                        mode="lines",
                        line=dict(color="rgba(0,0,0,0)", width=14),
                        hovertemplate=f"{nivel:.3f} eV<extra></extra>",
                        showlegend=False,
                    ))

        def flecha_doble(fig, x, y0, y1, texto, color="black", head_margin=0.0):
            y0_dibujo = y0 + head_margin
            y1_dibujo = y1 - head_margin
            fig.add_shape(type="line", x0=x, x1=x, y0=y0_dibujo, y1=y1_dibujo,
                        line=dict(color=color, width=1, dash="dash"))
            fig.add_trace(go.Scatter(
                x=[x, x], y=[y0_dibujo, y1_dibujo], mode="markers",
                marker=dict(symbol=["triangle-down", "triangle-up"], size=8, color=color),
                showlegend=False, hoverinfo="skip",
            ))
            fig.add_annotation(x=x, y=(y0 + y1) / 2, text=f"{texto} eV",
                                showarrow=False, textangle=-90,
                                font=dict(size=13, color=color), xshift=-14)

        # Se grafica relativo a VB, para que VB quede fijo en 0 en el eje Y
        gap = cb - vb
        vb0, cb0 = 0.0, gap

        margen = 0.5
        grosor_banda = 0.3
        head_margin = 0.1

        x_min, x_max = -0.4, 1.1

        fig_levels = go.Figure()

        fig_levels.add_shape(type="rect", x0=x_min, x1=x_max, y0=vb0 - grosor_banda, y1=vb0, fillcolor="gray", line_width=0)
        fig_levels.add_shape(type="rect", x0=x_min, x1=x_max, y0=cb0, y1=cb0 + grosor_banda, fillcolor="gray", line_width=0)
        fig_levels.add_hline(y=vb0, line=dict(color="black", width=1, dash="dash"))
        fig_levels.add_hline(y=cb0, line=dict(color="black", width=1, dash="dash"))

        # Listas de niveles, ya desplazadas para quedar relativas a VB
        niveles_up_occ = [n - vb for n in (row.get("levels up occ") or [])]
        niveles_up_unocc = [n - vb for n in (row.get("levels up unocc") or [])]
        niveles_down_occ = [n - vb for n in (row.get("levels dw occ") or [])]
        niveles_down_unocc = [n - vb for n in (row.get("levels dw unocc") or [])]

        # Segmentos más largos y delgados, con más separación entre spin up y down
        dibujar_niveles(fig_levels, niveles_up_occ, 0.05, 0.42, "#d62728", "triangle-up", direction=1, relleno=True)
        dibujar_niveles(fig_levels, niveles_up_unocc, 0.05, 0.42, "#d62728", "triangle-up-open", direction=1, relleno=False)
        dibujar_niveles(fig_levels, niveles_down_occ, 0.58, 0.95, "#1f77b4", "triangle-down", direction=-1, relleno=True)
        dibujar_niveles(fig_levels, niveles_down_unocc, 0.58, 0.95, "#1f77b4", "triangle-down-open", direction=-1, relleno=False)

        # Flecha del gap completo, a la izquierda
        flecha_doble(fig_levels, -0.2, vb0, cb0, f"{gap:.3f}", head_margin=head_margin)

        # Una sola transición por spin: del último ocupado (o VB) al primer desocupado (o CB)
        y0_up = niveles_up_occ[-1] if niveles_up_occ else vb0
        y1_up = niveles_up_unocc[0] if niveles_up_unocc else cb0
        flecha_doble(fig_levels, 0.05, y0_up, y1_up, f"{y1_up - y0_up:.3f}",
                    color="#d62728", head_margin=head_margin)

        y0_down = niveles_down_occ[-1] if niveles_down_occ else vb0
        y1_down = niveles_down_unocc[0] if niveles_down_unocc else cb0
        flecha_doble(fig_levels, 0.55, y0_down, y1_down, f"{y1_down - y0_down:.3f}",
                    color="#1f77b4", head_margin=head_margin)

        fig_levels.update_xaxes(visible=False, range=[x_min, x_max], fixedrange=True)
        fig_levels.update_yaxes(
            title="Energía (eV)", visible=True, fixedrange=True,
            range=[vb0 - margen, cb0 + margen], zeroline=False,
        )
        fig_levels.update_layout(
            height=300, showlegend=False, plot_bgcolor="white",
            margin=dict(l=60, r=20, t=0, b=0),
            dragmode=False,
        )

        st.plotly_chart(fig_levels, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Este defecto aún no tiene datos de bandas cargados para graficar los niveles.")

# ZPL
with col5:
    st.markdown("**ZPL**")
    pl_path = get_pl_path(row)
    if pl_path is not None:
        try:
            pl_data = pd.read_csv(pl_path, sep=r"\s+")
            col_e, col_pl = pl_data.columns[0], pl_data.columns[1]

            fig_pl = go.Figure()
            fig_pl.add_trace(go.Scatter(
                x=pl_data[col_e], y=pl_data[col_pl],
                mode="lines", line=dict(color="#1E50B4", width=2.5),
            ))
            fig_pl.update_xaxes(title="Energía (eV)")
            fig_pl.update_yaxes(title="Intensidad PL (u.a.)")
            fig_pl.update_layout(
                height=350, showlegend=False, plot_bgcolor="white",
                margin=dict(l=60, r=20, t=0, b=0),
            )

            zpl_val = row.get("ZPL (eV)")
            if pd.notna(zpl_val):
                fig_pl.add_shape(type="line", x0=zpl_val, x1=zpl_val, y0=0, y1=pl_data[col_pl].max(), line=dict(color="black", width=1.5, dash="dash"))
                y_puntos = np.linspace(0, 10, 30)
                fig_pl.add_annotation(x=zpl_val+0.075, y=0.8, text=f"ZPL = {zpl_val:.3f} eV", showarrow=False, textangle= -90, font=dict(size=16, color="black"))

                fig_pl.update_xaxes(range=[zpl_val - 1.2, zpl_val + 0.4])

            def flecha_doble_horizontal(fig, y, x0, x1, texto, color="black"):
                """Flecha horizontal punteada con cabezas en ambos extremos, para medir
                la distancia en eV entre dos picos consecutivos."""
                fig.add_shape(type="line", x0=x0, x1=x1, y0=y, y1=y,
                            line=dict(color=color, width=1, dash="dash"))
                fig.add_trace(go.Scatter(
                    x=[x0+0.01, x1-0.01], y=[y, y], mode="markers",
                    marker=dict(symbol=["triangle-left", "triangle-right"], size=8, color=color),
                    showlegend=False, hoverinfo="skip",
                ))
                fig.add_annotation(x=(x0 + x1) / 2, y=y, text=f"{texto} meV",
                                    showarrow=False, yshift=10,
                                    font=dict(size=12, color=color))

            psb_peaks = row.get("PSB (eV)") or []

            # Línea vertical + etiqueta para cada peak, mismo estilo que el ZPL
            for peak in psb_peaks:
                fig_pl.add_shape(type="line", x0=peak, x1=peak, y0=0, y1=1,
                                line=dict(color="black", width=1, dash="dash"))
                fig_pl.add_annotation(x=peak+0.035, y=0.8, text=f"{peak:.3f} eV", showarrow=False, yshift=12, textangle=-90, font=dict(size=14, color="black"))

            # Flechas de distancia entre puntos consecutivos (ZPL incluido como el primero)
            puntos = sorted(([zpl_val] if pd.notna(zpl_val) else []) + psb_peaks)
            y_flecha = 0.05
            for p0, p1 in zip(puntos[:-1], puntos[1:]):
                flecha_doble_horizontal(fig_pl, y_flecha, p0, p1, f"{(p1 - p0)*1000:.0f}", color="black")
            
            st.plotly_chart(fig_pl, use_container_width=True, config={"displayModeBar": False})

        except Exception as e:
            st.info(f"No se pudo graficar la fotoluminiscencia: {e}")
    else:
        st.info("Este defecto aún no tiene datos de fotoluminiscencia asociados.")

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