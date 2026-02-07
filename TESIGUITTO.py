import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="Tesi Guitto Simone - Analisi Finale", layout="wide")
N = 50 
dt = 0.02

if 'C' not in st.session_state:
    st.session_state.C = np.zeros((N, N))

st.title("Simulatore ADR: Visualizzazione Avanzata Tossicità")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🕹️ Parametri")
    src_x = st.slider("Sorgente X", 2, 47, 5)
    src_y = st.slider("Sorgente Y", 2, 47, 25)
    v_kmh = st.slider("Vento (km/h)", 1.0, 40.0, 10.0)
    k_diff = st.slider("Diffusione (K)", 0.5, 3.0, 1.5)
    st.subheader("🏢 Edifici")
    off_x = st.slider("Sposta X", -10, 20, 0)
    off_y = st.slider("Sposta Y", -10, 10, 0)

# --- 3. AMBIENTE E CALCOLO ---
edifici_mask = np.zeros((N, N))
edifici_altezze = np.zeros((N, N))
posizioni = [(15, 20), (15, 30), (30, 15), (30, 35)]
for bx, by in posizioni:
    nx, ny = max(1, min(N-6, bx + off_x)), max(1, min(N-6, by + off_y))
    edifici_mask[nx:nx+5, ny:ny+5] = 1
    edifici_altezze[nx:nx+5, ny:ny+5] = 12.0

C = np.zeros((N, N))
u_base = v_kmh / 3.6

for _ in range(250):
    Cn = C.copy()
    Cn[src_x, src_y] += 2.5
    for i in range(1, N-1):
        for j in range(1, N-1):
            if edifici_mask[i,j] == 1: continue
            u_eff, v_eff = u_base, 0
            if i < N-2 and edifici_mask[i+1, j] == 1:
                u_eff *= 0.1
                v_eff = 1.8 * u_base if j > 25 else -1.8 * u_base 
            
            diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
            adv_x = -u_eff * dt * (C[i,j] - C[i-1,j])
            adv_y = -v_eff * dt * (C[i,j] - C[i,j-1] if v_eff > 0 else C[i,j+1] - C[i,j])
            Cn[i,j] += diff + adv_x + adv_y
    C = np.where(edifici_mask == 1, 0, Cn)

if np.max(C) > 0:
    C = (C / np.max(C)) * 21.69

# --- 5. IL TRUCCO PER LE CURVE COLORATE ---
fig = go.Figure()

# Aggiungiamo la superficie del gas con COLORAZIONE PIENA
fig.add_trace(go.Surface(
    z=C,
    colorscale='Jet',
    cmin=0, cmax=22,
    opacity=0.8, # Un po' di trasparenza aiuta a vedere il fondo
    contours=dict(
        z=dict(
            show=True,
            usecolormap=True,
            highlightcolor="limegreen",
            project=dict(z=True), # Forza la proiezione
            start=0.1,
            end=22,
            size=1
        )
    ),
    colorbar=dict(title="PPM")
))

# Aggiungiamo gli edifici
fig.add_trace(go.Surface(
    z=edifici_altezze,
    colorscale=[[0, 'rgb(200,200,200)'], [1, 'rgb(255,255,255)']],
    showscale=False,
    opacity=1
))

fig.update_layout(
    scene=dict(
        zaxis=dict(range=[0, 30]),
        # Questo forza la visuale a non schiacciare le curve
        aspectmode='manual',
        aspectratio=dict(x=1, y=1, z=0.5)
    ),
    height=800
)

st.plotly_chart(fig, use_container_width=True)
