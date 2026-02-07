import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Laboratorio ADR Dinamico", layout="wide")
st.title("Simulatore Meteorologico: Editor Multi-Ostacolo")
st.write("Configura la densità urbana e orografica per analizzare la dispersione del gas.")

# --- SIDEBAR: CONTROLLO SCENARIO ---
st.sidebar.header("🏢 Configurazione Urbanistica")
num_palazzi = st.sidebar.slider("Numero di Palazzi", 0, 10, 3)
dist_primo_palazzo = st.sidebar.slider("Distanza Primo Palazzo (X)", 8, 20, 12)

st.sidebar.header("⛰️ Configurazione Orografica")
num_colline = st.sidebar.slider("Numero di Colline", 0, 5, 2)
altezza_max_colline = st.sidebar.slider("Altezza Massima Rilievi", 2.0, 10.0, 5.0)

st.sidebar.header("🌦️ Parametri Atmosferici")
clima = st.sidebar.selectbox("Stabilità Aria", ["Giorno (Turbolento)", "Standard", "Inversione (Ristagno)"])
u_v = 1.0 if clima == "Giorno (Turbolento)" else (1.5 if clima == "Standard" else 0.6)
k_v = 1.8 if clima == "Giorno (Turbolento)" else (1.0 if clima == "Standard" else 0.3)

u_vento = st.sidebar.slider("Velocità Vento", 0.1, 5.0, u_v)
k_diff = st.sidebar.slider("Diffusione (K)", 0.1, 2.5, k_v)

# --- CREAZIONE MAPPA DINAMICA ---
N = 50
dx, dt = 1.0, 0.02
edifici = np.zeros((N, N))
orografia = np.zeros((N, N))

# Posizionamento Dinamico Palazzi
np.random.seed(42) # Per mantenere la stessa "casualità" se non cambi il numero
if num_palazzi > 0:
    # Il primo palazzo è sempre in traiettoria critica (X impostata dall'utente)
    edifici[dist_primo_palazzo : dist_primo_palazzo+4, 23:27] = 1
    # Gli altri palazzi vengono sparsi nel dominio
    for _ in range(num_palazzi - 1):
        px, py = np.random.randint(15, 45), np.random.randint(10, 40)
        edifici[px:px+3, py:py+3] = 1

# Posizionamento Dinamico Colline
if num_colline > 0:
    for c in range(num_colline):
        # Distribuzione delle colline
        cx = 10 if c == 0 else np.random.randint(20, 45) # La prima è vicina, le altre sparse
        cy = 15 if c == 0 else np.random.randint(10, 40)
        h = altezza_max_colline * (0.5 + np.random.rand() * 0.5)
        
        for i in range(N):
            for j in range(N):
                dist = np.sqrt((i-cx)**2 + (j-cy)**2)
                if dist < 12:
                    orografia[i,j] += h * np.exp(-0.07 * dist**2)

# --- MOTORE DI CALCOLO ---
if st.sidebar.button("AVVIA SIMULAZIONE MULTI-OSTACOLO"):
    C = np.zeros((N, N))
    mappa_box = st.empty()
    testo_box = st.empty()
    sx, sy = 5, 25 # Sorgente fissa

    for t in range(160):
        Cn = C.copy()
        Cn[sx, sy] += 155 * dt # Rilascio costante
        
        for i in range(1, N-1):
            for j in range(1, N-1):
                if edifici[i,j] == 1: continue
                
                # Formula ADR (Equazione di Trasporto)
                diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u_vento * dt * (C[i,j] - C[i-1,j])
                Cn[i,j] += diff + adv

        # Pulizia e aderenza alle pareti
        C = np.where(edifici == 1, 0, Cn)
        C = np.clip(C, 0, 100)
        
        if t % 15 == 0:
            picco = np.max(C) * 0.15
            fig = go.Figure(data=[
                go.Surface(
                    z=C + orografia, 
                    colorscale='Jet', 
                    cmin=0.01, cmax=12, 
                    name="Gas"
                ),
                go.Surface(z=edifici * 4.5, colorscale='Greys', opacity=0.9, showscale=False),
                go.Surface(z=orografia, colorscale='Greens', opacity=0.3, showscale=False)
            ])
            
            fig.update_layout(
                scene=dict(
                    zaxis=dict(range=[0, 15], title="Concentrazione"),
                    xaxis_title="X [m]", yaxis_title="Y [m]"
                ),
                margin=dict(l=0, r=0, b=0, t=0), height=750
            )
            mappa_box.plotly_chart(fig, use_container_width=True)
            
            if picco > 0.1: testo_box.error(f"⚠️ SOGLIA CRITICA: {picco:.4f} ppm")
            else: testo_box.success(f"✅ STATO SICURO: {picco:.4f} ppm")

    st.info("Simulazione completata. L'interazione tra i molteplici ostacoli crea zone di ombra e accumulo.")
