import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Simulatore Dispersione", layout="wide")
st.title("Simulatore di Dispersione Inquinanti - Modello Stabile")

# --- PARAMETRI DI INPUT ---
st.sidebar.header("Parametri Meteo e Sorgente")

u = st.sidebar.slider("Velocita del vento (u) [m/s]", 0.1, 5.0, 1.0)
D = st.sidebar.slider("Coefficiente di Diffusione (K)", 0.1, 2.0, 1.0)

sostanza = st.sidebar.selectbox("Inquinante", ["Gas Tossico", "NO2", "CO"])
soglia = 0.05 if sostanza == "Gas Tossico" else 0.1 if sostanza == "NO2" else 9.0

q_rate = st.sidebar.slider("Intensita Sorgente (Q)", 10, 200, 100)

# --- CONFIGURAZIONE GRIGLIA E STABILITÀ ---
nx, ny = 50, 50
dx = 1.0

# PROTEZIONE NUMERICA: Calcolo automatico del dt (Condizione CFL)
# Più il vento è forte, più il tempo deve essere piccolo per non far esplodere i calcoli.
dt = 0.5 * (dx / (u + D + 0.1)) # Fattore di sicurezza 0.5
if dt > 0.1: dt = 0.1 # Cap massimo per fluidità

# Generazione ostacoli
obstacles = np.zeros((nx, ny))
np.random.seed(42)
for _ in range(12):
    ox, oy = np.random.randint(20, 45), np.random.randint(10, 40)
    obstacles[ox:ox+3, oy:oy+3] = 1

def esegui_simulazione():
    C = np.zeros((nx, ny))
    grafico = st.empty()
    testo = st.empty()
    
    # Sorgente fissa
    sx, sy = 10, 25

    for t in range(100):
        C_new = C.copy()
        
        # Emissione
        C_new[sx, sy] += q_rate * dt
        
        # Calcolo ADR con protezione
        for i in range(1, nx-1):
            for j in range(1, ny-1):
                if obstacles[i,j] == 1:
                    C_new[i,j] = 0
                    continue
                
                # Formule discretizzate
                diff = D * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j]) / (dx**2)
                adv = -u * dt * (C[i,j] - C[i-1,j]) / dx
                
                C_new[i,j] += diff + adv
        
        # FILTRO DI REALTÀ: Impedisce valori negativi o infiniti
        C = np.clip(C_new, 0, 100) 
        
        if t % 10 == 0:
            # Valutazione rischio (Normalizzata per evitare picchi assurdi)
            impatto = np.max(C[20:45, 10:40]) * 0.1
            
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='YlOrRd', showscale=False),
                go.Surface(z=obstacles * 2, colorscale='Greys', opacity=0.5, showscale=False)
            ])
            fig.update_layout(scene=dict(zaxis=dict(range=[0, 10])), margin=dict(l=0, r=0, b=0, t=0))
            grafico.plotly_chart(fig, use_container_width=True)
            
            stato = "ALLERTA" if impatto > soglia else "SICURO"
            testo.write(f"Stato: {stato} | Concentrazione rilevata: {impatto:.3f} ppm | Soglia: {soglia}")

if st.sidebar.button("Avvia Analisi"):
    esegui_simulazione()
