import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE AMBIENTE COMPUTAZIONALE ---
st.set_page_config(page_title="Simulatore Dispersione ADR", layout="wide")
st.title("Analisi Numerica della Dispersione di Inquinanti")
st.write("Studio dell'evoluzione del pennacchio inquinante in funzione di variabili meteorologiche e topografiche.")

# --- INPUT: CONDIZIONI METEOROLOGICHE (SIDEBAR) ---
st.sidebar.header("Parametri Atmosferici")
# La classe di stabilità definisce la capacità dispersiva dell'atmosfera
classe_stabilita = st.sidebar.selectbox("Classe di Stabilità", ["Instabile (Convezione)", "Neutra", "Stabile (Inversione)"])

if classe_stabilita == "Instabile (Convezione)":
    u_init, k_init = 1.0, 1.8 
elif classe_stabilita == "Neutra":
    u_init, k_init = 1.5, 1.0 
else:
    u_init, k_init = 0.5, 0.2 # Condizione critica per il ristagno al suolo

v_vento = st.sidebar.slider("Velocità del Vento (u) [m/s]", 0.1, 5.0, u_init)
coeff_K = st.sidebar.slider("Coefficiente di Diffusione (K)", 0.1, 2.5, k_init)

st.sidebar.header("Fenomeni di Washout (Pioggia)")
pioggia_intensita = st.sidebar.select_slider("Intensità Precipitazione", options=["Nulla", "Leggera", "Forte"])
solubilita_gas = st.sidebar.selectbox("Sostanza", ["Alta Solubilità", "Media Solubilità", "Bassa Solubilità"])

# Parametri chimico-fisici per la rimozione (Wet Deposition)
if solubilita_gas == "Alta Solubilità":
    limit_ppm, alpha = 0.05, 1.0
elif solubilita_gas == "Media Solubilità":
    limit_ppm, alpha = 0.1, 0.7
else:
    limit_ppm, alpha = 9.0, 0.3

# --- DISCRETIZZAZIONE E TOPOGRAFIA ---
N_griglia = 50
dx_spazio = 1.0
dt_tempo = 0.02
iter_tot = 160

# Calcolo del termine reattivo (sigma) per il lavaggio piovoso
sigma_base = {"Nulla": 0.0, "Leggera": 0.1, "Forte": 0.25}[pioggia_intensita]
sigma_effettivo = sigma_base * alpha

# Generazione ostacoli topografici (Morfologia urbana)
mappa_edifici = np.zeros((N_griglia, N_griglia))
np.random.seed(42)
for _ in range(10):
    gx, gy = np.random.randint(18, 43), np.random.randint(10, 38)
    mappa_edifici[gx:gx+3, gy:gy+3] = 1

# --- MOTORE DI CALCOLO ADR ---
if st.sidebar.button("CALCOLA DISPERSIONE"):
    Conc_mat = np.zeros((N_griglia, N_griglia))
    placeholder_map = st.empty()
    placeholder_text = st.empty()
    
    # Sorgente di rilascio
    src_x, src_y = 8, 25 

    for t in range(iter_tot):
        Cn_new = Conc_mat.copy()
        Cn_new[src_x, src_y] += 130 * dt_tempo # Termine sorgente costante
        
        for i in range(1, N_griglia-1):
            for j in range(1, N_griglia-1):
                if mappa_edifici[i,j] == 1:
                    continue # Condizione di impermeabilità degli edifici
                
                # Scomposizione dell'Equazione di Trasporto
                # Diffusione (Laplaciano)
                d_term = coeff_K * dt_tempo * (Conc_mat[i+1,j] + Conc_mat[i-1,j] + Conc_mat[i,j+1] + Conc_mat[i,j-1] - 4*Conc_mat[i,j])
                # Advezione (Trasporto Vento - Upwind)
                a_term = -v_vento * dt_tempo * (Conc_mat[i,j] - Conc_mat[i-1,j])
                # Reazione (Abbattimento Pioggia)
                r_term = -sigma_effettivo * dt_tempo * Conc_mat[i,j]
                
                Cn_new[i,j] += d_term + a_term + r_term

        # Integrazione topografica: il gas aderisce alle pareti (rimozione del vuoto)
        Conc_mat = np.where(mappa_edifici == 1, 0, Cn_new)
        Conc_mat = np.clip(Conc_mat, 0, 100)
        
        if t % 15 == 0:
            val_picco = np.max(Conc_mat[15:45, 10:40]) * 0.15
            
            # Utilizzo della scala colori 'Jet' (simile alla tesi originale)
            fig = go.Figure(data=[
                go.Surface(z=Conc_mat, colorscale='Jet', showscale=True),
                go.Surface(z=mappa_edifici * 2.8, colorscale='Greys', opacity=0.6, showscale=False)
            ])
            
            fig.update_layout(
                scene=dict(
                    zaxis=dict(range=[0, 15], title="C [ppm]"),
                    xaxis_title='X [m]', yaxis_title='Y [m]'
                ),
                margin=dict(l=0, r=0, b=0, t=0), height=700
            )
            placeholder_map.plotly_chart(fig, use_container_width=True)
            
            if val_picco > limit_ppm:
                placeholder_text.error(f"SOGLIA SUPERATA: {val_picco:.4f} ppm - Rischio per la salute")
            else:
                placeholder_text.success(f"SOGLIA RISPETTATA: {val_picco:.4f} ppm - Condizioni di sicurezza")

    st.info("Simulazione terminata. Il modello evidenzia come la pioggia (lavaggio) riduca la concentrazione al suolo, mentre la stabilità atmosferica ne condiziona il ristagno.")
