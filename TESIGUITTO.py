import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import time

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Simulatore ADR - Tesi", layout="wide")

st.markdown("""
# Simulatore di Equazioni alle Derivate Parziali (Paraboliche)
## Modello di Advezione-Diffusione-Reazione in Ambienti Urbani
Questo strumento risolve numericamente l'equazione del trasporto di inquinanti considerando orografia, 
topografia urbana e reazioni chimiche (es. idrolisi con umidità).
""")

# --- TEORIA MATEMATICA (PER LA TESI) ---
with st.expander("📘 Riferimenti Matematici e Modello Discretizzato"):
    st.latex(r'''
    \frac{\partial C}{\partial t} + \mathbf{u} \cdot \nabla C = \nabla \cdot (\mathbf{K} \nabla C) - R(C) + S
    ''')
    st.markdown("""
    Dove:
    * $\partial C / \partial t$: Variazione temporale della concentrazione.
    * $\mathbf{u} \cdot \nabla C$: **Termine di Advezione** (Trasporto del vento). Risolto con schema *Upwind*.
    * $\nabla \cdot (\mathbf{K} \nabla C)$: **Termine di Diffusione** (Dispersione turbolenta). Risolto con differenze centrali.
    * $R(C) = (k_{reac} + k_{dep})C$: **Termine di Reazione/Rimozione** (Decadimento chimico e deposizione secca).
    * $S$: Termine sorgente (Fuga di gas).
    """)

# --- SIDEBAR: PARAMETRI FISICI ---
st.sidebar.header("1. Parametri Ambientali")
u_base = st.sidebar.slider("Velocità Vento (u) [m/s]", 0.5, 15.0, 5.0)
dir_vento = st.sidebar.slider("Direzione Vento (gradi)", -45, 45, 0)
diffusivita = st.sidebar.select_slider("Diffusività Turbolenta (K)", 
                                       options=[0.1, 0.5, 2.0, 5.0], 
                                       value=0.5,
                                       help="Classe di stabilità di Pasquill: Bassa=Notte/Stabile, Alta=Giorno/Instabile")

st.sidebar.header("2. Termini di Reazione")
umidita = st.sidebar.radio("Condizioni Meteo", ["Secco", "Umido", "Pioggia"], index=0)
k_map = {"Secco": 0.0, "Umido": 0.05, "Pioggia": 0.2}
k_reac = k_map[umidita]
k_dep = st.sidebar.slider("Coeff. Deposizione al suolo", 0.0, 0.1, 0.01)

st.sidebar.header("3. Geometria Dominio")
n_obst = st.sidebar.slider("Numero Blocchi Urbani", 0, 5, 2)
h_hill = st.sidebar.slider("Altezza Collina (Orografia)", 0, 20, 10)

# --- INIZIALIZZAZIONE GRIGLIA E DOMINIO ---
nx, ny = 100, 60
dx = dy = 2.0  # metri per cella
X, Y = np.meshgrid(np.arange(nx)*dx, np.arange(ny)*dy)

# 1. Creazione Orografia (Collina Gaussiana)
Z_oro = h_hill * np.exp(-((X - 120)**2 + (Y - 60)**2) / 1000)

# 2. Creazione Ostacoli Urbani (Matrice Maschera)
# 0 = aria libera, 1 = edificio
obstacles = np.zeros((ny, nx))
if n_obst > 0:
    for i in range(n_obst):
        x_start = 40 + i * 15
        obstacles[25:35, x_start:x_start+5] = 1 # Edifici rettangolari

# 3. Calcolo Passo Temporale (CFL Stability Condition)
# Per la stabilità, dt deve soddisfare la condizione CFL:
# dt <= dx^2 / (4*K)  (Diffusione)
# dt <= dx / u        (Advezione)
dt_diff = (dx**2) / (4 * diffusivita)
dt_adv = dx / (u_base + 0.1) # +0.1 per evitare div by zero
dt = min(dt_diff, dt_adv) * 0.8 # Fattore di sicurezza 0.8
st.sidebar.markdown(f"**$\Delta t$ calcolato:** {dt:.4f} s (Stabilità CFL garantita)")

# --- LOGICA DI RISOLUZIONE (SOLVER) ---
def run_simulation():
    # Inizializzazione Concentrazione
    C = np.zeros((ny, nx))
    
    # Pre-calcolo velocità vento (Semplificato: deviazione leggera dovuta alla collina)
    # Vento prevalentemente lungo X
    U = np.ones((ny, nx)) * u_base * np.cos(np.radians(dir_vento))
    V = np.ones((ny, nx)) * u_base * np.sin(np.radians(dir_vento))
    
    # Il vento rallenta "dietro" la collina (effetto scia semplice) e sugli edifici
    U = U * (1 - 0.02 * Z_oro) 
    U[obstacles == 1] = 0
    V[obstacles == 1] = 0

    # Loop Temporale
    simulation_steps = 150
    placeholder = st.empty()
    stats_placeholder = st.empty()
    
    start_time = time.time()
    
    for t in range(simulation_steps):
        Cn = C.copy()
        
        # --- DISCRETIZZAZIONE FINITE DIFFERENCE ---
        
        # 1. Diffusione (Schema Centrato a 5 punti)
        # d^2C/dx^2 approx (C[i+1] - 2C[i] + C[i-1]) / dx^2
        laplacian = (
            (np.roll(Cn, -1, axis=1) - 2*Cn + np.roll(Cn, 1, axis=1)) / dx**2 +
            (np.roll(Cn, -1, axis=0) - 2*Cn + np.roll(Cn, 1, axis=0)) / dy**2
        )
        
        # 2. Advezione (Schema Upwind - Primo Ordine)
        # Se u > 0: (C[i] - C[i-1]) / dx
        adv_x = np.zeros_like(Cn)
        adv_y = np.zeros_like(Cn)
        
        # Gestione semplificata Upwind per vento positivo lungo X
        adv_x = U * (Cn - np.roll(Cn, 1, axis=1)) / dx
        # Gestione semplificata Upwind per vento lungo Y (segno dipende da dir_vento)
        if dir_vento >= 0:
            adv_y = V * (Cn - np.roll(Cn, 1, axis=0)) / dy
        else:
            adv_y = V * (np.roll(Cn, -1, axis=0) - Cn) / dy

        # 3. Reazione e Deposizione
        reaction = (k_reac + k_dep) * Cn

        # 4. Aggiornamento Temporale (Eulero Esplicito)
        C = Cn + dt * (diffusivita * laplacian - (adv_x + adv_y) - reaction)
        
        # 5. Condizioni al Contorno e Sorgente
        # Sorgente continua (es. camino industriale o perdita)
        if t < 100: # La perdita dura solo per un certo tempo
            C[ny//2, 10] = 100.0 
        
        # Condizioni Dirichlet ai bordi (0 concentrazione all'infinito)
        C[:, 0] = 0; C[:, -1] = 0; C[0, :] = 0; C[-1, :] = 0
        
        # Condizioni sugli ostacoli (Muri impermeabili o assorbenti)
        C[obstacles == 1] = 0 

        # --- VISUALIZZAZIONE OGNI 10 STEP ---
        if t % 5 == 0:
            # Creiamo un plot 3D combinato: Superficie Orografica + Heatmap Inquinante
            fig = go.Figure()

            # Orografia (Wireframe o Surface grigia)
            fig.add_trace(go.Surface(
                z=Z_oro, 
                x=X, y=Y, 
                colorscale='Gray', 
                opacity=0.3, 
                showscale=False,
                name="Orografia"
            ))

            # Inquinante (Heatmap proiettata o Surface colorata sopra l'orografia)
            # Aggiungiamo un piccolo offset z per vederla sopra il terreno
            fig.add_trace(go.Surface(
                z=Z_oro + 0.5 + (C/np.max(C)*10 if np.max(C)>0 else 0), # Esagerazione verticale per visibilità
                x=X, y=Y,
                surfacecolor=C,
                colorscale='Jet',
                cmin=0, cmax=20, # Saturazione visuale
                opacity=0.9,
                name="Concentrazione",
                colorbar=dict(title="Conc. [ppm]")
            ))

            # Aggiungi Edifici (Come scatter 3D o cubi - qui semplificato come punti alti)
            if n_obst > 0:
                obs_y, obs_x = np.where(obstacles == 1)
                fig.add_trace(go.Scatter3d(
                    x=obs_x*dx, y=obs_y*dy, z=np.ones_like(obs_x)*10,
                    mode='markers',
                    marker=dict(size=5, color='black', symbol='square'),
                    name="Edifici"
                ))

            fig.update_layout(
                title=f"Evoluzione Temporale: t = {t*dt:.1f} s",
                scene=dict(
                    xaxis_title="X [m]",
                    yaxis_title="Y [m]",
                    zaxis_title="Quota [m]",
                    zaxis=dict(range=[0, 30]),
                    aspectratio=dict(x=2, y=1, z=0.5)
                ),
                margin=dict(l=0, r=0, b=0, t=40)
            )
            
            placeholder.plotly_chart(fig, use_container_width=True)
            
            # Statistiche in tempo reale
            max_c = np.max(C)
            tot_mass = np.sum(C)*dx*dy
            stats_placeholder.markdown(f"""
            **Monitoraggio in tempo reale:**
            * Picco Concentrazione: `{max_c:.2f} ppm`
            * Massa Totale Inquinante: `{tot_mass:.2f} kg_eq`
            """)
            
            # Piccolo sleep per vedere l'animazione
            time.sleep(0.05)
            # --- CALCOLO IMPATTO SUI PALAZZI ---
        if n_obst > 0:
            # Calcoliamo la concentrazione media sopra le aree occupate dai palazzi
            conc_sui_palazzi = np.mean(C[obstacles == 1]) 
            # Calcoliamo la "Dose" accumulata (integrale temporale approssimato)
            dose_palazzi = np.sum(C[obstacles == 1]) * dt
        else:
            conc_sui_palazzi = 0
            dose_palazzi = 0

        # --- AGGIORNAMENTO STATISTICHE ---
        stats_placeholder.markdown(f"""
        ### 📊 Monitoraggio Impatto Atmosferico
        * **Picco in aria:** `{np.max(C):.2f} ppm`
        * **Massa totale in sospensione:** `{np.sum(C)*dx*dy:.2f} kg_eq`
        
        ### 🏙️ Analisi Esposizione Urbana
        * **Concentrazione media sui palazzi:** `{conc_sui_palazzi:.2f} ppm`
        * **Rischio Ristagno:** {"🔴 ALTO" if conc_sui_palazzi > 5 else "🟢 BASSO"}
        * *Nota: I palazzi agiscono come barriere, forzando l'accumulo sul lato sopravvento.*
        """)

# --- TASTO START ---
if st.button("🚀 Avvia Simulazione Numerica"):
    run_simulation()
else:
    st.info("Configura i parametri nella barra laterale e premi 'Avvia' per calcolare la dispersione.")
