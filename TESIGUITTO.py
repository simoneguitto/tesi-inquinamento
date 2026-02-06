import streamlit as st
import numpy as np
import plotly.graph_objects as go

# Configurazione dell'applicazione
st.set_page_config(page_title="Simulatore Dispersione Atmosferica", layout="wide")
st.title("Simulatore Numerico di Dispersione Inquinanti")
st.write("Analisi dell'equazione di Advezione-Diffusione con termini di deposizione umida.")

# --- AREA INPUT: METEOROLOGIA E AMBIENTE ---
st.sidebar.header("Variabili Meteorologiche")

# Evoluzione rispetto al modello base: Integrazione dinamica della stabilita
condizione_atmosferica = st.sidebar.selectbox(
    "Stabilità Atmosferica", 
    ["Instabile (Forte Turbolenza)", "Neutra", "Stabile (Inversione Termica)"]
)

# Gestione Precipitazioni (Miglioramento tecnico rispetto ai modelli statici)
pioggia = st.sidebar.select_slider(
    "Intensità Pioggia (Wet Deposition)",
    options=["Nessuna", "Leggera", "Moderata", "Forte"]
)

# Assegnazione parametri fisici (u = vento, D = diffusione, k = decadimento)
if condizione_atmosferica == "Instabile (Forte Turbolenza)":
    D_val, u_val = 1.8, 0.8
elif condizione_atmosferica == "Neutra":
    D_val, u_val = 1.0, 1.5
else:
    D_val, u_val = 0.2, 0.4

# Effetto di lavaggio atmosferico (Scavenging) dovuto alla pioggia
scavenging_map = {"Nessuna": 0.01, "Leggera": 0.07, "Moderata": 0.15, "Forte": 0.30}
k_reac = scavenging_map[pioggia]

u = st.sidebar.slider("Velocità del Vento (u) [m/s]", 0.1, 5.0, u_val)
D = st.sidebar.slider("Coefficiente di Diffusione (K)", 0.1, 2.5, D_val)

# --- CONFIGURAZIONE SORGENTE E SOSTANZA ---
st.sidebar.header("Parametri Chimici")
tipo_gas = st.sidebar.selectbox("Inquinante Target", ["Gas Altamente Tossico", "Biossido di Azoto", "Monossido di Carbonio"])

# Soglie basate su letteratura scientifica (es. caso Bhopal citato in letteratura)
if tipo_gas == "Gas Altamente Tossico":
    soglia = 0.05
elif tipo_gas == "Biossido di Azoto":
    soglia = 0.1
else:
    soglia = 9.0

q_rate = st.sidebar.slider("Portata Emissione (Q)", 50, 250, 120)

# --- MOTORE DI CALCOLO NUMERICO ---
nx, ny = 50, 50
dx = 1.0

# Calcolo automatico del passo temporale per garantire la stabilita (CFL condition)
dt = 0.4 * (dx / (u + D + 0.1))
if dt > 0.05: dt = 0.05

# Generazione Griglia Ostacoli (Edifici)
obstacles = np.zeros((nx, ny))
np.random.seed(42)
for _ in range(12):
    ox, oy = np.random.randint(18, 45), np.random.randint(10, 40)
    obstacles[ox:ox+3, oy:oy+3] = 1

def avvia_simulazione():
    C = np.zeros((nx, ny))
    frame_grafico = st.empty()
    frame_testo = st.empty()
    
    # Punto di rilascio inquinante
    sx, sy = 10, 25

    for t in range(130):
        C_new = C.copy()
        C_new[sx, sy] += q_rate * dt
        
        # Risoluzione alle differenze finite dell'equazione ADR
        for i in range(1, nx-1):
            for j in range(1, ny-1):
                if obstacles[i,j] == 1:
                    C_new[i,j] = 0 # Gli edifici sono barriere impermeabili
                    continue
                
                # Termini della formula: Diffusione + Advezione + Reazione (Pioggia)
                diff = D * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u * dt * (C[i,j] - C[i-1,j]) # Schema Upwind
                reac = -k_reac * dt * C[i,j]
                
                C_new[i,j] += diff + adv + reac

        # Clamp per stabilita numerica
        C = np.clip(C_new, 0, 50)
        
        if t % 12 == 0:
            # Rilevamento concentrazione critica sugli edifici
            picco_urbano = np.max(C[obstacles == 1 + 1] if np.any(obstacles) else 0)
            picco_realistico = np.max(C[20:45, 10:40]) * 0.13
            
            # Rendering 3D
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='Reds', name="Nube Inquinante"),
                go.Surface(z=obstacles * 2.5, colorscale='Greys', opacity=0.5, showscale=False, name="Edifici")
            ])
            fig.update_layout(
                scene=dict(zaxis=dict(range=[0, 15])),
                margin=dict(l=0, r=0, b=0, t=0),
                height=600
            )
            frame_grafico.plotly_chart(fig, use_container_width=True)
            
            # Valutazione rischio
            if picco_realistico > soglia:
                frame_testo.error(f"STATO: ALLERTA CRITICA | Concentrazione rilevata: {picco_realistico:.3f} ppm | Soglia limite: {soglia}")
            else:
                frame_testo.success(f"STATO: LIVELLI NELLA NORMA | Concentrazione rilevata: {picco_realistico:.3f} ppm | Soglia limite: {soglia}")

if st.sidebar.button("Esegui Modello Numerico"):
    avvia_simulazione()
