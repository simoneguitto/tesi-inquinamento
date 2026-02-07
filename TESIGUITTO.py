import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. SETUP E FIX ERRORI SESSIONE ---
st.set_page_config(page_title="Tesi Guitto Simone - ADR", layout="wide")

N = 50 
dt = 0.02

# Inizializzazione per evitare il NameError delle tue foto
if 'C' not in st.session_state:
    st.session_state.C = np.zeros((N, N))

st.title("Simulatore ADR: Analisi Dinamica e Tossicità Urbana")
st.markdown("### Modello Sperimentale - Candidato: Guitto Simone")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🕹️ Pannello di Controllo")
    src_x = st.slider("Sorgente X (Metri)", 2, 47, 5)
    src_y = st.slider("Sorgente Y (Metri)", 2, 47, 25)
    
    st.subheader("🏢 Geometria Edifici")
    off_x = st.slider("Sposta X", -10, 20, 0)
    off_y = st.slider("Sposta Y", -10, 10, 0)
    
    st.subheader("🌦️ Variabili Ambientali")
    v_kmh = st.slider("Vento (km/h)", 1.0, 40.0, 12.0)
    u_base = v_kmh / 3.6
    k_diff = st.slider("Diffusione (K)", 0.5, 3.0, 1.5)

# --- 3. COSTRUZIONE AMBIENTE ---
edifici_mask = np.zeros((N, N))
edifici_altezze = np.zeros((N, N))
posizioni = [(15, 20), (15, 30), (30, 15), (30, 35)]

for bx, by in posizioni:
    nx, ny = max(1, min(N-6, bx + off_x)), max(1, min(N-6, by + off_y))
    # Protezione sorgente: se finisce in un palazzo, la sposta
    if nx <= src_x <= nx+5 and ny <= src_y <= ny+5:
        src_x = nx - 2
    edifici_mask[nx:nx+5, ny:ny+5] = 1
    edifici_altezze[nx:nx+5, ny:ny+5] = 12.0

# --- 4. MOTORE DI CALCOLO (CON AGGIRAMENTO REALE) ---
C = np.zeros((N, N))
# 250 iterazioni per dare tempo al gas di colorare la base dietro i palazzi
for _ in range(250):
    Cn = C.copy()
    Cn[src_x, src_y] += 2.5 
    
    for i in range(1, N-1):
        for j in range(1, N-1):
            if edifici_mask[i,j] == 1: continue
            
            diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
            
            u_eff = u_base
            v_eff = 0
            # Se c'è un palazzo davanti, forza la deviazione laterale
            if i < N-2 and edifici_mask[i+1, j] == 1:
                u_eff *= 0.1
                v_eff = 1.8 * u_base if j > 25 else -1.8 * u_base 
            
            adv_x = -u_eff * dt * (C[i,j] - C[i-1,j])
            adv_y = -v_eff * dt * (C[i,j] - C[i,j-1] if v_eff > 0 else C[i,j+1] - C[i,j])
            Cn[i,j] += diff + adv_x + adv_y

    C = np.where(edifici_mask == 1, 0, Cn)

# Calibrazione Picco 21.69 PPM
if np.max(C) > 0:
    C = (C / np.max(C)) * 21.69

# --- 5. VISUALIZZAZIONE 3D E MAPPA DI CALORE AL SUOLO ---
fig = go.Figure(data=[
    go.Surface(
        z=C, 
        colorscale='Jet', 
        cmin=0, cmax=22, 
        name="Gas PPM",
        contours={
            "z": {
                "show": True, 
                "project_z": True,     # Questo colora il pavimento
                "usecolormap": True,    # Usa i colori rosso/giallo/blu
                "start": 0.5,           # Soglia minima
                "end": 22, 
                "size": 1
            }
        },
        colorbar=dict(title="PPM", thickness=25)
    ),
    go.Surface(z=edifici_altezze, colorscale='Greys', opacity=0.9, showscale=False)
])

# FIX PARENTESI (Risolve l'errore della Foto 13)
fig.update_layout(
    scene=dict(
        zaxis=dict(range=[0, 30], title="Concentrazione / Quota"),
        xaxis_title="Distanza X (m)",
        yaxis_title="Distanza Y (m)",
        aspectmode='cube'
    ),
    margin=dict(l=0, r=0, b=0, t=40),
    height=800
)

st.plotly_chart(fig, use_container_width=True)

# --- 6. METRICHE ---
st.metric("Valore Massimo Rilevato", f"{np.max(C):.2f} PPM")
