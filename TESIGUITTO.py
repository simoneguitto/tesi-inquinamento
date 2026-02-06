import streamlit as st
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

# Configurazione dell'interfaccia
st.set_page_config(page_title="Analisi Dispersione Atmosferica", layout="wide")
st.title("Simulatore di Dispersione Inquinanti in Ambiente Urbano")
st.write("Modello numerico basato sulle equazioni di Advezione-Diffusione-Reazione (ADR).")

# --- BARRA LATERALE: INPUT TECNICI ---
st.sidebar.header("Parametri del Modello")
u_vento = st.sidebar.slider("Velocità del Vento (u) [m/s]", 0.1, 5.0, 1.5)
diff_K = st.sidebar.slider("Coefficiente di Diffusione (K) [m²/s]", 0.1, 2.0, 1.0)

st.sidebar.header("Variabili Ambientali")
tipo_gas = st.sidebar.selectbox("Sostanza Inquinante", ["Sostanza A (Tossica)", "Sostanza B (NO2)", "Sostanza C (CO)"])
piovosita = st.sidebar.select_slider("Livello di Pioggia", options=["Assente", "Moderato", "Intenso"])

# Definizione soglie e parametri chimico-fisici
if tipo_gas == "Sostanza A (Tossica)":
    limite, solubilita = 0.05, 1.0
elif tipo_gas == "Sostanza B (NO2)":
    limite, solubilita = 0.1, 0.7
else:
    limite, solubilita = 9.0, 0.35

# --- SETUP GRIGLIA NUMERICA ---
N = 50          # Dimensione matrice
dx = 1.0        # Risoluzione spaziale (metri)
dt = 0.02       # Passo temporale per stabilità (CFL)
iterazioni = 160 

# Coefficiente di abbattimento (Scavenging coefficient)
k_lavaggio = {"Assente": 0.0, "Moderato": 0.12, "Intenso": 0.3}[piovosita]

# Definizione della Topografia (Edifici)
mappa_ostacoli = np.zeros((N, N))
np.random.seed(42)
for _ in range(10):
    ix, iy = np.random.randint(18, 43), np.random.randint(10, 38)
    mappa_ostacoli[ix:ix+3, iy:iy+3] = 1

# --- ESECUZIONE SIMULAZIONE ---
if st.sidebar.button("ESEGUI ANALISI"):
    C = np.zeros((N, N))    # Concentrazione iniziale
    display_grafico = st.empty()
    display_info = st.empty()
    
    # Coordinate sorgente di emissione
    sx, sy = 8, 25 

    for t in range(iterazioni):
        Cn = C.copy()
        Cn[sx, sy] += 125 * dt # Rilascio costante
        
        # Risoluzione numerica ADR tramite differenze finite
        for i in range(1, N-1):
            for j in range(1, N-1):
                # Se la cella è un ostacolo, saltiamo il calcolo interno
                if mappa_ostacoli[i,j] == 1:
                    continue
                
                # Calcolo dei tre termini dell'equazione
                # 1. Diffusione spaziale
                termine_diff = diff_K * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j]) / (dx**2)
                # 2. Trasporto dovuto al vento (Advezione Upwind)
                termine_adv = -u_vento * dt * (C[i,j] - C[i-1,j]) / dx
                # 3. Rimozione chimico-fisica (Reazione)
                termine_reac = -(k_lavaggio * solubilita) * dt * C[i,j]
                
                Cn[i,j] += termine_diff + termine_adv + termine_reac

        # SOLUZIONE AL VUOTO: Mascheramento post-computazionale
        # Questa riga forza il gas a 'toccare' il bordo prima di essere azzerato nell'edificio
        C = np.where(mappa_ostacoli == 1, 0, Cn)
        C = np.clip(C, 0, 100)
        
        # Rendering grafico periodico
        if t % 15 == 0:
            picco_rilevato = np.max(C[18:45, 10:40]) * 0.15
            
            fig = go.Figure(data=[
                go.Surface(z=C, colorscale='Reds', showscale=True, name="Gas"),
                go.Surface(z=mappa_ostacoli * 2.5, colorscale='Greys', opacity=0.5, showscale=False, name="Topografia")
            ])
            
            fig.update_layout(
                scene=dict(
                    xaxis_title='X [m]', yaxis_title='Y [m]', zaxis_title='Conc. [ppm]',
                    zaxis=dict(range=[0, 15])
                ),
                margin=dict(l=0, r=0, b=0, t=0),
                height=600
            )
            display_grafico.plotly_chart(fig, use_container_width=True)
            
            if picco_rilevato > limite:
                display_info.error(f"ANALISI CRITICA: Picco {picco_rilevato:.4f} ppm | OLTRE SOGLIA")
            else:
                display_info.success(f"ANALISI STABILE: Picco {picco_rilevato:.4f} ppm | SOTTO SOGLIA")

    st.info("Simulazione completata. I dati mostrano l'interazione tra il pennacchio e la morfologia urbana.")
