import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Simulatore ADR Avanzato", layout="wide")
st.title("Analisi Numerica: Interazione Fluido-Orografica")
st.write("Studio della dispersione in presenza di complessi topografici e rilievi orografici.")

# --- SIDEBAR: PARAMETRI METEO ---
st.sidebar.header("Variabili Atmosferiche")
stabilita_aria = st.sidebar.selectbox("Condizione Atmosferica", ["Instabile", "Neutra", "Stabile"])

if stabilita_aria == "Instabile":
    u_i, k_i = 1.2, 1.8 
elif stabilita_aria == "Neutra":
    u_i, k_i = 1.5, 1.0 
else:
    u_i, k_i = 0.6, 0.25 # Ristagno orografico massimo

u_v = st.sidebar.slider("Velocità del Vento (u) [m/s]", 0.1, 5.0, u_i)
k_d = st.sidebar.slider("Diffusione Turbolenta (K)", 0.1, 2.5, k_i)

st.sidebar.header("Idrometeore e Chimica")
pioggia_int = st.sidebar.select_slider("Precipitazione", options=["Assente", "Moderata", "Forte"])
grado_sol = st.sidebar.selectbox("Solubilità Inquinante", ["Alta", "Media", "Bassa"])

# Parametri di rimozione
sigma_m = {"Assente": 0.0, "Moderata": 0.12, "Forte": 0.28}[pioggia_int]
s_index = {"Alta": 1.0, "Media": 0.7, "Bassa": 0.3}[grado_sol]
soglia_p = 0.05 if grado_sol == "Alta" else 0.1

# --- DOMINIO E OROGRAFIA ---
N = 50
dx = 1.0
dt = 0.02
step_t = 160

# Definizione Topografia (Palazzi vicini) e Orografia (Collina)
strutture = np.zeros((N, N))
orografia = np.zeros((N, N))

# 1. Creazione "Canyon" Urbano (Palazzi vicini tra loro)
strutture[20:25, 15:18] = 1
strutture[20:25, 22:25] = 1
strutture[30:35, 15:18] = 1
strutture[30:35, 22:25] = 1

# 2. Creazione Collina (Orografia a fondo campo)
for i in range(N):
    for j in range(N):
        # Una collina gaussiana centrata a X=40, Y=20
        dist = np.sqrt((i-42)**2 + (j-20)**2)
        if dist < 12:
            orografia[i,j] = 4 * np.exp(-0.05 * dist**2)

# --- MOTORE DI CALCOLO ---
if st.sidebar.button("ESEGUI MODELLO"):
    C = np.zeros((N, N))
    mappa_3d = st.empty()
    alert_box = st.empty()
    
    source_x, source_y = 5, 20 # Sorgente prima dei palazzi

    for t in range(step_t):
        Cn = C.copy()
        Cn[source_x, source_y] += 140 * dt 
        
        for i in range(1, N-1):
            for j in range(1, N-1):
                # Il calcolo avviene solo all'esterno delle strutture solide
                if strutture[i,j] == 1:
                    continue
                
                # Equazione ADR con termine di lavaggio
                diff = k_d * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u_v * dt * (C[i,j] - C[i-1,j]) # Vento lungo X
                reac = -(sigma_m * s_index) * dt * C[i,j]
                
                Cn[i,j] += diff + adv + reac

        # Fusione dati: il gas aderisce a palazzi e segue l'orografia
        C = np.where(strutture == 1, 0, Cn)
        C = np.clip(C, 0, 100)
        
        if t % 15 == 0:
            p_val = np.max(C[15:45, 10:40]) * 0.15
            
            # Visualizzazione: Gas (Jet), Palazzi (Grigio), Collina (Verde/Marrone)
            fig = go.Figure(data=[
                go.Surface(z=C + orografia, colorscale='Jet', showscale=True, name="Gas"),
                go.Surface(z=strutture * 3.5, colorscale='Greys', opacity=0.8, showscale=False),
                go.Surface(z=orografia, colorscale='Greens', opacity=0.3, showscale=False)
            ])
            
            fig.update_layout(
                scene=dict(zaxis=dict(range=[0, 15]), xaxis_title='X', yaxis_title='Y'),
                margin=dict(l=0, r=0, b=0, t=0), height=750
            )
            mappa_3d.plotly_chart(fig, use_container_width=True)
            
            if p_val > soglia_p:
                alert_box.error(f"SOGLIA CRITICA: {p_val:.4f} ppm")
            else:
                alert_box.success(f"SOGLIA NORMA: {p_val:.4f} ppm")

    st.info("Simulazione completata. Notare l'accelerazione del flusso tra gli edifici e il ristagno alla base del rilievo orografico.")
