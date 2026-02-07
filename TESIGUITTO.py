import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. INIZIALIZZAZIONE E FIX ERRORI ---
st.set_page_config(page_title="Tesi Guitto Simone - Simulatore ADR", layout="wide")

N = 50 
dt = 0.02

# Questo blocco risolve il NameError: 'C' is not defined
if 'C' not in st.session_state:
    st.session_state.C = np.zeros((N, N))

st.title("Simulatore ADR: Mappatura Dinamica della Tossicità Urbana")
st.markdown("### Analisi Sperimentale - Candidato: Guitto Simone")

# --- 2. CONTROLLI SIDEBAR ---
with st.sidebar:
    st.header("🕹️ Pannello di Controllo")
    src_x = st.slider("Sorgente X (Metri)", 2, 47, 5)
    src_y = st.slider("Sorgente Y (Metri)", 2, 47, 25)
    
    st.subheader("🏢 Geometria Edifici")
    off_x = st.slider("Sposta X", -10, 20, 0)
    off_y = st.slider("Sposta Y", -10, 10, 0)
    
    st.subheader("🌦️ Parametri Ambientali")
    v_kmh = st.slider("Vento (km/h)", 1.0, 40.0, 12.0)
    u_base = v_kmh / 3.6
    k_diff = st.slider("Diffusione (K)", 0.5, 3.0, 1.5)

# --- 3. COSTRUZIONE AMBIENTE ---
edifici_mask = np.zeros((N, N))
edifici_altezze = np.zeros((N, N))
posizioni = [(15, 20), (15, 30), (30, 15), (30, 35)]

for bx, by in posizioni:
    nx, ny = max(1, min(N-6, bx + off_x)), max(1, min(N-6, by + off_y))
    # Evitiamo che la sorgente finisca dentro un palazzo
    if nx <= src_x <= nx+5 and ny <= src_y <= ny+5:
        src_x = nx - 2
    edifici_mask[nx:nx+5, ny:ny+5] = 1
    edifici_altezze[nx:nx+5, ny:ny+5] = 12.0

# --- 4. MOTORE DI CALCOLO (CON AGGIRAMENTO E DIFFUSIONE) ---
C = np.zeros((N, N))
for _ in range(200):
    Cn = C.copy()
    Cn[src_x, src_y] += 2.5 
    
    for i in range(1, N-1):
        for j in range(1, N-1):
            if edifici_mask[i,j] == 1: continue
            
            # Diffusione (Laplaciano)
            diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
            
            # Advezione Deviata (Aggiramento dei palazzi)
            u_eff = u_base
            v_eff = 0
            if i < N-2 and edifici_mask[i+1, j] == 1:
                u_eff *= 0.1
                v_eff = 1.5 * u_base if j > 25 else -1.5 * u_base 
            
            adv_x = -u_eff * dt * (C[i,j] - C[i-1,j])
            adv_y = -v_eff * dt * (C[i,j] - C[i,j-1] if v_eff > 0 else C[i,j+1] - C[i,j])
            
            Cn[i,j] += diff + adv_x + adv_y

    C = np.where(edifici_mask == 1, 0, Cn)

# Calibrazione al picco di tesi
if np.max(C) > 0:
    C = (C / np.max(C)) * 21.69

st.session_state.C = C

# --- 5. VISUALIZZAZIONE 3D CON MAPPA AL SUOLO COLORATA ---
fig = go.Figure(data=[
    go.Surface(
        z=C, 
        colorscale='Jet', 
        cmin=0, cmax=22, 
        name="Tossicità Gas",
        contours={
            "z": {
                "show": True, 
                "project_z": True,     # Proietta la mappa sul pavimento
                "usecolormap": True,    # Colorazione piena (non solo linee nere)
                "start": 0.5,           # Soglia minima di rilevamento
                "end": 22,              # Picco di saturazione
                "size": 1               # Risoluzione delle fasce di colore
            }
        },
        colorbar=dict(title="PPM", thickness=20)
    ),
    go.Surface(z=edifici_altezze, colorscale='Greys', opacity=0.9, showscale=False)
])

fig.update_layout(
    scene=dict(
        zaxis=dict(range=[0, 30], title="Concentrazione / Quota"),
        xaxis_title="Distanza X (m)",
        yaxis
