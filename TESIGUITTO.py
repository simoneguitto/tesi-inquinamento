import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Editor Dispersione Dinamico", layout="wide")
st.title("Simulatore Meteorologico Interattivo")
st.write("Configura la topografia e l'orografia per analizzare la dispersione del gas.")

# --- SIDEBAR: CONTROLLO SCENARIO (EDITOR) ---
st.sidebar.header("🕹️ Editor Ostacoli")

# Controlli per il Palazzo
st.sidebar.subheader("Posizione Palazzo")
pal_x = st.sidebar.slider("Distanza Palazzo (X)", 10, 40, 15)
pal_y = st.sidebar.slider("Spostamento Laterale (Y)", 10, 40, 25)

# Controlli per la Collina
st.sidebar.subheader("Configurazione Collina")
col_x = st.sidebar.slider("Posizione Collina (X)", 10, 45, 40)
col_y = st.sidebar.slider("Posizione Collina (Y)", 10, 45, 25)
col_h = st.sidebar.slider("Altezza Collina", 1.0, 8.0, 5.0)

st.sidebar.header("🌦️ Parametri Meteo")
clima = st.sidebar.selectbox("Stabilità", ["Giorno", "Standard", "Inversione"])
u_v = 1.0 if clima == "Giorno" else (1.5 if clima == "Standard" else 0.6)
k_v = 1.8 if clima == "Giorno" else (1.0 if clima == "Standard" else 0.3)

u_vento = st.sidebar.slider("Velocità Vento", 0.1, 5.0, u_v)
k_diff = st.sidebar.slider("Diffusione (K)", 0.1, 2.5, k_v)

# --- CREAZIONE MAPPA DINAMICA ---
N = 50
dx, dt = 1.0, 0.02
edifici = np.zeros((N, N))
orografia = np.zeros((N, N))

# Posizionamento dinamico Palazzo (3x3 nodi)
edifici[pal_x:pal_x+4, pal_y-2:pal_y+2] = 1

# Posizionamento dinamico Collina (Gaussiana)
for i in range(N):
    for j in range(N):
        dist = np.sqrt((i-col_x)**2 + (j-col_y)**2)
        if dist < 12:
            orografia[i,j] = col_h * np.exp(-0.06 * dist**2)

# --- MOTORE DI CALCOLO ---
if st.sidebar.button("AVVIA SIMULAZIONE DINAMICA"):
    C = np.zeros((N, N))
    mappa_box = st.empty()
    testo_box = st.empty()
    sx, sy = 5, 25 # Sorgente fissa

    for t in range(160):
        Cn = C.copy()
        Cn[sx, sy] += 150 * dt 
        
        for i in range(1, N-1):
            for j in range(1, N-1):
                if edifici[i,j] == 1: continue
                
                # Formula ADR
                diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u_vento * dt * (C[i,j] - C[i-1,j])
                Cn[i,j] += diff + adv

        C = np.where(edifici == 1, 0, Cn)
        C = np.clip(C, 0, 100)
        
        if t % 15 == 0:
            picco = np.max(C) * 0.15
            fig = go.Figure(data=[
                go.Surface(z=C + orografia, colorscale='Jet', cmin=0.01, cmax=12, name="Gas"),
                go.Surface(z=edifici * 4.0, colorscale='Greys', opacity=0.9, showscale=False),
                go.Surface(z=orografia, colorscale='Greens', opacity=0.3, showscale=False)
            ])
            fig.update_layout(scene=dict(zaxis=dict(range=[0, 15])), margin=dict(l=0, r=0, b=0, t=0), height=700)
            mappa_box.plotly_chart(fig, use_container_width=True)
            
            if picco > 0.1: testo_box.error(f"SOGLIA SUPERATA: {picco:.4f} ppm")
            else: testo_box.success(f"STATO SICURO: {picco:.4f} ppm")

    st.info("Simulazione completata con la configurazione personalizzata.")
