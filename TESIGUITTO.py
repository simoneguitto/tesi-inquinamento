import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Tesi Guitto Simone - Simulatore ADR", layout="wide")

# --- INTESTAZIONE ACCADEMICA ---
st.title("Sistema Integrato di Simulazione Dispersione Atmosferica")
st.markdown("""
### Analisi fluidodinamica e monitoraggio PPM (Modello Sperimentale)
**Ingegneria Civile e Ambientale - Università Uninettuno**
""")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🏢 Parametri Urbanistici")
    num_palazzi = st.slider("Numero edifici", 0, 15, 8) # Aumentato per test più complessi
    
    st.header("🌦️ Variabili Ambientali")
    v_kmh = st.slider("Vento (km/h)", 1.0, 40.0, 12.0)
    u_base = v_kmh / 3.6 
    k_diff = st.slider("Diffusione (K)", 0.1, 2.5, 0.8)
    mm_pioggia = st.slider("Pioggia (mm/h)", 0, 100, 0)

# --- LOGICA MATEMATICA AVANZATA ---
N = 50
dt = 0.02
sigma_pioggia = (mm_pioggia / 100) * 0.4 

# Inizializzazione matrici
edifici_mask = np.zeros((N, N))
edifici_altezze = np.zeros((N, N))
# MATRICE VELOCITÀ LOCALE (Il vento che devia)
U_local = np.full((N, N), u_base) 

# Posizionamento Edifici (Random ma coerente)
np.random.seed(42)
for _ in range(num_palazzi):
    px, py = np.random.randint(12, 45), np.random.randint(5, 45)
    w, h_ed = np.random.randint(3, 6), np.random.choice([5.0, 10.0, 15.0])
    edifici_mask[px:px+w, py:py+w] = 1
    edifici_altezze[px:px+w, py:py+w] = h_ed
    # EFFETTO SPERIMENTALE: Il vento si annulla dentro il palazzo 
    # e accelera ai lati (effetto Venturi semplificato)
    U_local[px:px+w, py:py+w] = 0 
    if px > 0: U_local[px-1, py:py+w] *= 1.2 # Accelerazione laterale

# --- ESECUZIONE SIMULAZIONE ---
if st.sidebar.button("AVVIA SIMULAZIONE SPERIMENTALE"):
    C = np.zeros((N, N))
    mappa_box = st.empty()
    testo_box = st.empty()
    sx, sy = 5, 25 # Sorgente

    for t in range(200): # Aumentato per stabilità
        Cn = C.copy()
        # RILASCIO COSTANTE (Calibrato per raggiungere i ~21 PPM in accumulo)
        Cn[sx, sy] += 45 * dt 
        
        # Algoritmo ADR con Vento Variabile
        for i in range(1, N-1):
            for j in range(1, N-1):
                if edifici_mask[i,j] == 1:
                    Cn[i,j] = 0
                    continue
                
                # Diffusione (Laplaciano)
                diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                # Advezione Deviata (Usa la velocità locale U_local)
                adv = -U_local[i,j] * dt * (C[i,j] - C[i-1,j])
                # Reazione (Pioggia)
                reac = -sigma_pioggia * dt * C[i,j]
                
                Cn[i,j] += diff + adv + reac
        
        C = Cn.copy()
        
        if t % 20 == 0:
            picco = np.max(C)
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='Jet', cmin=0, cmax=22, name="PPM"),
                go.Surface(z=edifici_altezze, colorscale='Greys', opacity=0.7, showscale=False)
            ])
            fig.update_layout(scene=dict(zaxis=dict(range=[0, 25])), height=700)
            mappa_box.plotly_chart(fig, use_container_width=True)
            testo_box.warning(f"⚠️ Rilevazione Critica: {picco:.2f} PPM")

    st.success("Sperimentazione conclusa con successo.")
    
    # EXPORT DATI
    df = pd.DataFrame([
        {"X": i, "Y": j, "PPM": round(C[i,j], 2)} 
        for i in range(N) for j in range(N) if C[i,j] > 0.1
    ])
    st.download_button("💾 SCARICA REPORT SPERIMENTALE (CSV)", df.to_csv().encode('utf-8'), "dati_tesi.csv")
