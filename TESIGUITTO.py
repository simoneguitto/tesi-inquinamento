import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import time

# --- SETUP DELLA PAGINA ---
st.set_page_config(page_title="Simulatore Tesi Guitto", layout="wide")

st.title("Simulatore Diffusione Inquinanti - Analisi Orografica")
st.write("Modello ADR (Advezione-Diffusione-Reazione) sviluppato per lo studio del ristagno urbano.")

# --- BARRA LATERALE PARAMETRI ---
st.sidebar.header("Parametri Simulazione")

# Scelta dell'inquinante per definire la soglia di rischio
st.sidebar.subheader("🧪 Agente Chimico")
tipo_gas = st.sidebar.selectbox(
    "Sostanza analizzata",
    ["Biossido di Azoto (NO2)", "Monossido di Carbonio (CO)", "Gas Industriale (Tossico)", "Custom"]
)

# Soglie realistiche per la tesi (in ppm)
if tipo_gas == "Biossido di Azoto (NO2)":
    soglia = 0.1  # Limite per salute pubblica
    nota = "Inquinante urbano (scarichi auto)."
elif tipo_gas == "Monossido di Carbonio (CO)":
    soglia = 9.0  # Limite orario standard
    nota = "Gas da combustione riscaldamento."
elif tipo_gas == "Gas Industriale (Tossico)":
    soglia = 0.05 # Molto sensibile (tipo Bhopal)
    nota = "Sostanza ad alta tossicità acuta."
else:
    soglia = st.sidebar.slider("Soglia manuale", 0.01, 10.0, 1.0)
    nota = "Valore inserito manualmente."

st.sidebar.info(f"Soglia allerta: {soglia} ppm. {nota}")

# Parametri fisici classici
u = st.sidebar.slider("Velocità del vento (u)", 0.0, 5.0, 1.5)
D = st.sidebar.slider("Coefficiente Diffusione (K)", 0.1, 2.0, 0.5)
k_reac = st.sidebar.slider("Decadimento chimico", 0.0, 0.1, 0.01)


# Dimensioni griglia (nx, ny sono i nodi di calcolo)
L, W = 50, 50
nx, ny = 50, 50
dx, dy = L/nx, W/ny

# Variabili fisiche
u = st.sidebar.slider("Velocità del vento (u)", 0.0, 5.0, 1.5)
D = st.sidebar.slider("Coefficiente Diffusione (K)", 0.1, 2.0, 0.5)
k_reac = st.sidebar.slider("Reazione/Decadimento", 0.0, 0.1, 0.01)

# Punto di rilascio gas
st.sidebar.subheader("Sorgente")
src_x = st.sidebar.slider("Posiz. X", 0, nx-1, 5)
src_y = st.sidebar.slider("Posiz. Y", 0, ny-1, 25)
q_rate = st.sidebar.number_input("Portata emissione (Q)", 1.0, 100.0, 10.0)

# Settaggio palazzi
st.sidebar.subheader("Edifici")
n_obst = st.sidebar.slider("Numero edifici", 0, 15, 5)
seed = st.sidebar.number_input("Seme mappa (random)", 0, 100, 42)

# --- INIZIALIZZAZIONE MATRICI ---
C = np.zeros((nx, ny))
obstacles = np.zeros((nx, ny))

# Genero ostacoli casuali sulla griglia
np.random.seed(seed)
for _ in range(n_obst):
    ox, oy = np.random.randint(15, nx-5), np.random.randint(5, ny-5)
    obstacles[ox:ox+4, oy:oy+4] = 1 # Dimensioni blocco 4x4

dt = 0.05 # Passo temporale scelto per stabilità numerica

# --- CORE DEL CALCOLO ---
def avvia_calcolo():
    global C
    C = np.zeros((nx, ny))
    
    # Placeholder per aggiornare l'interfaccia senza ricaricare la pagina
    area_grafico = st.empty()
    area_testo = st.empty()
    
    for t in range(100):
        C_new = C.copy()
        
        # Emissione continua alla sorgente
        C_new[src_x, src_y] += q_rate * dt
        
        # Algoritmo alle differenze finite (loop spaziale)
        for i in range(1, nx-1):
            for j in range(1, ny-1):
                # Se c'è un palazzo, la concentrazione è zero (boundary condition interna)
                if obstacles[i, j] == 1:
                    C_new[i, j] = 0
                    continue
                
                # Calcolo Laplaciano per la diffusione
                diff = D * dt * (
                    (C[i+1, j] - 2*C[i, j] + C[i-1, j])/dx**2 + 
                    (C[i, j+1] - 2*C[i, j] + C[i, j-1])/dy**2
                )
                
                # Trasporto dovuto al vento (Advezione upwind)
                adv = -u * dt * (C[i, j] - C[i-1, j])/dx
                
                # Perdita chimica
                reac = -k_reac * dt * C[i, j]
                
                C_new[i, j] += diff + adv + reac
        
        C = np.maximum(0, C_new) # Evito concentrazioni negative
        
        # Monitoraggio picchi sugli edifici
        if n_obst > 0 and np.any(obstacles == 1):
            c_max_p = np.max(C[obstacles == 1])
            c_med_p = np.mean(C[obstacles == 1])
        else:
            c_max_p, c_med_p = 0, 0
            
        soglia = 1.0 # Limite critico per allerta
        
        # Visualizzazione ogni 5 frame per non rallentare troppo
        if t % 5 == 0:
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='Inferno', name='Inquinante'),
                go.Surface(z=obstacles * (np.max(C)*0.7), colorscale='Greys', opacity=0.4, showscale=False)
            ])
            fig.update_layout(scene=dict(zaxis=dict(range=[0, np.max(C)+0.5 if np.max(C)>0 else 5])))
            area_grafico.plotly_chart(fig, use_container_width=True)
            
            # Box dei risultati
            stato = "🔴 ALLERTA: RISTAGNO CRITICO" if c_max_p > soglia else "🟢 CONDIZIONI SICURE"
            area_testo.info(f"Step: {t} | Picco Aria: {np.max(C):.2f} | Picco Palazzi: {c_max_p:.2f} | STATO: {stato}")
            
    return C

# --- BOTTONE START ---
if st.button("Lancia Simulazione"):
    risultato = avvia_calcolo()
    st.success("Analisi completata.")
    
    # Export dati per tabelle tesi
    csv = pd.DataFrame(risultato).to_csv(index=False).encode('utf-8')
    st.download_button("Scarica Dati (CSV)", csv, "dati_simulazione_guitto.csv")
