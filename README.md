# Analisi Numerica della Dispersione di Inquinanti
## Tesi di Laurea: Modelli di Inquinamento Ambientale con Impatto su Orografia e Topografia Urbana

Questo repository ospita il simulatore numerico sviluppato per lo studio delle equazioni alle derivate parziali di tipo parabolico (reazione-diffusione-trasporto).

### Caratteristiche del Modello:
- **Soluzione Numerica:** Implementazione di schemi alle differenze finite per termini di advezione e diffusione.
- **Topografia Urbana:** Gestione di ostacoli artificiali (palazzi) tramite matrici di mascheramento.
- **Orografia:** Inserimento di rilievi naturali nel dominio spaziale.
- **Visualizzazione:** Rendering 3D interattivo tramite Plotly e interfaccia Streamlit.

### Come eseguire la simulazione:
1. Installa i requisiti: `pip install -r requirements.txt`
2. Avvia l'app: `streamlit run TESIGUITTO.py`
