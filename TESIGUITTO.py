import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Simulatore ADR Urban", layout="wide")
st.title("Analisi Dispersione Inquinanti - Modello ADR")

# --- INPUT LATERALI ---
st.sidebar.header("Parametri Ambiente")

meteo_scelta = st.sidebar.selectbox("Stabilità Aria", ["Instabile", "Neutro", "Inversione"])
pioggia_livello = st.sidebar.select_slider("Pioggia", options=["Zero", "Leggera", "Media", "Forte"])

# Parametri fisici derivati dalla tesi (u=vento, D=diffusione)
if meteo_scelta == "Instabile":
    D_base, u_base = 1.8, 0.8
elif meteo_scelta == "Neutro":
    D_base, u_base = 1.0, 1.5
else:
    D_base, u_base = 0.2, 0.4

u = st.sidebar.slider("Vento (u) [m/s]", 0.1, 5.0, u_base)
D = st.sidebar.slider("Diffusione (K)", 0.1, 2.5, D_base)

st.sidebar.header("Sostanza")
gas = st.sidebar.selectbox("Tipo Gas", ["Tossico (MIC)", "NO2", "CO"])

# Soglie e solubilità per il lavaggio pioggia
if gas == "Tossico (MIC)":
    limite, solub = 0.05, 1.0
elif gas == "NO2":
    limite, solub = 0.1, 0.8
else:
    limite, solub = 9.0, 0.3 # Il CO si lava meno

Q = st.sidebar.slider("Emissione (Q)", 50, 250, 120)

# --- MOTORE DI CALCOLO ---
N = 50 
dx = 1.0
dt = 0.04 # Passo temporale fisso o quasi per stabilità

# Coefficienti pioggia
k_p = {"Zero": 0.0, "Leggera": 0.06, "Media": 0.15, "Forte": 0.3}[pioggia_livello]

# Matrice edifici (1 = muro, 0 = aria)
edifici = np.zeros((N, N))
np.random.seed(42)
for _ in range(12):
    x_e, y_e = np.random.randint(18, 45), np.random.randint(10, 40)
    edifici[x_e:x_e+3, y_e:y_e+3] = 1

def run_sim():
    C = np.zeros((N, N))
    mappa = st.empty()
    testo_risultato = st.empty()
    
    # Sorgente (x, y)
    sx, sy = 10, 25

    for t in range(150):
        Cn = C.copy()
        Cn[sx, sy] += Q * dt
        
        # Loop spaziale (Equazione ADR discretizzata)
        for i in range(1, N-1):
            for j in range(1, N-1):
                if edifici[i,j] == 1:
                    Cn[i,j] = 0
                    continue
                
                # Differenze finite (Advezione Upwind + Diffusione Centrale)
                diff = D * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u * dt * (C[i,j] - C[i-1,j])
                reac = -(k_p * solub) * dt * C[i,j]
                
                Cn[i,j] += diff + adv + reac

        C = np.clip(Cn, 0, 100)
        
        if t % 15 == 0:
            picco = np.max(C[20:45, 10:40]) * 0.13
            
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='YlOrRd'),
                go.Surface(z=edifici * 2, colorscale='Greys', opacity=0.5, showscale=False)
            ])
            fig.update_layout(scene=dict(zaxis=dict(range=[0, 15])), margin=dict(l=0, r=0, b=0, t=0))
            mappa.plotly_chart(fig, use_container_width=True)
            
            if picco > limite:
                testo_risultato.error(f"Soglia Superata: {picco:.3f} / {limite}")
            else:
                testo_risultato.success(f"Livelli ok: {picco:.3f} / {limite}")

    # Fine: Excel di riepilogo
    p_fin = np.max(C[20:45, 10:40]) * 0.13
    res_fin = "ALLERTA" if p_fin > limite else "OK"
    
    df = pd.DataFrame({
        "Parametro": ["Gas", "Meteo", "Vento", "Pioggia", "Picco", "Esito"],
        "Valore": [gas, meteo_scelta, u, pioggia_livello, f"{p_fin:.4f}", res_fin]
    })
    
    out = BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    
    st.sidebar.download_button("Scarica Excel", out.getvalue(), "dati_tesi.xlsx")

if st.sidebar.button("CALCOLA"):
    run_sim()
