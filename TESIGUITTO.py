# --- 5. VISUALIZZAZIONE 3D CON MAPPA DI RISCHIO ALLA BASE ---
fig = go.Figure(data=[
    go.Surface(
        z=C, 
        colorscale='Jet', 
        cmin=0, 
        cmax=22, 
        name="Tossicità Gas",
        # Configurazione delle curve di livello colorate
        contours={
            "z": {
                "show": True,       # Mostra le curve
                "project_z": True,  # PROIETTA LE CURVE SUL PAVIMENTO (Fondamentale)
                "usecolormap": True, # Usa i colori (Rosso, Giallo, Blu) invece del nero
                "start": 0.5,       # Inizia a colorare sopra lo 0.5 PPM
                "end": 22,          # Finisce al picco di pericolosità
                "size": 1           # Distanza tra una curva e l'altra
            }
        },
        colorbar=dict(title="Concentrazione (PPM)", thickness=20)
    ),
    # I palazzi rimangono solidi
    go.Surface(z=edifici_altezze, colorscale='Greys', opacity=0.9, showscale=False)
])

fig.update_layout(
    scene=dict(
        zaxis=dict(range=[-1, 30], title="Quota / Intensità"), # range parte da -1 per far vedere bene la base
        xaxis_title="Distanza X",
        yaxis_title="Distanza Y",
        aspectmode='manual',
        aspectratio=dict(x=1, y=1, z=0.5)
    ),
    height=800
)

st.plotly_chart(fig, use_container_width=True)
