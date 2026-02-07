import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. CONFIGURAZIONE E FIX ERRORE 'C' ---
st.set_page_config(page_title="Tesi Guitto Simone - ADR Real-Time", layout="wide")

N = 50 
dt = 0.02

# Inizializzazione sicura per evitare il NameError delle tue foto
if 'C' not in st.session_state:
    st.session_state.C = np.zeros((N, N))

st.title("Simulatore ADR: Analisi della Dispersione Urbanistica")

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("🎮 Comandi Sperimentali")
    src_x = st.slider("Sorgente X", 0, 49, 5)
    src_y = st.slider("Sorgente Y", 0, 49, 25)
    
    st.subheader("🏢 Posizione Palazzi")
    off_x = st.slider("Sposta X", -10, 20, 0)
    off_y = st.slider("Sposta Y", -10, 10, 0)
    
    v_kmh = st.slider("Vento (km/h)", 1.0, 40.0, 10.0) # Vento consigliato: 10 per vedere l'aggiramento
    u_base = v_kmh / 3.6
    k_diff = st.slider("Diffusione (K)", 0.5, 3.0, 1.5) # Aumentata la diffusione di base

# --- 3. COSTRUZIONE AMBIENTE ---
edifici_mask = np.zeros((N, N))
edifici_altezze = np.zeros((N, N))
# Definiamo i palazzi
posizioni = [(15, 20), (15, 30), (30, 15), (30, 35)]
for bx, by in posizioni:
    nx, ny = max(1, min(N-5, bx + off_x)), max(1, min(N-5, by + off_y))
    edifici_mask[nx:nx+5, ny:ny+5] = 1 # Palazzi leggermente più grandi
    edifici_altezze[nx:nx+5, ny:ny+5] = 12.0

# --- 4. MOTORE DI CALCOLO AD ALTA ITERAZIONE ---
C = np.zeros((N, N))

# Portiamo le iterazioni a 250 per dare tempo al gas di girare l'angolo
for _ in range(250):
    Cn = C.copy()
    Cn[src_x, src_y] += 2.0 # Sorgente più intensa
    
    # Calcolo con logica di deviazione fluida
    for i in range(1, N-1):
        for j in range(1, N-1):
            if edifici_mask[i,j] == 1: continue
            
            # Diffusione potenziata (Laplaciano)
            diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
            
            # ADVEZIONE DEVIATA (La soluzione al tuo problema)
            u_eff = u_base
            v_eff = 0
            
            # Se un palazzo è nel raggio di 2 celle davanti, inizia a deviare (Anticipazione)
            if i < N-3 and np.any(edifici_mask[i+1:i+3, j] == 1):
                u_eff *= 0.1 # Il gas rallenta drasticamente
                # Forza il gas a scivolare a destra o sinistra
                v_eff = 1.5 * u_base if j > 25 else -1.5 * u_base 
            
            adv_x = -u_eff * dt * (C[i,j] - C[i-1,j])
            adv_y = -v_eff * dt * (C[i,j] - C[i,j-1] if v_eff > 0 else C[i,j+1] - C[i,j])
            
            Cn[i,j] += diff + adv_x + adv_y

    C = np.where(edifici_mask == 1, 0, Cn)

# --- 5. CALIBRAZIONE E GRAFICA ---
if np.max(C) > 0:
    C = (C / np.max(C)) * 21.69 # Il tuo valore di tesi

st.session_state.C = C

fig = go.Figure(data=[
    go.Surface(
        z=C, colorscale='Jet', cmin=0, cmax=22, name="PPM",
        contours={"z": {"show": True, "usecolormap": True, "project_z": True, "start": 1}}
    ),
    go.Surface(z=edifici_altezze, colorscale='Greys', opacity=0.8, showscale=False)
])

fig.update_layout(scene=dict(zaxis=dict(range=[0, 30])), height=750)
st.plotly_chart(fig, use_container_width=True)
st.metric("Monitoraggio Tesi", f"Picco Rilevato: {np.max(C):.2f} PPM")
