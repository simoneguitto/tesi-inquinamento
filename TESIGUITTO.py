import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO

# Titolo e setup
st.set_page_config(page_title="Modello ADR", layout="wide")
st.title("Simulatore Dispersione Inquinanti - Analisi Numerica")

# --- BARRA LATERALE (INPUT) ---
st.sidebar.header("Parametri Modello")
meteo = st.sidebar.selectbox("Meteo", ["Instabile", "Neutro", "Inversione"])
pioggia = st.sidebar.select_slider("Pioggia", options=["No", "Bassa", "Forte"])

# Dati tecnici (Rif. Tesi Fedi)
if meteo == "Instabile": d_val, u_val = 1.7, 0.7
elif meteo == "Neutro": d_val, u_val = 1.0, 1.4
else: d_val, u_val = 0.2, 0.4

u = st.sidebar.slider("Vento u (m/s)", 0.1, 5.0, u_val)
K = st.sidebar.slider("Diffusione K", 0.1, 2.5, d_val)

gas = st.sidebar.selectbox("Inquinante", ["Gas Tossico", "NO2", "CO"])
if gas == "Gas Tossico": soglia, sol = 0.05, 1.0
elif gas == "NO2": soglia, sol = 0.1, 0.7
else: soglia, sol = 9.0, 0.35

Q = st.sidebar.slider("Sorgente Q", 50, 250, 100)

# --- GRIGLIA E MATRICI ---
N = 50
dx = 1.0
dt = 0.04  # Passo tempo stabile

# Coefficiente lavaggio pioggia
kp_val = {"No": 0.0, "Bassa": 0.07, "Forte": 0.22}[pioggia]

# Creazione Edifici (Orografia urbana Cap. A.4)
muri = np.zeros((N, N))
np.random.seed(42)
for _ in range(10):
    ix, iy = np.random.randint(20, 44), np.random.randint(10, 39)
    muri[ix:ix+3, iy:iy+3] = 1

# --- CALCOLO ---
if st.sidebar.button("AVVIA"):
    C = np.zeros((N, N))
    grafico = st.empty()
    alert = st.empty()
    
    # Sorgente interna (sx, sy)
    sx, sy = 10, 25

    for t in range(140):
        C_new = C.copy()
        C_new[sx, sy] += Q * dt
        
        # Loop spaziale per Differenze Finite (Cap. 5 Tesi)
        for i in range(1, N-1):
            for j in range(1, N-1):
                if muri[i,j] == 1:
                    C_new[i,j] = 0
                    continue
                
                # Formula ADR discretizzata
                diff = K * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u * dt * (C[i,j] - C[i-1,j]) # Schema Upwind
                reac = -(kp_val * sol) * dt * C[i,j]
                
                C_new[i,j] += diff + adv + reac

        C = np.clip(C_new, 0, 100)
        
        # Aggiornamento grafico
        if t % 15 == 0:
            picco = np.max(C[20:45, 10:40]) * 0.13
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='Reds'),
                go.Surface(z=muri * 2.5, colorscale='Greys', opacity=0.3, showscale=False)
            ])
            fig.update_layout(scene=dict(zaxis=dict(range=[0, 15])), margin=dict(l=0, r=0, b=0, t=0))
            grafico.plotly_chart(fig, use_container_width=True)
            
            if picco > soglia:
                alert.error(f"ALLERTA: {picco:.3f} ppm (Limite: {soglia})")
            else:
                alert.success(f"NORMALE: {picco:.3f} ppm")

    # --- EXCEL FINALE ---
    p_fin = np.max(C[20:45, 10:40]) * 0.13
    df = pd.DataFrame({
        "Parametro": ["Sostanza", "Meteo", "Vento", "Pioggia", "Picco PPM"],
        "Valore": [gas, meteo, u, pioggia, round(p_fin, 4)]
    })
    
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    
    st.sidebar.download_button(
        label="Scarica Excel",
        data=buf.getvalue(),
        file_name="report_sim.xlsx",
        mime="application/vnd.ms-excel"
    )
