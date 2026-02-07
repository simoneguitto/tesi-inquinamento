import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd  # Fondamentale per l'export Excel

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Tesi Guitto Simone - Simulatore ADR", layout="wide")

# --- INTESTAZIONE ACCADEMICA ---
st.title("Sistema Integrato di Simulazione Dispersione Atmosferica")
st.markdown("""
### Analisi fluidodinamica e monitoraggio PPM
**Corso di Laurea in Ingegneria Civile e Ambientale - Università Uninettuno**

**Candidato:** Guitto Simone  
**Oggetto:** Simulazione dinamica modello ADR (Advezione-Diffusione-Reazione) con export dati per post-processing.
""")
st.markdown("---")

# --- SIDEBAR DI CONTROLLO ---
with st.sidebar:
    st.header("🎓 Dati Tesi")
    st.info("**Candidato:** Guitto Simone\n\n**Facoltà:** Ingegneria Civile e Ambientale")
    
    st.divider()
    
    st.header("🏢 Parametri Urbanistici")
    num_palazzi = st.slider("Numero edifici", 0, 10, 6)
    dist_primo = st.slider("Distanza sorgente (m)", 8, 20, 12)
    
    st.header("🌦️ Variabili Ambientali")
    v_kmh = st.slider("Vento (km/h)", 1.0, 40.0, 12.0)
    u_vento = v_kmh / 3.6 
    k_diff = st.slider("Diffusione (K)", 0.1, 2.5, 0.8)
    mm_pioggia = st.slider("Pioggia (mm/h)", 0, 100, 0)

# --- LOGICA E MAPPA ---
dt = 0.02
sigma_pioggia = (mm_pioggia / 100) * 0.4 
N = 50
edifici_mask = np.zeros((N, N))
edifici_altezze = np.zeros((N, N))
orografia = np.zeros((N, N))

np.random.seed(42)
if num_palazzi > 0:
    # Palazzo principale (Alto)
    edifici_mask[dist_primo:dist_primo+4, 23:27] = 1
    edifici_altezze[dist_primo:dist_primo+4, 23:27] = 13.0
    # Altri edifici
    for _ in range(num_palazzi - 1):
        px, py = np.random.randint(15, 45), np.random.randint(10, 40)
        h = np.random.choice([3.5, 7.0, 10.0, 15.0]) 
        edifici_mask[px:px+3, py:py+3] = 1
        edifici_altezze[px:px+3, py:py+3] = h

# --- ESECUZIONE ---
if st.sidebar.button("AVVIA SIMULAZIONE TECNICA"):
    C = np.zeros((N, N))
    mappa_box = st.empty()
    testo_box = st.empty()
    sx, sy = 5, 25 

    for t in range(180):
        Cn = C.copy()
        Cn[sx, sy] += 38 * dt # Calibrazione PPM (Target 3.7 - 4.0)
        
        for i in range(1, N-1):
            for j in range(1, N-1):
                if edifici_mask[i,j] == 1: continue
                diff = k_diff * dt * (C[i+1,j] + C[i-1,j] + C[i,j+1] + C[i,j-1] - 4*C[i,j])
                adv = -u_vento * dt * (C[i,j] - C[i-1,j])
                reac = -sigma_pioggia * dt * C[i,j]
                Cn[i,j] += diff + adv + reac
        C = np.where(edifici_mask == 1, 0, Cn)
        
        if t % 15 == 0:
            picco = np.max(C)
            fig = go.Figure(data=[
                go.Surface(z=C + orografia, colorscale='Jet', cmin=0.01, cmax=8, name="Concentrazione Gas"),
                go.Surface(z=edifici_altezze, colorscale='Greys', opacity=0.8, showscale=False, name="Edifici"),
            ])
            fig.update_layout(
                scene=dict(
                    zaxis=dict(range=[0, 20], title="Quota Z (m) / Conc. (PPM)"),
                    xaxis_title="Distanza X (m)", yaxis_title="Larghezza Y (m)"
                ),
                margin=dict(l=0, r=0, b=0, t=0), height=700
            )
            mappa_box.plotly_chart(fig, use_container_width=True)
            testo_box.info(f"Monitoraggio in tempo reale: Picco rilevato {picco:.2f} PPM")

    st.success("Analisi completata. Dati pronti per l'esportazione.")

    # --- CREAZIONE DEL FILE CSV PER EXCEL ---
    # Creiamo una tabella con tutti i dati della mappa finale
    dati_export = []
    for i in range(N):
        for j in range(N):
            valore_ppm = C[i,j]
            if valore_ppm > 0.1: # Salviamo solo i punti dove c'è gas per non appesantire il file
                dati_export.append({
                    "Coordinata X (m)": i,
                    "Coordinata Y (m)": j,
                    "Altezza Suolo (m)": orografia[i,j],
                    "Altezza Edificio (m)": edifici_altezze[i,j],
                    "Concentrazione (PPM)": round(valore_ppm, 4)
                })
    
    # Convertiamo in formato scaricabile
    df = pd.DataFrame(dati_export)
    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="💾 SCARICA DATASET COMPLETO (CSV/EXCEL)",
        data=csv,
        file_name='dati_tesi_guitto_simone.csv',
        mime='text/csv',
    )
