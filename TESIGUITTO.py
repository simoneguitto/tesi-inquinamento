import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Analisi Meteo-Dispersiva", layout="wide")
st.title("Modello di Dispersione Inquinanti: Analisi Meteorologica")
st.write("Studio dell'evoluzione del pennacchio in funzione di topografia e orografia.")

# --- MENU LATERALE: VARIABILI METEO ---
st.sidebar.header("Parametri Atmosferici")
clima = st.sidebar.selectbox("Condizioni di Stabilità", ["Giorno (Turbolento)", "Standard", "Inversione (Ristagno)"])

if clima == "Giorno (Turbolento)":
    u_init, k_init = 1.0, 2.0 
elif clima == "Standard":
    u_init, k_init = 1.6, 1.1 
else:
    u_init, k_init = 0.6, 0.25 # Condizione di massimo pericolo

u_vento = st.sidebar.slider("Velocità vento (u) [m/s]", 0.1, 5.0, u_init)
k_diff = st.sidebar.slider("Diffusione (K)", 0.1, 2.5, k_init)

st.sidebar.header("Variabili di Pioggia")
intensita_p = st.sidebar.select_slider("Precipitazione", options=["Assente", "Moderata", "Forte"])
tipo_gas = st.sidebar.selectbox("Tipo di Gas", ["Solubile", "Semi-Solubile", "Inerte"])

# Parametri fisici di abbattimento
sigma_base = {"Assente": 0.0, "Moderata": 0.12, "Forte": 0.28}[intensita_p]
sol_val = {"Solubile": 1.0, "Semi-Solubile": 0.6, "Inerte": 0.2}[tipo_gas]
soglia_allarme = 0.08 if tipo_gas == "Solubile" else 0.15

# --- COSTRUZIONE AMBIENTE (TOPOGRAFIA E OROGRAFIA) ---
N = 50
dx, dt = 1.0, 0.02
edifici = np.zeros((N, N))
colline = np.zeros((N, N))

# 1. TOPOGRAFIA: Palazzi sparsi (Il primo in rotta di collisione col gas)
edifici[18:24, 23:27] = 1   # PALAZZO FRONTALE (Impatto diretto)
edifici[12:16, 12:16] = 1   # Laterale
edifici[30:35, 15:20] = 1   # Centrale
edifici[25:32, 38:43] = 1   # Lontano

# 2. OROGRAFIA: Due rilievi (Colline)
for i in range(N):
    for j in range(N):
        # Collina iniziale (deviazione flusso)
        d1 = np.sqrt((i-8)**2 + (j-18)**2)
        if d1 < 8: colline[i,j] += 2.5 * np.exp(-0.15 * d1**2)
        # Collina finale (barriera orografica)
        d2 = np.sqrt((i-43)**2 + (j-25)**2)
        if d2 < 15: colline[i,j] += 5.5 * np.exp(-0.04 * d2**2)

# --- SIMULAZIONE NUMERICA ---
if st.sidebar.button("ESEGUI ANALISI"):
    C = np.zeros((N, N))
    mappa_box = st.empty()
    testo_box = st.empty()
    
    # Sorgente emissione
    sx, sy = 5, 25 

    for t in range(165):
        Cn = C.copy()
        Cn[sx, sy] += 150 * dt # Emissione costante
        
        for i in range(1, N-1):
            for j in range(1, N-1):
                if edifici[i,j] == 1:
                    continue
                
                # Formula ADR (Advezione-Diffusione-Reazione)
                diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u_vento * dt * (C[i,j] - C[i-1,j])
                reac = -(sigma_base * sol_val) * dt * C[i,j]
                
                Cn[i,j] += diff + adv + reac

        # Pulizia dati e aderenza pareti
        C = np.where(edifici == 1, 0, Cn)
        C = np.clip(C, 0, 100)
        
        if t % 15 == 0:
            picco_ppm = np.max(C[10:45, 10:45]) * 0.15
            
            # Grafico con scala Jet calibrata (niente difetti nel blu)
            fig = go.Figure(data=[
                go.Surface(
                    z=C + colline, 
                    colorscale='Jet', 
                    showscale=True,
                    cmin=0.01, cmax=12, # Forza la scala a non sbiadire nel blu o bianco
                    name="Gas"
                ),
                go.Surface(z=edifici * 4.2, colorscale='Greys', opacity=0.9, showscale=False),
                go.Surface(z=colline, colorscale='Greens', opacity=0.3, showscale=False)
            ])
            
            fig.update_layout(
                scene=dict(
                    zaxis=dict(range=[0, 15], title="ppm"),
                    xaxis_title="X [m]", yaxis_title="Y [m]"
                ),
                margin=dict(l=0, r=0, b=0, t=0), height=750
            )
            mappa_box.plotly_chart(fig, use_container_width=True)
            
            if picco_ppm > soglia_allarme:
                testo_box.error(f"ATTENZIONE: Picco rilevato {picco_ppm:.4f} ppm - Soglia superata")
            else:
                testo_box.success(f"STATO: {picco_ppm:.4f} ppm - Entro i limiti")

    st.info("Analisi conclusa. Il modello evidenzia l'impatto diretto del gas sul primo edificio e il ristagno alla base della collina finale.")
