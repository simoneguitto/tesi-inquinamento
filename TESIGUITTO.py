import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO

# Configurazione base
st.set_page_config(page_title="Modello ADR Urban", layout="wide")
st.title("Simulazione Dispersione Inquinanti (Metodo ADR)")

# --- INPUT ---
st.sidebar.header("Parametri")
meteo = st.sidebar.selectbox("Stabilità", ["Instabile", "Neutro", "Inversione"])
pioggia_lvl = st.sidebar.select_slider("Pioggia", options=["Zero", "Bassa", "Alta"])

# Valori basati sulla tesi di Fedi
if meteo == "Instabile": D_val, u_val = 1.7, 0.8
elif meteo == "Neutro": D_val, u_val = 1.0, 1.5
else: D_val, u_val = 0.2, 0.4

u = st.sidebar.slider("Vento (u) [m/s]", 0.1, 5.0, u_val)
D = st.sidebar.slider("Diffusione (K)", 0.1, 2.5, D_val)

gas_tipo = st.sidebar.selectbox("Sostanza", ["Tossico (MIC)", "NO2", "CO"])
if gas_tipo == "Tossico (MIC)": soglia, sol = 0.05, 1.0
elif gas_tipo == "NO2": soglia, sol = 0.1, 0.7
else: soglia, sol = 9.0, 0.3

Q = st.sidebar.slider("Emissione (Q)", 50, 250, 120)

# --- GRIGLIA E COSTANTI ---
N = 50
dx = 1.0
dt = 0.04  # Passo temporale stabile

# Fattore pioggia (k)
kp_map = {"Zero": 0.0, "Bassa": 0.08, "Alta": 0.25}
k_p = kp_map[pioggia_lvl]

# Edifici (Orografia urbana)
ostacoli = np.zeros((N, N))
np.random.seed(42)
for _ in range(10):
    ix, iy = np.random.randint(20, 45), np.random.randint(10, 40)
    ostacoli[ix:ix+3, iy:iy+3] = 1

# --- ESECUZIONE ---
if st.sidebar.button("AVVIA SIMULAZIONE"):
    C = np.zeros((N, N))
    mappa = st.empty()
    testo = st.empty()
    
    # Sorgente
    sx, sy = 10, 25

    for t in range(140):
        Cn = C.copy()
        Cn[sx, sy] += Q * dt
        
        # Calcolo ADR (Advezione-Diffusione-Reazione)
        # Usiamo indici 1:-1 per non toccare i bordi e dare errore
        for i in range(1, N-1):
            for j in range(1, N-1):
                if ostacoli[i,j] == 1:
                    Cn[i,j] = 0
                    continue
                
                # Formula discretizzata (Simile a Cap. 5 tesi Fedi)
                diff = D * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u * dt * (C[i,j] - C[i-1,j]) # Upwind
                reac = -(k_p * sol) * dt * C[i,j]
                
                Cn[i,j] += diff + adv + reac

        C = np.clip(Cn, 0, 100)
        
        if t % 15 == 0:
            picco = np.max(C[20:45, 10:40]) * 0.13
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='YlOrRd'),
                go.Surface(z=ostacoli * 2.5, colorscale='Greys', opacity=0.4, showscale=False)
            ])
            fig.update_layout(scene=dict(zaxis=dict(range=[0, 15])), margin=dict(l=0, r=0, b=0, t=0))
            mappa.plotly_chart(fig, use_container_width=True)
            
            if picco > soglia:
                testo.error(f"SOGLIA SUPERATA: {picco:.4f} ppm")
            else:
                testo.success(f"LIVELLI SICURI: {picco:.4f} ppm")

    # --- REPORT FINALE ---
    p_f = np.max(C[20:45, 10:40]) * 0.13
    esito = "PERICOLO" if p_f > soglia else "OK"
    
    df = pd.DataFrame({
        "Parametro": ["Gas", "Meteo", "Pioggia", "Vento", "Picco ppm", "Esito"],
        "Valore": [gas_tipo, meteo, pioggia_lvl, u, round(p_f, 4), esito]
    })
    
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    
    st.sidebar.download_button(
        label="Scarica Dati Excel",
        data=buf.getvalue(),
        file_name="risultati_simulazione.xlsx",
        mime="application/vnd.ms-excel"
    )
