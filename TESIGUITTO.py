import streamlit as st
import numpy as np
import plotly.graph_objects as go

# Configurazione dell'interfaccia
st.set_page_config(page_title="Simulatore Dispersione Atmosferica", layout="wide")
st.title("Simulatore di Dispersione Inquinanti in Ambiente Urbano")
st.write("Modellazione numerica basata sull'equazione di Advezione-Diffusione-Reazione (ADR).")

# --- SIDEBAR: CONFIGURAZIONE METEO ---
st.sidebar.header("Variabili Meteorologiche")

meteo = st.sidebar.selectbox(
    "Stabilità Atmosferica", 
    ["Instabile (Forte Rimescolamento)", "Neutra", "Stabile (Inversione Termica)"]
)

pioggia = st.sidebar.select_slider(
    "Intensità Precipitazioni",
    options=["Nessuna", "Leggera", "Moderata", "Forte"]
)

# Parametri fisici di base (D=Diffusione, u=Vento)
if meteo == "Instabile (Forte Rimescolamento)":
    D_val, u_val = 1.8, 0.6
elif meteo == "Neutra":
    D_val, u_val = 1.0, 1.5
else:
    D_val, u_val = 0.2, 0.3

# Mappa dello scavenging (lavaggio atmosferico)
scavenging_map = {"Nessuna": 0.0, "Leggera": 0.05, "Moderata": 0.12, "Forte": 0.25}
k_pioggia = scavenging_map[pioggia]

u = st.sidebar.slider("Velocità del Vento (u) [m/s]", 0.1, 5.0, u_val)
D = st.sidebar.slider("Coefficiente di Diffusione (K)", 0.1, 2.5, D_val)

# --- SIDEBAR: PARAMETRI CHIMICI ---
st.sidebar.header("Sostanza Rilasciata")
sostanza = st.sidebar.selectbox("Inquinante", ["Gas Tossico Industriale", "Biossido di Azoto (NO2)", "Monossido di Carbonio (CO)"])

# Impostazione soglie e solubilità (Il CO è meno influenzato dalla pioggia)
if sostanza == "Gas Tossico Industriale":
    soglia = 0.05
    solubilita = 1.0
elif sostanza == "Biossido di Azoto (NO2)":
    soglia = 0.1
    solubilita = 0.8
else: # Monossido di Carbonio
    soglia = 9.0
    solubilita = 0.4 # Il CO oppone più resistenza al lavaggio della pioggia

q_rate = st.sidebar.slider("Portata Sorgente (Q)", 50, 250, 120)

# --- MOTORE DI CALCOLO NUMERICO ---
nx, ny = 50, 50
dx = 1.0

# Calcolo automatico del passo temporale (CFL condition) per evitare crash
dt = 0.4 * (dx / (u + D + 0.1))
if dt > 0.05: dt = 0.05

# Generazione Edifici (Orografia urbana)
obstacles = np.zeros((nx, ny))
np.random.seed(42)
for _ in range(12):
    ox, oy = np.random.randint(18, 45), np.random.randint(10, 40)
    obstacles[ox:ox+3, oy:oy+3] = 1

def avvia_calcolo():
    C = np.zeros((nx, ny))
    plot_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # Punto di emissione (Sorgente interna)
    sx, sy = 10, 25

    for t in range(150):
        C_new = C.copy()
        C_new[sx, sy] += q_rate * dt
        
        # Risoluzione ADR
        for i in range(1, nx-1):
            for j in range(1, ny-1):
                if obstacles[i,j] == 1:
                    C_new[i,j] = 0
                    continue
                
                # Formula discretizzata
                diff = D * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u * dt * (C[i,j] - C[i-1,j])
                # Effetto pioggia corretto per solubilità del gas
                reac = -(k_pioggia * solubilita) * dt * C[i,j]
                
                C_new[i,j] += diff + adv + reac

        # Clamp dei valori (Protezione numerica)
        C = np.clip(C_new, 0, 100)
        
        if t % 15 == 0:
            # Calcolo impatto realistico sulle zone edificate
            impatto = np.max(C[20:45, 10:40]) * 0.12
            
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='YlOrRd', showscale=True),
                go.Surface(z=obstacles * 2.5, colorscale='Greys', opacity=0.5, showscale=False)
            ])
            fig.update_layout(
                scene=dict(zaxis=dict(range=[0, 15])),
                margin=dict(l=0, r=0, b=0, t=0),
                height=600
            )
            plot_placeholder.plotly_chart(fig, use_container_width=True)
            
            # Semaforo di sicurezza
            if impatto > soglia:
                status_placeholder.error(f"STATO: ALLERTA | Picco Rilevato: {impatto:.3f} ppm | Soglia: {soglia}")
            else:
                status_placeholder.success(f"STATO: SICURO | Picco Rilevato: {impatto:.3f} ppm | Soglia: {soglia}")

if st.sidebar.button("Avvia Simulazione"):
    avvia_calcolo()
