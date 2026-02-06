import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO

# Setup pagina
st.set_page_config(page_title="Modello ADR", layout="wide")
st.title("Simulazione Numerica ADR - Analisi Inquinanti")

# --- PARAMETRI SIDEBAR ---
st.sidebar.header("Input Modello")
meteo = st.sidebar.selectbox("Atmosfera", ["Instabile", "Neutro", "Inversione"])
pioggia_scelta = st.sidebar.select_slider("Pioggia", options=["No", "Debole", "Forte"])

# Setup fisico (rif. Tesi Fedi Cap. 4)
if meteo == "Instabile": d_init, u_init = 1.7, 0.7
elif meteo == "Neutro": d_init, u_init = 1.0, 1.4
else: d_init, u_init = 0.2, 0.4

u_vento = st.sidebar.slider("Vento (u) [m/s]", 0.1, 5.0, u_init)
diff_K = st.sidebar.slider("Diffusione (K)", 0.1, 2.5, d_init)

gas = st.sidebar.selectbox("Gas", ["Tossico (Bhopal)", "NO2", "CO"])
if gas == "Tossico (Bhopal)": soglia, sol = 0.05, 1.0
elif gas == "NO2": soglia, sol = 0.1, 0.8
else: soglia, sol = 9.0, 0.35 # CO meno solubile

Q_sorgente = st.sidebar.slider("Sorgente (Q)", 50, 250, 100)

# --- GRIGLIA E MATRICI ---
N = 50
dx = 1.0
dt = 0.04 # Passo tempo per stabilità numerica

# Rimozione per pioggia (Cap. 6 tesi)
k_p = {"No": 0.0, "Debole": 0.07, "Forte": 0.22}[pioggia_scelta]

# Matrice ostacoli (Edifici)
muri = np.zeros((N, N))
np.random.seed(42)
for _ in range(10):
    ix, iy = np.random.randint(20, 44), np.random.randint(10, 39)
    muri[ix:ix+3, iy:iy+3] = 1

# --- LOGICA SIMULAZIONE ---
if st.sidebar.button("RUN SIMULAZIONE"):
    C = np.zeros((N, N))
    mappa = st.empty()
    alert = st.empty()
    
    # Rilascio gas
    sx, sy = 10, 25

    for t in range(140):
        C_new = C.copy()
        C_new[sx, sy] += Q_sorgente * dt
        
        # Algoritmo Differenze Finite (Cap. 5 Tesi Fedi)
        for i in range(1, N-1):
            for j in range(1, N-1):
                if muri[i,j] == 1:
                    C_new[i,j] = 0
                    continue
                
                # Equazione ADR discretizzata
                diff = diff_K * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u_vento * dt * (C[i,j] - C[i-1,j]) # Schema Upwind
                reac = -(k_p * sol) * dt * C[i,j]
                
                C_new[i,j] += diff + adv + reac

        C = np.clip(C_new, 0, 100)
        
        if t % 15 == 0:
            # Calcolo picco su area urbana
            val_picco = np.max(C[20:45, 10:40]) * 0.13
            
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='Reds'),
                go.Surface(z=muri * 2.5, colorscale='Greys', opacity=0.3, showscale=False)
            ])
            fig.update_layout(scene=dict(zaxis=dict(range=[0, 15])), margin=dict(l=0, r=0, b=0, t=0))
            mappa.plotly_chart(fig, use_container_width=True)
            
            if val_picco > soglia:
                alert.error(f"PERICOLO: {val_picco:.4f} ppm")
            else:
                alert.success(f"SICURO: {val_picco:.4f} ppm")

    # --- EXCEL---
    p_finale = np.max(C[20:45, 10:40]) * 0.13
    df = pd.DataFrame({
        "Parametro": ["Gas", "Meteo", "Vento", "Pioggia", "Picco PPM", "Soglia"],
        "Dato": [gas, meteo, u_vento, pioggia_scelta, round(p_finale, 4), soglia]
    })
    
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    
    st.sidebar.download_button(
        label="Download Risultati Excel",
        data=buf.getvalue(),
        file_name="report_tesi.xlsx",
        mime="application/vnd.ms-excel"
    )
