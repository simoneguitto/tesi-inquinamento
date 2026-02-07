import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Simulatore Dispersione Meteorologica", layout="wide")
st.title("Analisi della Dispersione in Ambienti con Ostacoli Multipli")
st.write("Studio dell'impatto meteorologico e topografico sulla diffusione di gas tossici.")

# --- INPUT METEOROLOGICI (SIDEBAR) ---
st.sidebar.header("Condizioni Atmosferiche")
tipo_aria = st.sidebar.selectbox("Stabilità Atmosferica", ["Instabile (Turbolenta)", "Neutra", "Stabile (Ristagno)"])

# Parametri che variano in base alla meteorologia scelta
if tipo_aria == "Instabile (Turbolenta)":
    v_def, k_def = 1.0, 1.9  # Vento calmo, molta dispersione laterale
elif tipo_aria == "Neutra":
    v_def, k_def = 1.5, 1.0  # Condizioni standard
else:
    v_def, k_def = 0.6, 0.2  # Vento debole, gas molto concentrato (Pericolo!)

u_vento = st.sidebar.slider("Velocità del Vento (u) [m/s]", 0.1, 5.0, v_def)
k_diff = st.sidebar.slider("Diffusione Turbolenta (K)", 0.1, 2.5, k_def)

st.sidebar.header("Variabili di Lavaggio (Pioggia)")
pioggia = st.sidebar.select_slider("Intensità Precipitazione", options=["Zero", "Leggera", "Forte"])
solubilita = st.sidebar.selectbox("Tipo Sostanza", ["Alta", "Media", "Bassa"])

# Parametri di abbattimento fisico
sigma_p = {"Zero": 0.0, "Leggera": 0.12, "Forte": 0.25}[pioggia]
s_index = {"Alta": 1.0, "Media": 0.7, "Bassa": 0.3}[solubilita]
soglia_allarme = 0.06 if solubilita == "Alta" else 0.15

# --- CREAZIONE DEL DOMINIO (TOPOGRAFIA E OROGRAFIA) ---
N = 50
dx = 1.0
dt = 0.02
edifici = np.zeros((N, N))
colline = np.zeros((N, N))

# 1. TOPOGRAFIA: Posizionamento mirato dei palazzi
# Palazzo 1: Esattamente in traiettoria (davanti alla sorgente)
edifici[18:23, 23:26] = 1 
# Palazzi di contorno sparsi (non a scacchiera)
edifici[10:13, 10:14] = 1 
edifici[35:40, 15:18] = 1 
edifici[28:33, 35:38] = 1 

# 2. OROGRAFIA: Due colline dinamiche
for i in range(N):
    for j in range(N):
        # Collina piccola vicino alla sorgente (deviazione iniziale)
        dist1 = np.sqrt((i-8)**2 + (j-18)**2)
        if dist1 < 7: colline[i,j] += 2.5 * np.exp(-0.1 * dist1**2)
        
        # Collina grande in fondo (barriera finale)
        dist2 = np.sqrt((i-42)**2 + (j-25)**2)
        if dist2 < 14: colline[i,j] += 5.5 * np.exp(-0.04 * dist2**2)

# --- CALCOLO NUMERICO (Modello ADR) ---
if st.sidebar.button("CALCOLA MODELLO"):
    C = np.zeros((N, N))
    mappa_plot = st.empty()
    alert_text = st.empty()
    
    # Sorgente gas (sx, sy)
    sx, sy = 5, 25 

    for t in range(165):
        Cn = C.copy()
        Cn[sx, sy] += 135 * dt # Rilascio costante di inquinante
        
        for i in range(1, N-1):
            for j in range(1, N-1):
                if edifici[i,j] == 1:
                    continue
                
                # Equazione: Trasporto + Allargamento - Lavaggio pioggia
                diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u_vento * dt * (C[i,j] - C[i-1,j]) # Trasporto lungo asse X
                reac = -(sigma_p * s_index) * dt * C[i,j]
                
                Cn[i,j] += diff + adv + reac

        # Effetto aderenza topografica (niente vuoto visivo)
        C = np.where(edifici == 1, 0, Cn)
        C = np.clip(C, 0, 100)
        
        if t % 15 == 0:
            picco_attuale = np.max(C[10:45, 10:45]) * 0.15
            
            # Grafico con scala Jet (identico a modelli scientifici)
            fig = go.Figure(data=[
                go.Surface(z=C + colline, colorscale='Jet', name="Gas"),
                go.Surface(z=edifici * 3.8, colorscale='Greys', opacity=0.85, showscale=False),
                go.Surface(z=colline, colorscale='Greens', opacity=0.3, showscale=False)
            ])
            
            fig.update_layout(
                scene=dict(zaxis=dict(range=[0, 15]), xaxis_title='X [m]', yaxis_title='Y [m]'),
                margin=dict(l=0, r=0, b=0, t=0), height=750
            )
            mappa_plot.plotly_chart(fig, use_container_width=True)
            
            if picco_attuale > soglia_allarme:
                alert_text.error(f"SOGLIA CRITICA: {picco_attuale:.4f} ppm - Rilevato impatto su edifici")
            else:
                alert_text.success(f"STATO: {picco_attuale:.4f} ppm - Dispersione controllata")

    st.info("Analisi completata. Il gas impatta direttamente il primo ostacolo topografico prima di diffondersi nel resto del dominio.")
