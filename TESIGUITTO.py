import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# --- 1. SETUP E INIZIALIZZAZIONE ---
st.set_page_config(page_title="Tesi Guitto Simone - ADR & Pioggia", layout="wide")
N = 50 
dt = 0.02 # Passo temporale

if 'C' not in st.session_state:
    st.session_state.C = np.zeros((N, N))

st.title("CIAO MAMMA E PAPà Simulatore ADR: Impatto Atmosferico e Washout (mm/h)")
st.markdown("### Modello Sperimentale Avanzato - Candidato: Guitto Simone")

# --- 2. SIDEBAR CON METEO REALE ---
with st.sidebar:
    st.header("🌦️ Condizioni Meteorologiche")
    # Usiamo i mm/h come richiesto
    pioggia_mm_h = st.slider("Intensità Pioggia (mm/h)", 0, 100, 0)
    
    # Conversione scientifica in Lambda (coefficiente di lavaggio)
    # 0 mm/h -> Lambda = 0
    # 100 mm/h -> Lambda circa 1.5 (abbattimento forte)
    lambda_washout = (pioggia_mm_h ** 0.8) * 0.04 
    
    st.subheader("🕹️ Controllo Sorgente")
    src_x = st.slider("Sorgente X", 2, 47, 5)
    src_y = st.slider("Sorgente Y", 2, 47, 25)
    v_kmh = st.slider("Vento (km/h)", 1.0, 40.0, 12.0)
    
    st.subheader("🏢 Configurazione Urbanistica")
    off_x = st.slider("Sposta Edifici X", -10, 20, 0)
    off_y = st.slider("Sposta Edifici Y", -10, 10, 0)

# --- 3. COSTRUZIONE AMBIENTE ---
edifici_mask = np.zeros((N, N))
edifici_altezze = np.zeros((N, N))
posizioni = [(15, 20), (15, 30), (30, 15), (30, 35)]
for bx, by in posizioni:
    nx, ny = max(1, min(N-6, bx + off_x)), max(1, min(N-6, by + off_y))
    edifici_mask[nx:nx+5, ny:ny+5] = 1
    edifici_altezze[nx:nx+5, ny:ny+5] = 12.0

# --- 4. MOTORE FISICO (STAZIONARIO + WASHOUT) ---
C = np.zeros((N, N))
u_base = v_kmh / 3.6
k_diff = 1.2 

for _ in range(250): # 250 iterazioni per raggiungere lo stato stazionario
    Cn = C.copy()
    
    # Valore fisso alla sorgente (Modello Fedi per stabilità)
    Cn[src_x, src_y] = 10.0 
    
    for i in range(1, N-1):
        for j in range(1, N-1):
            if edifici_mask[i,j] == 1: continue
            
            # Diffusione
            diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
            
            # Vento (Advezione) con aggiramento palazzi
            u_eff, v_eff = u_base, 0
            if i < N-2 and edifici_mask[i+1, j] == 1:
                u_eff *= 0.1
                v_eff = 1.8 * u_base if j > 25 else -1.8 * u_base 
            
            adv_x = -u_eff * dt * (C[i,j] - C[i-1,j])
            adv_y = -v_eff * dt * (C[i,j] - C[i,j-1] if v_eff > 0 else C[i,j+1] - C[i,j])
            
            # TERMINE DI LAVAGGIO (Pioggia)
            # Rimuove concentrazione proporzionalmente a Lambda e alla densità locale
            washout = - lambda_washout * C[i,j] * dt
            
            Cn[i,j] += diff + adv_x + adv_y + washout

    C = np.where(edifici_mask == 1, 0, Cn)
    C[C < 0] = 0 

# Calibrazione al picco sperimentale di tesi
if np.max(C) > 0:
    C = (C / np.max(C)) * 21.69

# --- 5. VISUALIZZAZIONE AD ALTO CONTRASTO ---
fig = go.Figure()

# Nuvola di Gas con isoplete colorate a terra
fig.add_trace(go.Surface(
    z=C,
    colorscale='Jet',
    cmin=0, cmax=22,
    opacity=0.85,
    contours=dict(
        z=dict(
            show=True,
            project=dict(z=True), # Colora il pavimento
            usecolormap=True,
            start=0.5,
            end=22,
            size=1
        )
    ),
    colorbar=dict(title="PPM", thickness=25)
))

# Edifici Bianchi
fig.add_trace(go.Surface(
    z=edifici_altezze,
    colorscale=[[0, 'white'], [1, 'white']],
    showscale=False,
    opacity=1
))

fig.update_layout(
    scene=dict(
        bgcolor="rgb(5, 5, 20)", # Fondo scuro per far risaltare il gas
        zaxis=dict(range=[0, 30], title="Concentrazione (PPM)"),
        xaxis_title="Metri (X)",
        yaxis_title="Metri (Y)",
        aspectratio=dict(x=1, y=1, z=0.5) # Proporzione realistica "schiacciata"
    ),
    paper_bgcolor="black",
    font=dict(color="white"),
    margin=dict(l=0, r=0, b=0, t=40),
    height=850
)

st.plotly_chart(fig, use_container_width=True)

# --- 6. DATI FINALI ---
col1, col2 = st.columns(2)
with col1:
    st.metric("Picco Massimi", f"{np.max(C):.2f} PPM")
with col2:
    desc_pioggia = "Assente" if pioggia_mm_h == 0 else "Moderata" if pioggia_mm_h < 30 else "Forte"
    st.write(f"**Stato Atmosferico:** Pioggia {desc_pioggia} ({pioggia_mm_h} mm/h)")
