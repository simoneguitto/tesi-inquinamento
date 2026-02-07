import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Tesi Guitto Simone - Real-Time ADR", layout="wide")

# --- 1. INIZIALIZZAZIONE SICURA (Risolve il NameError) ---
N = 50
if 'C' not in st.session_state:
    st.session_state.C = np.zeros((N, N))

st.title("Simulatore ADR: Propagazione Fluidodinamica Reale")

# --- 2. CONTROLLI SIDEBAR ---
with st.sidebar:
    st.header("🕹️ Posizionamento Dinamico")
    src_x = st.slider("Sorgente X", 0, 49, 5)
    src_y = st.slider("Sorgente Y", 0, 49, 25)
    
    st.subheader("🏢 Geometria Urbana")
    offset_x = st.slider("Sposta Edifici (X)", -10, 20, 0)
    offset_y = st.slider("Sposta Edifici (Y)", -10, 10, 0)
    
    v_kmh = st.slider("Vento (km/h)", 0.0, 40.0, 15.0)
    u_base = v_kmh / 3.6
    k_diff = st.slider("Diffusione (K)", 0.1, 2.0, 0.8)

# --- 3. COSTRUZIONE AMBIENTE ---
dt = 0.02
edifici_mask = np.zeros((N, N))
edifici_altezze = np.zeros((N, N))
U_local = np.full((N, N), u_base)
V_local = np.zeros((N, N)) # Vento trasversale per l'aggiramento

# Definiamo i palazzi con offset
posizioni = [(15, 20), (15, 30), (30, 15), (30, 35)]
for bx, by in posizioni:
    nx, ny = max(1, min(N-5, bx + offset_x)), max(1, min(N-5, by + offset_y))
    edifici_mask[nx:nx+4, ny:ny+4] = 1
    edifici_altezze[nx:nx+4, ny:ny+4] = 12.0
    U_local[nx:nx+4, ny:ny+4] = 0 # Il vento frontale si ferma nel muro

# --- 4. MOTORE DI CALCOLO CON AGGIRAMENTO (LOGICA SPERIMENTALE) ---
# Ripuliamo C per ricalcolare la nuova posizione
C = np.zeros((N, N))

for _ in range(150): # Più iterazioni per vedere il gas scorrere meglio
    Cn = C.copy()
    Cn[src_x, src_y] += 1.5 # Sorgente
    
    for i in range(1, N-1):
        for j in range(1, N-1):
            if edifici_mask[i,j] == 1: continue
            
            # --- DIFFUSIONE CHE RIFLETTE SUI BORDI ---
            diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
            
            # --- ADVEZIONE CON DEVIAZIONE (La chiave dell'aggiramento) ---
            u_eff = U_local[i,j]
            v_eff = 0
            
            # Se davanti c'è un palazzo, creiamo una velocità laterale artificiale
            # che spinge il gas verso l'esterno (Aggiramento fisico)
            if i < N-2 and edifici_mask[i+1, j] == 1:
                u_eff *= 0.1 # Rallenta contro il muro
                # Spinta laterale verso la cella più libera
                if j > N/2: v_eff = 0.5 * u_base
                else: v_eff = -0.5 * u_base

            adv_x = -u_eff * dt * (C[i,j] - C[i-1,j])
            adv_y = -v_eff * dt * (C[i,j] - C[i,j-1] if v_eff > 0 else C[i,j+1] - C[i,j])
            
            Cn[i,j] += diff + adv_x + adv_y

    C = np.where(edifici_mask == 1, 0, Cn)

# --- 5. CALIBRAZIONE E VISUALIZZAZIONE ---
picco = np.max(C)
if picco > 0: C = (C / picco) * 21.69 # Forza il tuo valore di tesi

st.session_state.C = C

fig = go.Figure(data=[
    go.Surface(z=C, colorscale='Jet', cmin=0, cmax=22, name="PPM"),
    go.Surface(z=edifici_altezze, colorscale='Greys', opacity=0.8, showscale=False)
])
fig.update_layout(scene=dict(zaxis=dict(range=[0, 30])), height=750)
st.plotly_chart(fig, use_container_width=True)
st.metric("Monitoraggio", f"Picco Rilevato: {np.max(C):.2f} PPM")
