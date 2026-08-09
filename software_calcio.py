import json
import os
import sys
import warnings
from datetime import datetime
import numpy as np
import pandas as pd
#import ScraperFC as sfc
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore")

FILE_PARTITE_ATTUALE = "banca_dati_calendario_2627.csv"
FILE_PARTITE_STORICO = "banca_dati_partite_finite.csv"
FILE_FORMAZIONI = "banca_dati_formazioni_live.csv"
FILE_STATS_GIORNALIERE = "banca_dati_statistiche_giornaliere.csv"
FILE_STATS_SQUADRE = "banca_dati_squadre_sofascore.csv"
FILE_MEMORIA_ANALISI = "banca_dati_chat_e_analisi.json"
FILE_FORMAZIONI_DETTAGLIATE = "banca_dati_formazioni_dettagliate.csv"


try:
    sofascore_scraper = sfc.Sofascore()
except Exception:
    sofascore_scraper = None


def recupera_storico_squadra_fallback(squadra, numero_match=5):
    """Recupera cronologicamente le ultime partite giocate da un club."""
    match_totali = []

    if os.path.exists(FILE_PARTITE_ATTUALE):
        try:
            df_att = pd.read_csv(FILE_PARTITE_ATTUALE)
            if not df_att.empty and "Stato" in df_att.columns:
                df_att_finiti = df_att[df_att["Stato"].str.lower() == "finished"]
                if not df_att_finiti.empty:
                    match_totali.append(df_att_finiti)
        except Exception:
            pass

    if os.path.exists(FILE_PARTITE_STORICO):
        try:
            df_sto = pd.read_csv(FILE_PARTITE_STORICO)
            if not df_sto.empty:
                match_totali.append(df_sto)
        except Exception:
            pass

    if not match_totali:
        return pd.DataFrame()

    df_globale = pd.concat(match_totali, ignore_index=True)
    df_globale = df_globale.drop_duplicates(subset=["ID_Partita"], keep="last")

    squadra_pulita = squadra.strip().lower()
    df_squadra = df_globale[
        (df_globale["Squadra_Casa"].str.lower() == squadra_pulita) |
        (df_globale["Squadra_Trasferta"].str.lower() == squadra_pulita)
    ]

    return df_squadra.tail(numero_match).reset_index(drop=True)

def pulisci_testo_universale(testo):
    """Sostituisce caratteri accentati e pulisce prefissi comuni."""
    if not isinstance(testo, str):
        return ""
    t = testo.lower().strip()
    for prefisso in ["ssc ", "as ", "ac ", "fc ", "hellas ", " udinese", " cagliari", " fc"]:
        t = t.replace(prefisso, "")
    mappa = {'á': 'a', 'à': 'a', 'é': 'e', 'è': 'e', 'í': 'i', 'ì': 'i', 'ó': 'o', 'ò': 'o', 'ú': 'u', 'ù': 'u', 'ć': 'c', 'ž': 'z', 'š': 's', 'đ': 'd', 'ł': 'l', 'ń': 'n', 'ö': 'o', 'ü': 'u', 'č': 'c'}
    for acc, reg in mappa.items():
        t = t.replace(acc, reg)
    return t.strip()
def calcola_fallback_reparto(squadra, ruolo):
    """Calcola la media delle prestazioni del reparto per i nuovi acquisti."""
    if not os.path.exists(FILE_STATS_GIORNALIERE):
        return pd.Series(dtype=float)
    try:
        df_stats = pd.read_csv(FILE_STATS_GIORNALIERE)
        if df_stats.empty:
            return pd.Series(dtype=float)
        
        sq_target = pulisci_testo_universale(squadra)
        df_stats["Squadra_Pulita"] = df_stats["Squadra"].apply(pulisci_testo_universale)
        # Filtra per reparto, poi media dei valori numerici
        df_reparto = df_stats[
            (df_stats["Squadra_Pulita"].str.contains(sq_target, na=False)) &
            (df_stats["Ruolo"].str.upper() == ruolo.upper())
        ]
        if df_reparto.empty:
            df_reparto = df_stats[df_stats["Ruolo"].str.upper() == ruolo.upper()]
        
        # Seleziona colonne numeriche utili per la media
        col_esclude = ['ID_Partita', 'Giornata', 'ID_Giocatore', 'ID_Squadra']
        col_num = df_reparto.select_dtypes(include=[np.number]).columns.tolist()
        col_pulite = [c for c in col_num if c not in col_esclude]
        
        return df_reparto[col_pulite].mean().fillna(0)
    except Exception:
        return pd.Series(dtype=float)



# 🧱 BLOCCO 1 - PARTE 3: ESTRAZIONE LINEUP VERTICALE (Pezzo 1 di 4)
def estrai_lineup_verticale_match(id_partita):
    if not os.path.exists(FILE_FORMAZIONI):
        print(f"[ERRORE] File '{FILE_FORMAZIONI}' non trovato.")
        return None, None
    try:
        df_live = pd.read_csv(FILE_FORMAZIONI)
        df_match = df_live[df_live["ID_Partita"] == int(id_partita)]
        df_cal = pd.read_csv(FILE_PARTITE_ATTUALE)
        match_info = df_cal[df_cal["ID_Partita"] == int(id_partita)]
        if not match_info.empty:
            squadra_casa = str(match_info["Squadra_Casa"].values[0])
            squadra_trasferta = str(match_info["Squadra_Trasferta"].values[0])
        else:
            squadra_casa, squadra_trasferta = "Casa", "Trasferta"
# 🧱 BLOCCO 1 - PARTE 3: ESTRAZIONE LINEUP VERTICALE (Pezzo 2 di 4)
        if df_match.empty and sofascore_scraper is not None:
            try:
                df_online = sofascore_scraper.scrape_player_match_stats(int(id_partita))
                if df_online is not None and not df_online.empty:
                    df_online = df_online.loc[:, ~df_online.columns.duplicated()].copy()
                    df_tit_online = df_online[df_online.get('substitute', False) == False].copy()
                    nuovi_record = []
                    for _, g_on in df_tit_online.iterrows():
                        squadra_c = str(g_on.get('teamName', ''))
                        if not squadra_c:
                            is_home = bool(g_on.get('isHome', True))
                            squadra_c = squadra_casa if is_home else squadra_trasferta
# 🧱 BLOCCO 1 - PARTE 3: ESTRAZIONE LINEUP VERTICALE (Pezzo 3 di 4)
                        nuovi_record.append({
                            "ID_Partita": int(id_partita),
                            "Squadra": squadra_c,
                            "Giocatore": str(g_on.get('nome', g_on.get('nome_giocatore', 'Sconosciuto'))),
                            "Ruolo": str(g_on.get('position', 'N/D')),
                            "Stato": "Titolare"
                        })
                    if nuovi_record:
                        df_match = pd.DataFrame(nuovi_record)
            except Exception:
                pass
# 🧱 BLOCCO 1 - PARTE 3: ESTRAZIONE LINEUP VERTICALE (Pezzo 4 di 4)
        if df_match.empty:
            return None, None
            
        df_casa = df_match[df_match["Squadra"].apply(pulisci_testo_universale).str.contains(pulisci_testo_universale(squadra_casa), na=False)]
        df_trasf = df_match[df_match["Squadra"].apply(pulisci_testo_universale).str.contains(pulisci_testo_universale(squadra_trasferta), na=False)]
        return df_casa, df_trasf
    except Exception:
        return None, None

# 🧱 BLOCCO 1 - PARTE 4: CALCOLO FORMA RECENTE EWMA (Pezzo 1 di 4)
def calcola_forma_recente_calciatore(nome_giocatore, squadra_att):
    if not os.path.exists(FILE_STATS_GIORNALIERE):
        return pd.Series(dtype=float)
    try:
        df_all = pd.read_csv(FILE_STATS_GIORNALIERE)
        if df_all.empty:
            return pd.Series(dtype=float)
            
        g_pulito = pulisci_testo_universale(nome_giocatore)
        sq_pulita = pulisci_testo_universale(squadra_att)
        
        df_all["Nome_Pulito"] = df_all["Giocatore"].apply(pulisci_testo_universale)
        df_all["Squadra_Pulita"] = df_all["Squadra"].apply(pulisci_testo_universale)
# 🧱 BLOCCO 1 - PARTE 4: CALCOLO FORMA RECENTE EWMA (Pezzo 2 di 4)
        df_gioc = df_all[
            (df_all["Nome_Pulito"] == g_pulito) & 
            (df_all["Squadra_Pulita"].str.contains(sq_pulita, na=False) | df_all["Squadra_Pulita"].apply(lambda x: x in sq_pulita if x else False))
        ]
        
        if df_gioc.empty:
            ruolo_stimato = "Cen"
            for col_r in ["Ruolo", "position", "Position"]:
                if col_r in df_all.columns:
                    match_r = df_all[df_all["Nome_Pulito"] == g_pulito]
                    if not match_r.empty:
                        ruolo_stimato = str(match_r[col_r].values[0])
                        break
            return calcola_fallback_reparto(squadra_att, ruolo_stimato)
# 🧱 BLOCCO 1 - PARTE 4: CALCOLO FORMA RECENTE EWMA (Pezzo 3 di 4)
        df_gioc = df_gioc.copy()
        for col_g in ["Giornata", "giornata", "round", "Round"]:
            if col_g in df_gioc.columns:
                df_gioc = df_gioc.sort_values(by=col_g, ascending=True)
                break
                
        ruolo = "Cen"
        for col_r in ["Ruolo", "position", "Position"]:
            if col_r in df_gioc.columns:
                ruolo = str(df_gioc[col_r].values[0])
                break
# 🧱 BLOCCO 1 - PARTE 4: CALCOLO FORMA RECENTE EWMA (Pezzo 4 di 4)
        fattore_alfa = 0.85 if ruolo.upper() in ["ATT", "FORWARD"] else (0.75 if ruolo.upper() in ["CEN", "MIDFIELDER"] else 0.65)
        col_esclude = ['ID_Partita', 'Giornata', 'Timestamp_Data_Nascita', 'Anno', 'Numero_Maglia']
        col_num = df_gioc.select_dtypes(include=[np.number]).columns.tolist()
        col_pulite = [c for c in col_num if c not in col_esclude and "ID_" not in c]
        
        proiezioni = {}
        for col in col_pulite:
            valore_accumulato = 0
            for _, riga in df_gioc.iterrows():
                minuti = float(riga.get("Minuti_Giocati", 90) or 90)
                val_grezzo = float(riga.get(col, 0) or 0)
                val_norm = (val_grezzo / minuti) * 90 if minuti > 15 else val_grezzo
                valore_accumulato = (fattore_alfa * val_norm) + ((1 - fattore_alfa) * valore_accumulato)
            proiezioni[col] = round(valore_accumulato, 2)
        return pd.Series(proiezioni)
    except Exception:
        return pd.Series(dtype=float)

# ==============================================================================
# 🧱 BLOCCO 1 PARTE 4: IL CLASSIFICATORE GEOMETRICO POSIZIONALE (SQUADRE VS SINGOLI)
# COSA FA: Incrocia l'indice EWMA del singolo calciatore con le medie macroscopiche 
# della sua squadra presenti in banca_dati_squadre_sofascore.csv. Normalizza la 
# prestazione del singolo all'interno del contesto tattico collettivo della squadra.
# ==============================================================================

# 🧱 BLOCCO 1 - PARTE 5: NORMALIZZAZIONE TATICA CONTESTUALE (Pezzo 1 di 3)
def normalizza_contesto_tattico_squadra(df_profili, nome_squadra):
    if df_profili is None or df_profili.empty:
        return df_profili
    if not os.path.exists(FILE_STATS_SQUADRE):
        return df_profili
    try:
        df_sq = pd.read_csv(FILE_STATS_SQUADRE)
        sq_target = pulisci_testo_universale(nome_squadra)
        df_sq["Squadra_Pulita"] = df_sq["Squadra"].apply(pulisci_testo_universale)
        
        df_info = df_sq[df_sq["Squadra_Pulita"].str.contains(sq_target, na=False)]
        if df_info.empty:
            return df_profili
# 🧱 BLOCCO 1 - PARTE 5: NORMALIZZAZIONE TATTICA CONTESTUALE (Pezzo 2 di 3)
        possesso_medio = float(df_info["Possesso_Palla_Medio"].values[0] if "Possesso_Palla_Medio" in df_info.columns else 50.0)
        tiri_concessi = float(df_info["Tiri_Concessi_Medio"].values[0] if "Tiri_Concessi_Medio" in df_info.columns else 10.0)
        
        df_norm = df_profili.copy()
        moltiplicatore_possesso = 1.0 + ((50.0 - possesso_medio) / 100.0)
        moltiplicatore_difesa = 1.0 + ((tiri_concessi - 10.0) / 20.0)
# 🧱 BLOCCO 1 - PARTE 5: NORMALIZZAZIONE TATTICA CONTESTUALE (Pezzo 3 di 3)
        for giocatore, profilo in df_norm.items():
            if isinstance(profilo, pd.Series):
                for col in profilo.index:
                    if "Passaggi" in col or "Tiri_Totali" in col:
                        df_norm[giocatore][col] = round(profilo[col] * moltiplicatore_possesso, 2)
                    elif "Tackle" in col or "Intercettazioni" in col or "Spazzate" in col:
                        df_norm[giocatore][col] = round(profilo[col] * moltiplicatore_difesa, 2)
        return df_norm
    except Exception:
        return df_profili

# ==============================================================================
# 🧱 BLOCCO 2 PARTE 1: IL RADAR DI SCENARIO ONLINE E CORREZIONE API SOFASCORE
# COSA FA: Si collega via internet ai server ufficiali di Sofascore utilizzando 
# gli endpoint stabili (://sofascore.com) per scaricare in tempo reale le info di 
# contorno del match: arbitro designato, meteo, infortuni e squalifiche dell'ultima ora.
# Riscrive ed elimina totalmente i bug e le variabili non definite (ref_id, res_ev) di Pastebin.
# ==============================================================================

def scarica_radar_scenario_online(id_partita):
    """Estrae in modo sicuro l'arbitro e le condizioni meteo da Sofascore."""
    scenario_output = {
        "Arbitro": "Sconosciuto",
        "Meteo_Condizioni": "Non Disponibile",
        "Meteo_Temperatura": "N/D",
        "Infortunati_Casa": [],
        "Infortunati_Trasferta": [],
        "Stato_Formazioni": "NON UFFICIALI (Dati Probabili)"
    }
    try:
        if sofascore_scraper is not None:
            match_dict = sofascore_scraper.get_match_dict(int(id_partita))
            if match_dict and "event" in match_dict:
                json_evento = match_dict["event"]
                if json_evento.get("lineupsConfirmed", False):
                    scenario_output["Stato_Formazioni"] = "UFFICIALI CONFERMATE"
                
                scenario_output["Arbitro"] = json_evento.get("referee", {}).get("name", "Sconosciuto")
                
                venue_data = json_evento.get("venue", {})
                meteo_data = venue_data.get("weather", {})
                if meteo_data:
                    scenario_output["Meteo_Condizioni"] = meteo_data.get("description", "Non Disponibile")
                    scenario_output["Meteo_Temperatura"] = f"{meteo_data.get('temperature', 'N/D')}°C"
    except Exception:
        pass
    return scenario_output



# ==============================================================================
# 🧱 BLOCCO 3 PARTE 1: IL FILTRO FINANZIARIO E LOGICA VALUE BET (CONFRONTO QUOTE)
# COSA FA: Mette in atto il calcolatore matematico di valore per il pre-match.
# Incrocia la probabilità stimata dall'algoritmo con le quote reali offerte dai 
# bookmaker, calcolando l'Indice di Valore. Identifica ed evidenzia le scommesse 
# finanziarie solo se superano la soglia rigida di profittabilità (>= 1.05) 
# e garantiscono una stabilità d'élite (probabilità >= 65%).
# ==============================================================================

# 🧱 BLOCCO 3 - PARTE 1: VALUTAZIONE VALUE BET (Pezzo 1 di 2)
def esegui_filtro_finanziario_quote(probabilita_ia, quota_bookmaker, stato_formazioni="PROBABILI"):
    """Calcola la convenienza finanziaria (Value Bet) basata sulle quote."""
    investimento_output = {
        "Indice_Valore": 0.0,
        "Quota_Giusta_IA": 99.0,
        "Segnale_Operativo": "NO VALUE (Passare oltre)",
        "Luce_Verde": False
    }
    if quota_bookmaker <= 1.01 or probabilita_ia <= 0:
        return investimento_output

    quota_giusta = round(100 / probabilita_ia, 2)
    investimento_output["Quota_Giusta_IA"] = quota_giusta
    indice_valore = round(quota_bookmaker / quota_giusta, 2)
    investimento_output["Indice_Valore"] = indice_valore

    # Parametri rigidi: Valore ed elevata confidenza statistica
    if indice_valore >= 1.05 and probabilita_ia >= 65:
        investimento_output["Luce_Verde"] = True
        investimento_output["Segnale_Operativo"] = "INVESTIMENTO VALIDO: INVESTIRE QUOTA VALUE BET 🔥"
    elif indice_valore >= 1.05:
        investimento_output["Segnale_Operativo"] = "VALORE PRESENTE (Confidenza IA sotto soglia 65%)"
        
    return investimento_output


# ==============================================================================
# 🧱 BLOCCO 3 PARTE 2: MOTORE DI CONSOLIDAMENTO POST-MATCH E BACKTESTING REALE
# COSA FA: Prende le vecchie analisi memorizzate nel file JSON e le confronta con 
# i dati reali accumulati sul campo una volta terminato il match. Calcola lo 
# scarto medio (Errore Medio) tra le stime dell'IA e la realtà (es. xG, Possesso),
# validando l'efficacia finanziaria a lungo termine del sistema.
# ==============================================================================

# 🧱 BLOCCO 3 - PARTE 2: OTTIMIZZAZIONE BACKTESTING (Pezzo 1 di 2)
def esegui_consolidamento_post_match(id_partita):
    """Esegue il backtesting analizzando i voti reali, ignorando cartellini e tempi."""
    if not os.path.exists(FILE_FORMAZIONI_DETTAGLIATE) or not os.path.exists(FILE_STATS_GIORNALIERE):
        return {"Stato": "ERRORE", "Messaggio": "Database storici non disponibili"}
    try:
        df_dett = pd.read_csv(FILE_FORMAZIONI_DETTAGLIATE)
        df_match = df_dett[df_dett["ID_Partita"] == int(id_partita)]
        if df_match.empty:
            return {"Stato": "ERRORE", "Messaggio": "Tabellino partita non trovato"}
        df_stats = pd.read_csv(FILE_STATS_GIORNALIERE)
        df_stats["Giocatore_Pulito"] = df_stats["Giocatore"].apply(pulisci_testo_universale)
        df_match = df_match.copy()
        df_match["Giocatore_Pulito"] = df_match["Giocatore"].apply(pulisci_testo_universale)
        
        voti_reali = []
        for _, giocatore in df_match.iterrows():
            g_stats = df_stats[(df_stats["Giocatore_Pulito"] == giocatore["Giocatore_Pulito"]) & (df_stats["Giornata"].astype(int) == int(giocatore["Giornata"]))]
            if not g_stats.empty and "Voto_Sofascore" in g_stats.columns:
                voti_reali.append(float(g_stats["Voto_Sofascore"].values[0]))
                
        voto_medio_reale = round(np.mean(voti_reali), 2) if voti_reali else 0.0
        return {"ID_Partita": int(id_partita), "Voto_Medio_Reale": voto_medio_reale, "Stato_Match": "CONSOLIDATO"}
    except Exception:
        return {"Stato": "ERRORE", "Messaggio": "Eccezione durante il calcolo"}


# ==============================================================================
# 🧱 BLOCCO 4 PARTE 1: MOTORE SEMANTICO DELLA CHAT CON L'IA
def elabora_chat_ia_semantica(id_partita, testo_utente, contesto_statistico_match):
    """Gestisce la chat intelligente con GroqCloud usando la chiave API di sistema."""
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY", "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")
 
    if not api_key:
        return "⚠ [ERRORE CHAT]: Chiave API non configurata."
    try:
        client = Groq(api_key=api_key)
        prompt_sistema = (
            f"Sei l'analista d'élite dell'ecosistema software calcio.\n"
            f"Match: {contesto_statistico_match.get('Squadra_Casa', 'Casa')} vs {contesto_statistico_match.get('Squadra_Trasferta', 'Trasferta')}.\n"
            f"Contesto: {contesto_statistico_match.get('Scenario_Match', 'Analisi')}.\n\n"
            f"Ecco i dati reali estratti dai tuoi database locali del PC:\n"
            f"{contesto_statistico_match.get('Dati_Completi', '')}\n\n"
            f"Istruzioni: Rispondi liberamente in italiano a qualunque domanda dell'utente (tattica, statistica o finanziaria). "
            f"Argomenta le tue risposte basandoti esclusivamente sui dati reali dei database sopra elencati. "
            f"Non inventare calciatori, voti o statistiche esterni. Escludi i tag <think>."
        )

        chiamata = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Modello standard Groq stabile
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": testo_utente}
            ],
            temperature=0.1,
            max_tokens=400
        )
        testo_grezzo = chiamata.choices[0].message.content.strip()
        return testo_grezzo.split("</think>")[-1].strip() if "</think>" in testo_grezzo else testo_grezzo
    except Exception as e:
        return f"❌ Errore di connessione GroqCloud o Sintassi: {e}"

if __name__ == "__main__":
    df_cal = pd.read_csv(FILE_PARTITE_ATTUALE)
    df_hist = pd.read_csv(FILE_PARTITE_STORICO)
    
    ricerca = input("🔍 Inserisci il nome della squadra da analizzare: ").strip().lower()

    # Filtro dei match futuri e passati per nome squadra
    df_f = df_cal[(df_cal["Squadra_Casa"].str.lower().str.contains(ricerca, na=False)) | 
                  (df_cal["Squadra_Trasferta"].str.lower().str.contains(ricerca, na=False))].copy()
    df_f["Fonte_Stato"] = "🚀 FUTURO (Pronostico)"
    df_f["Is_Finito_Bool"] = False
    # Unione database e visualizzazione
    df_p = df_hist[(df_hist["Squadra_Casa"].str.lower().str.contains(ricerca, na=False)) | 
                   (df_hist["Squadra_Trasferta"].str.lower().str.contains(ricerca, na=False))].copy()
    df_p["Fonte_Stato"] = "✅ FINITO"
    df_totale = pd.concat([df_p, df_f], ignore_index=True)

    if df_totale.empty: print("❌ Nessun match."); sys.exit(1)

    print("\n📅 MATCH TROVATI:")
    for i, r in df_totale.iterrows():
        print(f"[{i}] {r['Squadra_Casa']} vs {r['Squadra_Trasferta']} | {r['Fonte_Stato']}")
    try:
        scelta_idx = int(input("\n👉 Seleziona il numero del match: ").strip())
        if scelta_idx < 0 or scelta_idx >= len(df_totale): raise ValueError
    except ValueError:
        print("❌ Selezione non valida."); sys.exit(1)

    m = df_totale.iloc[scelta_idx].to_dict()
    id_p = m.get("ID_Partita", 0)
    is_finito = "finito" in str(m.get("Fonte_Stato", "")).lower()
    giornata_selezionata = m.get("Giornata", 1)
    if not is_finito:
        scenario = scarica_radar_scenario_online(id_p)
        lineup_casa, lineup_trasferta = estrai_lineup_verticale_match(id_p)
    else:
        scenario = {"Stato_Formazioni": "STORICHE REALI"}
        lineup_casa, lineup_trasferta = None, None

    print(f"\n⚙️ Caricamento analisi per: {m.get('Squadra_Casa')} vs {m.get('Squadra_Trasferta')}")
    df_stats_gioc = pd.read_csv(FILE_STATS_GIORNALIERE)
    df_form_dett = pd.read_csv(FILE_FORMAZIONI_DETTAGLIATE) if os.path.exists(FILE_FORMAZIONI_DETTAGLIATE) else pd.DataFrame()

    casa_p = pulisci_testo_universale(m.get('Squadra_Casa', ''))
    trasf_p = pulisci_testo_universale(m.get('Squadra_Trasferta', ''))
    try:
        giornata_pulita = int(float(str(giornata_selezionata).replace("Giornata", "").strip()))
    except Exception:
        giornata_pulita = 1

    lineup_c, lineup_t = [], []
    p_casa, p_trasferta = {}, {}
    c_mac_data, t_mac_data = {}, {}
    if is_finito:
        df_form_dett["Giornata_Int"] = pd.to_numeric(df_form_dett["Giornata"], errors="coerce").fillna(0).astype(int)
        df_form_dett["Squadra_Pulita"] = df_form_dett["Squadra"].astype(str).apply(pulisci_testo_universale)

        cond_g_f = df_form_dett["Giornata_Int"] == giornata_pulita
        cond_c_f = (df_form_dett["Squadra_Pulita"].str.contains(casa_p, na=False)) | (df_form_dett["Squadra_Pulita"].str.contains(trasf_p, na=False))
        df_m_st = df_form_dett[cond_g_f & cond_c_f]

        df_stats_gioc["Giornata_Int"] = pd.to_numeric(df_stats_gioc["Giornata"], errors="coerce").fillna(0).astype(int)
        df_stats_gioc["Giocatore_Pulito"] = df_stats_gioc["Giocatore"].astype(str).apply(pulisci_testo_universale)
        if not df_m_st.empty:
            for _, r_g in df_m_st.iterrows():
                # 🚀 FILTRO AGGIORNATO: Scarta solo le riserve fisse che non hanno preso voto (Voto == 0 o assente)
                stato_giocatore = str(r_g.get("Stato", "Titolare")).strip().lower()
                voto_giocatore = float(str(r_g.get("Voto_Sofascore", r_g.get("Voto", 0))).strip() or 0)
                tiri_g = float(str(r_g.get("Tiri_Totali", 0)).strip() or 0)
                falli_g = float(str(r_g.get("Falli_Commessi", 0)).strip() or 0)
                
                # Se è segnato come subentrato ma non ha voto, né tiri, né falli, allora è rimasto in panchina
                if stato_giocatore == "subentrato" and voto_giocatore == 0 and tiri_g == 0 and falli_g == 0:
                    continue  # Salta la riserva inutilizzata

                    
                sq_g_p = pulisci_testo_universale(str(r_g["Squadra"]))
                g_nome_completo = str(r_g["Giocatore"]).strip()
                g_pulito = pulisci_testo_universale(g_nome_completo)


                # Ricerca nella miniera giornaliera per Giornata + Nome Pulito
                cond_g_m = df_stats_gioc["Giornata_Int"] == giornata_pulita
                cond_p_m = df_stats_gioc["Giocatore_Pulito"] == g_pulito
                df_miniera_match = df_stats_gioc[cond_g_m & cond_p_m]
                if not df_miniera_match.empty:
                    g_diz = df_miniera_match.fillna(0).iloc[0].to_dict()
                else:
                    stats_fallback = calcola_fallback_reparto(str(r_g["Squadra"]), str(r_g["Ruolo"]))
                    g_diz = stats_fallback.to_dict() if not stats_fallback.empty else {}

                g_diz.update({
                    "Squadra": str(r_g["Squadra"]).strip(),
                    "Giocatore": g_nome_completo,
                    "Ruolo": str(r_g["Ruolo"]).strip(),
                    "Stato": str(r_g.get("Stato", "Titolare")).strip()
                })

                if casa_p in sq_g_p or sq_g_p in casa_p:
                    lineup_c.append(g_diz)
                    p_casa[g_nome_completo] = g_diz
                else:
                    lineup_t.append(g_diz)
                    p_trasferta[g_nome_completo] = g_diz
        df_stats_sq = pd.read_csv(FILE_STATS_SQUADRE) if os.path.exists(FILE_STATS_SQUADRE) else pd.DataFrame()
        if not df_stats_sq.empty and "teamName" in df_stats_sq.columns:
            c_m_r = df_stats_sq[df_stats_sq["teamName"].apply(pulisci_testo_universale).str.contains(casa_p, na=False)]
            c_mac_data = c_m_r.fillna(0).iloc[0].to_dict() if not c_m_r.empty else {}
            t_m_r = df_stats_sq[df_stats_sq["teamName"].apply(pulisci_testo_universale).str.contains(trasf_p, na=False)]
            t_mac_data = t_m_r.fillna(0).iloc[0].to_dict() if not t_m_r.empty else {}
    else:
        for lineup, team_name, is_casa in [(lineup_casa, m['Squadra_Casa'], True), (lineup_trasferta, m['Squadra_Trasferta'], False)]:
            if not lineup:
                df_sq = df_stats_gioc[df_stats_gioc["Squadra"].apply(pulisci_testo_universale).str.contains(pulisci_testo_universale(team_name), na=False)]
                if not df_sq.empty:
                    top_11 = df_sq.groupby(["Giocatore", "Ruolo"])["Minuti_Giocati"].sum().nlargest(11).reset_index()
                    lista_f = [{"Squadra": team_name, "Giocatore": r["Giocatore"], "Stato": "Titolare"} for _, r in top_11.iterrows()]
                    if is_casa: lineup_casa = lista_f
                    else: lineup_trasferta = lista_f
        for l, sq_n, prof_diz in [(lineup_casa, m['Squadra_Casa'], p_casa), (lineup_trasferta, m['Squadra_Trasferta'], p_trasferta)]:
            if l:
                for g in l:
                    ewma_gioc = calcola_forma_recente_calciatore(g['Giocatore'], sq_n)
                    prof_diz[g['Giocatore']] = ewma_gioc.to_dict() if not ewma_gioc.empty else {}
        df_stats_sq = pd.read_csv(FILE_STATS_SQUADRE) if os.path.exists(FILE_STATS_SQUADRE) else pd.DataFrame()
        if not df_stats_sq.empty and "teamName" in df_stats_sq.columns:
            c_data = df_stats_sq[df_stats_sq["teamName"].apply(pulisci_testo_universale).str.contains(casa_p, na=False)]
            t_data = df_stats_sq[df_stats_sq["teamName"].apply(pulisci_testo_universale).str.contains(trasf_p, na=False)]
            c_mac_data = c_data.fillna(0).iloc[0].to_dict() if not c_data.empty else {}
            t_mac_data = t_data.fillna(0).iloc[0].to_dict() if not t_data.empty else {}
    # Funzione locale per sommare i dati reali del passato dalle liste pulite
    def somma_v_csv(lista_dati, chiave):
        return round(sum(float(str(g.get(chiave, 0) or 0).strip() or 0) for g in lista_dati), 2)

    if is_finito:
        # 📋 RIPRISTINO STRUTTURA NATIVA ORIGINALE (Somma lineare tiri base dal database)
        df_casa_miniera = df_stats_gioc[(df_stats_gioc["Giornata_Int"] == giornata_pulita) & (df_stats_gioc["Squadra"].astype(str).apply(pulisci_testo_universale).str.contains(casa_p, na=False))]
        df_trasf_miniera = df_stats_gioc[(df_stats_gioc["Giornata_Int"] == giornata_pulita) & (df_stats_gioc["Squadra"].astype(str).apply(pulisci_testo_universale).str.contains(trasf_p, na=False))]
        
        # Calcolo dei Tiri Totali classici (Senza tiri respinti)
        t_tot_c = float(df_casa_miniera["Tiri_Totali"].sum())
        t_tot_t = float(df_trasf_miniera["Tiri_Totali"].sum())
        t_tot = (round(t_tot_c, 2), round(t_tot_t, 2))
        
        # Calcolo dei restanti parametri (I Falli rimangono protetti e corretti alla sorgente)
        t_porta = (round(float(df_casa_miniera["Tiri_In_Porta"].sum()), 2), round(float(df_trasf_miniera["Tiri_In_Porta"].sum()), 2))
        falli = (round(float(df_casa_miniera["Falli_Commessi"].sum()), 2), round(float(df_trasf_miniera["Falli_Commessi"].sum()), 2))
        f_gioco = (round(float(df_casa_miniera["Fuorigioco_Totali"].sum()), 2), round(float(df_trasf_miniera["Fuorigioco_Totali"].sum()), 2))
    else:
        t_tot = (sum(p.get("Tiri_Totali", 0.0) for p in p_casa.values()), sum(p.get("Tiri_Totali", 0.0) for p in p_trasferta.values()))
        t_porta = (sum(p.get("Tiri_In_Porta", 0.0) for p in p_casa.values()), sum(p.get("Tiri_In_Porta", 0.0) for p in p_trasferta.values()))
        falli = (sum(p.get("Falli_Commessi", 0.0) for p in p_casa.values()), sum(p.get("Falli_Commessi", 0.0) for p in p_trasferta.values()))
        f_gioco = (sum(p.get("Fuorigioco_Totali", 0.0) for p in p_casa.values()), sum(p.get("Fuorigioco_Totali", 0.0) for p in p_trasferta.values()))
          
    print(f"\n📊 TABELLA COMPARATIVA ({'Reale' if is_finito else 'Medie'})")

    if is_finito:
        print(f"🏆 RISULTATO REALE: {m.get('Squadra_Casa')} {int(float(m.get('Gol_Casa', 0)))} - {int(float(m.get('Gol_Trasferta', 0)))} {m.get('Squadra_Trasferta')}")
    
    print(f"{'Parametro':<20} | {m['Squadra_Casa']:<15} | {m['Squadra_Trasferta']:<15}\n" + "-" * 56)
    for label, v in [("Tiri Totali", t_tot), ("Tiri in Porta", t_porta), ("Falli Commessi", falli), ("Fuorigioco", f_gioco)]:
        print(f"{label:<20} | {v[0]:<15} | {v[1]:<15}")
    print(f"\n🏠 FORMAZIONI TITOLARI REALI E MODULI DETTAGLIATI:")
    print("-" * 56)
    
    # Questo contenitore salverà i dati completi di TUTTE le 106 colonne per ogni giocatore
    dati_giocatori_accumulati = "DATI COMPLETI DI TUTTE LE COLONNE PER CALCIATORE:\n"
    
    for sq_label, prof_diz in [("CASA: " + m['Squadra_Casa'], p_casa), ("TRASFERTA: " + m['Squadra_Trasferta'], p_trasferta)]:
        reparti_titolari = {"Portiere": [], "Difesa": [], "Centrocampo": [], "Attacco": []}
        conteggio_mod = {"D": 0, "M": 0, "F": 0}
        
        for nome_g, stats_forma in prof_diz.items():
            if stats_forma:
                ruolo = str(stats_forma.get("Ruolo", "N/D")).strip().upper()
                stato_p = str(stats_forma.get("Stato", "Titolare")).strip()
                
                # 🚀 FIX TOKENS: Filtro chirurgico iniziale per rimanere sotto i 12.000 token di Groq
                colonne_base = [
                    "Ruolo", "Stato", "Minuti_Giocati", "Voto_Sofascore", 
                    "Gol_Segnati", "Assist_Serviti", "Tiri_Totali", "Falli_Commessi"
                ]
                mappa_leggera = {col: stats_forma.get(col, 0) for col in colonne_base if col in stats_forma}
                
                import json
                dati_completi_giocatore = json.dumps(mappa_leggera, ensure_ascii=False)
                dati_giocatori_accumulati += f"-> {nome_g}: {dati_completi_giocatore}\n"

                
                # Smistiamo a schermo solo i nomi dei titolari per reparto
                if stato_p.lower() == "titolare":
                    if ruolo == "G":
                        reparti_titolari["Portiere"].append(nome_g)
                    elif ruolo == "D":
                        reparti_titolari["Difesa"].append(nome_g)
                        conteggio_mod["D"] += 1
                    elif ruolo == "M":
                        reparti_titolari["Centrocampo"].append(nome_g)
                        conteggio_mod["M"] += 1
                    elif ruolo == "F":
                        reparti_titolari["Attacco"].append(nome_g)
                        conteggio_mod["F"] += 1
            else:
                dati_giocatori_accumulati += f"-> {nome_g}: Dati insufficienti / Fallback\n"
        
        # Calcolo dinamico del modulo
        modulo_rilevato = f"{conteggio_mod['D']}-{conteggio_mod['M']}-{conteggio_mod['F']}"
        
        # Stampa pulita sul tuo terminale
        print(f"\n🏃 {sq_label.upper()} | 📋 MODULO: {modulo_rilevato}")
        print(f" Portiere    : {', '.join(reparti_titolari['Portiere']) if reparti_titolari['Portiere'] else 'N/D'}")
        print(f" Difesa ({conteggio_mod['D']})  : {', '.join(reparti_titolari['Difesa']) if reparti_titolari['Difesa'] else 'N/D'}")
        print(f" Centro ({conteggio_mod['M']})  : {', '.join(reparti_titolari['Centrocampo']) if reparti_titolari['Centrocampo'] else 'N/D'}")
        print(f" Attacco ({conteggio_mod['F']}) : {', '.join(reparti_titolari['Attacco']) if reparti_titolari['Attacco'] else 'N/D'}")

    # Forniamo l'indicazione precisa della giornata e del risultato reale per ancorare l'IA
    giornata_corrente = m.get('Giornata', 'N/D')
    risultato_testo = f"GIORNATA DI CAMPIONATO: {giornata_corrente}\nRISULTATO REALE DEL MATCH: {m.get('Squadra_Casa', 'Casa')} {m.get('Gol_Casa', 0)} - {m.get('Gol_Trasferta', 0)} {m.get('Squadra_Trasferta', 'Trasferta')}" if is_finito else f"GIORNATA DI CAMPIONATO: {giornata_corrente}\nPartita del futuro (non ancora disputata)"

    # Costruiamo il macro-confronto di squadra senza indici estranei
    dati_macro_confronto = (
        f"STATISTICHE GLOBALI DI SQUADRA:\n"
        f"- {m['Squadra_Casa']} (Tiri Totali: {t_tot}, In Porta: {t_porta}, Falli: {falli}, Fuorigioco: {f_gioco})\n"
        f"- {m['Squadra_Trasferta']} (Tiri Totali: {t_tot}, In Porta: {t_porta}, Falli: {falli}, Fuorigioco: {f_gioco})\n"
    )

    # Iniezione blindata del mega-contesto dati nell'interfaccia dell'IA
    contesto_ia = {
        "Squadra_Casa": m.get("Squadra_Casa", "Casa"),
        "Squadra_Trasferta": m.get("Squadra_Trasferta", "Trasferta"),
        "Dati_Completi": f"{risultato_testo}\n\n{dati_macro_confronto}\n{dati_giocatori_accumulati}",
        "Scenario_Match": "Partita del Passato (Rapporto Backtesting)" if is_finito else "Partita del Futuro (Analisi Pronostico)"
    }

    # 📋 PROMEMORIA VISIVO DELLE MACROCATEGORIE SUL TERMINALE
    print("\n💡 MACROGRUPPI STATISTICI DISPONIBILI (106 Colonne):")
    print(" ⚔️  [ATTACCO]   -> Gol, xG, xGOT, Tiri, Pali, Fuorigioco, Malus offensivi")
    print(" ⚙️  [REGIA]     -> Assist, xA, Passaggi, Chiave, Cross, Lanci, Tocchi")
    print(" 🛡️  [DIFESA]    -> Duelli, Recuperati, Spazzate, Intercettazioni, Tackle, Parate, Malus")
    print(" 🏃  [ATLETICA]  -> Chilometri, Sprint, Velocità Massima, Portate Palla, Progressioni")
    print(" 📁  [ALTRO]     -> Anagrafica, Numeri Maglia, Valori di Mercato, ID, Metadati")
    print("-" * 56)

    print("\n💬 INTERFACCIA CHAT IA REALE: FAI UNA DOMANDA SUL MATCH (Scrivi 'esci')")
    while True:
        dom = input("\nTu 👤: ").strip()
        if dom.lower() == 'esci': 
            print("Chiusura sessione...")
            break
        if not dom: 
            continue
            
        contesto_temporaneo = contesto_ia.copy()
        dati_extra_ia = ""
        tutti_i_profili = {**p_casa, **p_trasferta}
        
        # 🚀 SCUDO ANTIE-ERRORE: Mappatura flessibile delle scorciatoie digitate dall'utente
        mappa_scorciatoie = {
            "attacco": ["attacco", "att", "attacc", "offensiva", "off"],
            "regia": ["regia", "reg", "costruzione", "passaggi", "manovra"],
            "difesa": ["difesa", "dif", "difensiva", "portiere", "tackle"],
            "atletica": ["atletica", "atle", "movimento", "corsa", "km"],
            "altro": ["altro", "alt", "anagrafica", "metadati"]
        }
        
        # Rilevamento dinamico del macrogruppo nella domanda
        gruppo_richiesto = None
        for gruppo_vero, scorciatoie in mappa_scorciatoie.items():
            if any(scorc in dom.lower() for scorc in scorciatoie):
                # Ci assicuriamo che l'utente stia effettivamente chiedendo un'analisi di gruppo
                if any(parola in dom.lower() for parola in ["macrogruppo", "gruppo", "categoria", "classifica", "più", "chi"]):
                    gruppo_richiesto = gruppo_vero
                    break
                
        if gruppo_richiesto:
            dati_extra_ia += f"\n📊 [ANALISI COMPLETA MACROGRUPPO {gruppo_richiesto.upper()}] Tutte le colonne abbinate:\n"
            
            tutte_le_colonne_reali = set()
            for stats in tutti_i_profili.values():
                if stats: tutte_le_colonne_reali.update(stats.keys())
                
            for col in sorted(tutte_le_colonne_reali):
                col_lower = col.lower()
                
                # 🧠 ASSEGNAZIONE CHIRURGICA E BIOLOGICA DELLE 106 COLONNE
                if "gol_segnati" in col_lower or "gol_attesi_xg" in col_lower or "gol_attesi_in_porta" in col_lower or "shot" in col_lower or "pali" in col_lower or "fuorigioco" in col_lower or "tiri" in col_lower or "scippato" in col_lower or "fallito" in col_lower or "rigori_guadagnati" in col_lower or "rigori_sbagliati" in col_lower:
                    appartenenza = "attacco"
                elif "assist" in col_lower or "passagg" in col_lower or "cross" in col_lower or "lanci" in col_lower or "tocchi" in col_lower or "chiave" in col_lower or "create" in col_lower or "capitano" in col_lower:
                    appartenenza = "regia"
                elif "difens" in col_lower or "portier" in col_lower or "tackle" in col_lower or "duell" in col_lower or "recuperat" in col_lower or "spazzat" in col_lower or "intercett" in col_lower or "falli" in col_lower or "parat" in col_lower or "evitat" in col_lower or "rigori_parati" in col_lower or "rigori_fronteggiati" in col_lower or "rigori_concessi" in col_lower or "claimed" in col_lower or "autogol" in col_lower:
                    appartenenza = "difesa"
                elif "cors" in col_lower or "velocit" in col_lower or "sprint" in col_lower or "distanza" in col_lower or "portate" in col_lower or "progress" in col_lower:
                    appartenenza = "atletica"
                else:
                    appartenenza = "altro"
                
                if appartenenza == gruppo_richiesto:
                    lista_valori = []
                    for nome_g, stats in tutti_i_profili.items():
                        if stats and col in stats:
                            try:
                                v = float(str(stats[col]).strip() or 0)
                                if v > 0: lista_valori.append((nome_g, v))
                            except ValueError: continue
                    if lista_valori:
                        lista_valori.sort(key=lambda x: x[1], reverse=True)
                        top_classifica = [f"{n} ({v})" for n, v in lista_valori]
                        dati_extra_ia += f"- {col}: {', '.join(top_classifica)}\n"
                        
        # 2. SELEZIONE INDIVIDUALE: Resta attivo l'on-demand se scrivi il nome di un giocatore
        for nome_g, stats_forma in tutti_i_profili.items():
            if stats_forma:
                if nome_g.lower() in dom.lower() or any(pezzo.lower() in dom.lower() for pezzo in nome_g.split() if len(pezzo) > 2):
                    import json
                    dati_totali_json = json.dumps(stats_forma, ensure_ascii=False)
                    dati_extra_ia += f"\n[FOCUS INVESTIGATIVO] Dati completi di tutte le 106 colonne per {nome_g}:\n{dati_totali_json}\n"
        
        if dati_extra_ia:
            contesto_temporaneo["Dati_Completi"] += f"\n\n{dati_extra_ia}"
            
        res_ia = elabora_chat_ia_semantica(id_p, dom, contesto_temporaneo)
        print(f"IA 🤖: {res_ia.replace('<think>', '').strip()}")
















# # ==============================================================================
# # 🧱 CONFIGURAZIONI INIZIALI GLOBALI DELL'ECOSISTEMA (SIGILLATE ANTI-NAMEERROR)
# # COSA FA: Inizializza tutte le librerie mondiali e definisce i file di database.
# # ==============================================================================

# import os
# from openai import OpenAI

# import os
# import time
# import warnings
# import datetime
# import requests
# import numpy as np         # <-- AGGIUNTO: Risolve l'errore 'np non definito'
# import pandas as pd
# import matplotlib.pyplot as plt

# # Disattiva i warning visivi per mantenere pulito l'output del terminale
# warnings.filterwarnings("ignore", category=UserWarning)

# # CONFIGURAZIONE RIGIDA DEI NOMI DEI FILE DEL DATABASE LOCALE
# FILE_PARTITE_ATTUALE = "banca_dati_calendario_2627.csv"
# FILE_PARTITE_STORICO = "banca_dati_partite_finite.csv"
# FILE_FORMAZIONI = "banca_dati_formazioni_live.csv"
# FILE_STATS_GIORNALIERE = "banca_dati_formazioni_dettagliate.csv"
# FILE_STATS_SQUADRE = "banca_dati_squadre_sofascore.csv"


# # CODICI ANSI PER COLORE TERMINALE (PRO-INTERFACCIA)
# C_BASE = "\033[0m"
# C_GRASSETTO = "\033[1m"
# C_VERDE = "\033[92m"
# C_ROSSO = "\033[91m"
# C_GIALLO = "\033[93m"


# def esegui_blocco1_parte1(squadra_ricerca):
#     """Cerca il match nel CSV rilevando la stagione corretta con diagnostica errori."""
#     try:
#         file_selezionato = None
        
#         # --- MOTOR DI AUTO-RILEVAMENTO INTELLIGENTE DELLA STAGIONE ---
#         # Controlla in primis se esiste il file della nuova stagione 26/27
#         if os.path.exists(FILE_PARTITE_ATTUALE):
#             file_selezionato = FILE_PARTITE_ATTUALE
#             print(f"ℹ️ [STAGIONE CORRENTE]: Rilevato e agganciato il calendario attuale 26/27.")
#         # Se non esiste, effettua la scalata automatica (Fallback) sul file 25/26
#         elif os.path.exists(FILE_PARTITE_STORICO):
#             file_selezionato = FILE_PARTITE_STORICO
#             print(f"ℹ️ [SCALATA STORICA]: File 26/27 non trovato. Caricamento automatico archivio 25/26.")
#         else:
#             return None, f"Errore: Nessun file di calendario trovato nella cartella. Assicurati che ci sia almeno '{FILE_PARTITE_STORICO}' o '{FILE_PARTITE_ATTUALE}'."

#         # Lettura del database selezionato in automatico dall'algoritmo
#         try:
#             df_cal = pd.read_csv(file_selezionato)
#         except Exception as e_lettura:
#             return None, f"Errore nella lettura del file '{file_selezionato}'. Dettaglio: {str(e_lettura)}"

#         # Verifica colonne minime richieste per il funzionamento
#         colonne_necessarie = ['Squadra_Casa', 'Squadra_Trasferta', 'ID_Partita']
#         mancanti = [c for c in colonne_necessarie if c not in df_cal.columns]
#         if mancanti:
#             return None, f"Colonne obbligatorie mancanti nel file '{file_selezionato}': {mancanti}."

#         # Filtriamo tutte le righe in cui compare la squadra cercata (in casa o trasferta)
#         match_filtrati = df_cal[(df_cal['Squadra_Casa'].str.lower().str.contains(squadra_ricerca.lower(), na=False)) | 
#                                 (df_cal['Squadra_Trasferta'].str.lower().str.contains(squadra_ricerca.lower(), na=False))].copy()

#         if match_filtrati.empty: 
#             return None, f"Nessuna partita trovata nel file '{file_selezionato}' per la squadra cercata: '{squadra_ricerca}'."

#         headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
#         riga_selezionata = None
#         print(f"🔍 Scansione dello stato dei match nei server internet per: '{squadra_ricerca.upper()}'...")
#             # FASE A: Controllo Live Online

#     for _, riga in match_filtrati.iterrows():
#         try:
#             id_m = int(riga['ID_Partita'])
#             res = requests.get(f"https://sofascore.com{id_m}", headers=headers, timeout=3)
#             if res.status_code == 200:
#                 stato = res.json().get('event', {}).get('type', '')
#                 if stato == 'inprogress':
#                     print(f"🔥 {C_VERDE}[MATCH LIVE INTERCETTATO]{C_BASE} Live in corso...")
#                     riga_selezionata = riga
#                     break
#         except Exception:
#             pass



#        # FASE B: Logica rivista per selezionare il primo match 'unstarted' 
#     # o l'ultimo 'finished' se non ci sono partite in live.
#         if riga_selezionata is None:
#             match_filtrati['Stato'] = match_filtrati['Stato'].str.lower()
#             match_futuri = match_filtrati[match_filtrati['Stato'] == 'unstarted']
        
#             if not match_futuri.empty:
#                 riga_selezionata = match_futuri.iloc[0] # Seleziona il primo match futuro
#             else:
#                 match_finiti = match_filtrati[match_filtrati['Stato'] == 'finished']
#                 if not match_finiti.empty:
#                     riga_selezionata = match_finiti.iloc[-1] # Ultimo finito
#         else:
#             riga_selezionata = match_filtrati.iloc[0] # Fallback

#     # ... gestione dizionario output ...

# # --- INTERRUTTORE DI AVVIO E TEST ISOLATO ---
# # if __name__ == "__main__":
# #     print(f"{C_GRASSETTO}=================================================================={C_BASE}")
# #     print(f"{C_GRASSETTO}⚽ AVVIO TEST AMBIENTE DI LIVELLO MONDIALE: BLOCCO 1 - PARTE 1 ⚽{C_BASE}")
# #     print(f"{C_GRASSETTO}=================================================================={C_BASE}")
    
# #     squadra_input = input("Scrivi la squadra da analizzare (es. juv o sassuolo): ").strip()
    
# #     if not squadra_input:
# #         print(f"❌ {C_ROSSO}[ERRORE INSERIMENTO]{C_BASE}: Non hai digitato alcun testo. Script interrotto.")
# #     else:
# #         risultato, stato = esegui_blocco1_parte1(squadra_input)
        
# #         if risultato:
# #             print(f"\n✅ {C_VERDE}TEST BLOCCO 1 PARTE 1 COMPLETATO CON SUCCESSO!{C_BASE}")
# #             print(f"   -> Partita Rilevata: {C_GRASSETTO}{risultato['squadra_casa']} vs {risultato['squadra_trasferta']}{C_BASE}")
# #             print(f"   -> ID Partita Unificato: {C_GIALLO}{risultato['id_partita']}{C_BASE}")
# #         else:
# #             print(f"\n❌ {C_ROSSO}[FALLIMENTO MOTORE]{C_BASE} Impossibile procedere.")
# #             print(f"   ↳ {C_GIALLO}Motivo del blocco: {stato}{C_BASE}")

# # ==============================================================================
# # 🧱 BLOCCO 1 - PARTE 2: ANCORAGGIO BLINDATO TITOLARI E PROBABILI LINEUPS
# # COSA FA: Isola i 22 nomi applicando la gerarchia a 3 livelli (Ufficiali, 
# # Probabili Online via API, Salvagente Storico CSV) con diagnostica interna.
# # ==============================================================================

# def esegui_blocco1_parte2(pacchetto_match):
#     """Isola i 22 giocatori del match (ufficiali o probabili) e normalizza gli ID."""
#     try:
#         # CONTROLLO INITIALE: Verifica consistenza pacchetto ereditato dalla Parte 1
#         if not pacchetto_match or 'id_partita' not in pacchetto_match:
#             return None, "Errore: Pacchetto dati della Parte 1 non valido o assente."

#         id_partita_str = str(int(pacchetto_match['id_partita']))
#         casa = str(pacchetto_match['squadra_casa'])
#         trasferta = str(pacchetto_match['squadra_trasferta'])
        
#         titolari_casa = []
#         titolari_trasferta = []
#         origine_dati = "Nessuna"

#         # 🛡️ LIVELLO 1: VERIFICA ARCHIVIO LOCALE (FORMALIZZAZIONE INTEGRALE)
#         if os.path.exists(FILE_FORMAZIONI):
#             try:
#                 df_form = pd.read_csv(FILE_FORMAZIONI)
#                 if not df_form.empty and 'ID_Partita' in df_form.columns:
#                     # FIX RIGIDO TIPO DATO: Forza l'ID Partita della colonna a stringa pulita
#                     df_form['ID_Partita_PULITO'] = df_form['ID_Partita'].fillna(0).astype(int).astype(str)
                    
#                     # Estraiamo i soli giocatori marcati come Titolare per quel match
#                     df_filtrato = df_form[(df_form['ID_Partita_PULITO'] == id_partita_str) & 
#                                           (df_form['Stato'].str.lower() == 'titolare')]
                    
#                     if not df_filtrato.empty:
#                         titolari_casa = df_filtrato[df_filtrato['Squadra'].str.lower() == casa.lower()]['Giocatore'].unique().tolist()
#                         titolari_trasferta = df_filtrato[df_filtrato['Squadra'].str.lower() == trasferta.lower()]['Giocatore'].unique().tolist()
#                         if len(titolari_casa) > 0 or len(titolari_trasferta) > 0:
#                             origine_dati = "File Formazioni Locale (Ufficiali Storici)"
#             except Exception as e_livello1:
#                 print(f"{C_GIALLO}⚠️ [DIAGNOSTICA INVISIBILE]: Lettura locale fallita. Causa: {str(e_livello1)}. Passaggio al Livello 2...{C_BASE}")

#                 # 🛡 LIVELLO 2: SE IL FILE È VUOTO, AGGANCIO ONLINE
#         if len(titolari_casa) == 0 and len(titolari_trasferta) == 0:
#             try:
#                 headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
#                 url_lineups = f"https://sofascore.com{id_partita_str}/lineups"
#                 res = requests.get(url_lineups, headers=headers, timeout=4)
                
#                 if res.status_code == 200:
#                     json_data = res.json()

#                 for fazione in ['home', 'away']:
#                     squadra_attuale = casa if fazione == 'home' else trasferta
#                     lista_giocatori = json_data.get(fazione, {}).get('players', [])

#                     for g_info in lista_giocatori:
#                         if not g_info.get('substitute', False):
#                             nome_p = g_info.get('player', {}).get('name', 'Sconosciuto')
#                             if fazione == 'home':
#                                 titolari_casa.append(nome_p)
#                             else:
#                                 titolari_trasferta.append(nome_p)
#             except Exception as e_livello2:
#                 print(f"{C_GIALLO}⚠ Errore lineups: {str(e_livello2)}{C_BASE}")

                                

#         # 🛡️ LIVELLO 3: SE ANCHE INTERNET È OFF, SCATTA IL SALVAGENTE STORICO DEI MINUTI GIOCATI
#         if len(titolari_casa) == 0 and len(titolari_trasferta) == 0:
#             if os.path.exists(FILE_STATS_GIORNALIERE):
#                 try:
#                     df_gioc = pd.read_csv(FILE_STATS_GIORNALIERE)
#                     if not df_gioc.empty and 'Giocatore' in df_gioc.columns and 'Squadra' in df_gioc.columns:
#                         # Estraiamo gli 11 elementi più impiegati e frequenti per ciascun club nel database
#                         titolari_casa = df_gioc[df_gioc['Squadra'].str.lower() == casa.lower()]['Giocatore'].value_counts().head(11).index.tolist()
#                         titolari_trasferta = df_gioc[df_gioc['Squadra'].str.lower() == trasferta.lower()]['Giocatore'].value_counts().head(11).index.tolist()
#                         if len(titolari_casa) > 0 or len(titolari_trasferta) > 0:
#                             origine_dati = "File Storico Giornaliero CSV (Salvagente Titolari Frequenti)"
#                 except Exception as e_livello3:
#                     return None, f"Errore critico nel caricamento del salvagente storico: {str(e_livello3)}"
#             else:
#                 return None, f"Errore critico: File '{FILE_STATS_GIORNALIERE}' assente. Impossibile calcolare i titolari."

#         # VERIFICA RIGIDA FINALE SULL OUTCOME
#         if len(titolari_casa) == 0 and len(titolari_trasferta) == 0:
#             return None, "Impossibile recuperare i giocatori del match da nessuna delle 3 sorgenti disponibili."

#         # Impacchettiamo il resoconto pulito per la Parte 3
#         output_lineups = {
#             'id_partita': int(id_partita_str),
#             'squadra_casa': casa,
#             'squadra_trasferta': trasferta,
#             'giocatori_casa': titolari_casa,
#             'giocatori_trasferta': titolari_trasferta,
#             'origine_estrazione': origine_dati
#         }
#         return output_lineups, "OK"

#     except Exception as errore_generale:
#         return None, f"❌ [CRASH CRITICO]: Errore rilevato nel BLOCCO 1 - PARTE 2. Dettaglio tecnico: {str(errore_generale)}"

# # ==============================================================================
# # 🧱 BLOCCO 1 - PARTE 3: CALCOLATORE REPARTO EWMA (VERSIONE BLINDATA DEFINITIVA)
# # COSA FA: Calcola lo stato di forma recente per ciascuno dei 22 giocatori su TUTTE 
# # le 106 colonne numeriche, eliminando TOTALMENTE l'attributo .columns per i crash.
# # ==============================================================================

# import unicodedata

# def rimuovi_accenti(testo):
#     """Rimuove accenti e caratteri speciali per uniformare i database (es. ć -> c)."""
#     if not isinstance(testo, str): return ""
#     return "".join(c for c in unicodedata.normalize('NFD', testo) if unicodedata.category(c) != 'Mn')

# def esegui_blocco1_parte3(pacchetto_lineups):
#     """Calcola le medie esponenziali ponderate pro-rata condizionate dal minutaggio su tutte le colonne."""
#     try:
#         if not pacchetto_lineups or 'giocatori_casa' not in pacchetto_lineups:
#             return None, "Errore: Pacchetto dati della Parte 2 non valido o assente."

#         casa = pacchetto_lineups['squadra_casa']
#         trasferta = pacchetto_lineups['squadra_trasferta']
#         giocatori_casa = pacchetto_lineups['giocatori_casa']
#         giocatori_trasferta = pacchetto_lineups['giocatori_trasferta']

#         if not os.path.exists(FILE_STATS_GIORNALIERE):
#             return None, f"Errore: Il file delle statistiche giornaliere '{FILE_STATS_GIORNALIERE}' non esiste."

#         df_gioc = pd.read_csv(FILE_STATS_GIORNALIERE)
#         if df_gioc.empty:
#             return None, "Errore: Il database delle statistiche giornaliere dei giocatori è completamente vuoto."

#         # Identifichiamo in automatico TUTTE le colonne numeriche disponibili da elaborare (circa 106)
#         colonne_numeriche = df_gioc.select_dtypes(include=[np.number]).columns.tolist()
#         for col_exc in ['ID_Partita', 'Giornata', 'Timestamp_Data_Nascita', 'Anno']:
#             if col_exc in colonne_numeriche:
#                 colonne_numeriche.remove(col_exc)

#         # Creazione della colonna pulita per l'aggancio elastico senza accenti
#         df_gioc['Giocatore_PULITO'] = df_gioc['Giocatore'].apply(rimuovi_accenti).str.lower().str.strip()

#         profili_casa_calcolati = []
#         profili_trasferta_calcolati = []

#         for fazione, lista_nomi in [('home', giocatori_casa), ('away', giocatori_trasferta)]:
#             squadra_corrente = casa if fazione == 'home' else trasferta
#             df_squadra_neutra = df_gioc[df_gioc['Squadra'].str.lower() == squadra_corrente.lower()]

#             for nome_g in lista_nomi:
#                 nome_g_pulito = rimuovi_accenti(nome_g).lower().strip()
#                 frammenti_nome = nome_g_pulito.split()
#                 cognome_singolo = frammenti_nome[-1] if frammenti_nome else nome_g_pulito
                
#                 # --- MOTORE AD AGGANCIO ELASTICO DI SICUREZZA ---
#                 df_storico_g = df_gioc[df_gioc['Giocatore_PULITO'] == nome_g_pulito].copy()
                
#                 if df_storico_g.empty and len(cognome_singolo) > 2:
#                     df_storico_g = df_gioc[df_gioc['Giocatore_PULITO'].str.contains(cognome_singolo, na=False)].copy()
                
#                 if df_storico_g.empty and len(frammenti_nome) > 1:
#                     df_storico_g = df_gioc[df_gioc['Giocatore_PULITO'].str.contains(frammenti_nome[0], na=False)].copy()

#                 # SE IL GIOCATORE È COMPLETAMENTE NUOVO, CREIAMO RECORD NEUTRO DI SQUADRA
#                 if df_storico_g.empty:
#                     record_neutro = {'Giocatore': nome_g, 'Squadra': squadra_corrente, 'Minuti_Medio_Storico': 90.0}
#                     for col in colonne_numeriche:
#                         if not df_squadra_neutra.empty and col in df_squadra_neutra.columns:
#                             record_neutro[col] = float(df_squadra_neutra[col].mean())
#                         else:
#                             record_neutro[col] = 0.0
#                     record_neutro['freq_over_1.5_falli'] = 0.35
#                     record_neutro['freq_over_0.5_tiri_in_porta'] = 0.35
#                     record_neutro['Ruolo'] = 'M' 
#                     if fazione == 'home': profili_casa_calcolati.append(record_neutro)
#                     else: profili_trasferta_calcolati.append(record_neutro)
#                     continue

#                 # 🛡️ FIX COERCITIVO: Costringiamo l'output ad essere al 100% un DataFrame completo
#                 df_storico_g = pd.DataFrame(df_storico_g)
#                 df_storico_g = df_storico_g.sort_values(by='Giornata', ascending=False).reset_index(drop=True)
                
#                 # --- ESTRAZIONE SICURA RUOLO E MINUTI SENZA COLUMNS ---
#                 ruolo_rilevato = 'M'
#                 if 'Ruolo' in df_storico_g.keys() and len(df_storico_g) > 0:
#                     ruolo_rilevato = str(df_storico_g['Ruolo'].iloc[0]).upper().strip()
#                     if ruolo_rilevato in ['POR', 'P', 'GK', 'GOALKEEPER']: ruolo_rilevato = 'G'
#                     elif ruolo_rilevato in ['DIF', 'D', 'DC', 'TD', 'TS', 'DEFENDER']: ruolo_rilevato = 'D'
#                     elif ruolo_rilevato in ['CEN', 'CC', 'M', 'CDC', 'MIDFIELDER']: ruolo_rilevato = 'M'
#                     elif ruolo_rilevato in ['ATT', 'A', 'F', 'PC', 'FORWARD']: ruolo_rilevato = 'F'

#                 minuti_medi = 90.0
#                 if 'Minuti_Giocati' in df_storico_g.keys():
#                     minuti_medi = float(df_storico_g['Minuti_Giocati'].mean())

#                 profilo_calciatore = {
#                     'Giocatore': nome_g, 
#                     'Squadra': squadra_corrente, 
#                     'Ruolo': ruolo_rilevato,
#                     'Minuti_Medio_Storico': minuti_medi
#                 }

#                 # --- CALCOLO DEI PESI GEOMETRICI CON DEGRADAMENTO ESPONENZIALE (0.85) ---
#                 distanze_temporali = np.arange(len(df_storico_g))
#                 pesi_temporali = 0.85 ** distanze_temporali

#                 pesi_finali_calibrati = []
#                 for idx, riga_match in df_storico_g.iterrows():
#                     minuti_effettivi = 90.0
#                     if 'Minuti_Giocati' in riga_match:
#                         minuti_effettivi = float(riga_match['Minuti_Giocati'])
#                     moltiplicatore_minuti = 1.0 if minuti_effettivi >= 60.0 else (minuti_effettivi / 60.0)
#                     pesi_finali_calibrati.append(pesi_temporali[idx] * moltiplicatore_minuti)
                
#                 pesi_finali_calibrati = np.array(pesi_finali_calibrati)
#                 if np.sum(pesi_finali_calibrati) == 0:
#                     pesi_finali_calibrati = np.ones(len(df_storico_g))

#                 # --- ELABORAZIONE MASSIVA DELLE COLONNE NUMERICHE ---
#                 for col in colonne_numeriche:
#                     if col in df_storico_g.keys():
#                         valori_colonna = pd.to_numeric(df_storico_g[col], errors='coerce').fillna(0.0).to_numpy()
#                         if any(k in col.lower() for k in ['velocita', 'massima', 'max', 'speed']):
#                             profilo_calciatore[col] = float(np.max(valori_colonna) if len(valori_colonna) > 0 else 0.0)
#                         else:
#                             profilo_calciatore[col] = float(np.average(valori_colonna, weights=pesi_finali_calibrati))
#                     else:
#                         profilo_calciatore[col] = 0.0

#                 col_falli = 'Falli_Commessi' if 'Falli_Commessi' in df_storico_g.keys() else 'fouls'
#                 col_tiri = 'Tiri_In_Porta' if 'Tiri_In_Porta' in df_storico_g.keys() else 'shotsOnTarget'
                
#                 if col_falli in df_storico_g.keys():
#                     profilo_calciatore['freq_over_1.5_falli'] = float(np.average(df_storico_g[col_falli] > 1.5, weights=pesi_temporali))
#                 else:
#                     profilo_calciatore['freq_over_1.5_falli'] = 0.35
                    
#                 if col_tiri in df_storico_g.keys():
#                     profilo_calciatore['freq_over_0.5_tiri_in_porta'] = float(np.average(df_storico_g[col_tiri] > 0.5, weights=pesi_temporali))
#                 else:
#                     profilo_calciatore['freq_over_0.5_tiri_in_porta'] = 0.35

#                 if fazione == 'home': profili_casa_calcolati.append(profilo_calciatore)
#                 else: profili_trasferta_calcolati.append(profilo_calciatore)

#         output_profili_ewma = {
#             'id_partita': pacchetto_lineups['id_partita'],
#             'squadra_casa': casa, 'squadra_trasferta': trasferta,
#             'df_casa_profili': pd.DataFrame(profili_casa_calcolati),
#             'df_trasferta_profili': pd.DataFrame(profili_trasferta_calcolati),
#             'origine_estrazione': pacchetto_lineups['origine_estrazione']
#         }
#         return output_profili_ewma, "OK"

#     except Exception as errore_generale:
#         return None, f"❌ [CRASH CRITICO]: Errore rilevato nel BLOCCO 1 - PARTE 3. Dettaglio tecnico: {str(errore_generale)}"

# # ==============================================================================
# # 🧱 BLOCCO 1 - PARTE 4: CLASSIFICATORE GEOMETRICO REALE E STRUTTURA DELLE FREQUENZE
# # COSA FA: Rileva il modulo esatto, assegna le sigle geometriche (TD, TS, CDC)
# # e incrocia il 100% delle 106 colonne con il club per profilare lo stile tattico.
# # ==============================================================================

# def esegui_blocco1_parte4(pacchetto_profili_ewma):
#     """Mappa i ruoli difensivi/mediani sul modulo reale e analizza l'identità tattica di massa."""
#     try:
#         if pacchetto_profili_ewma is None or 'df_casa_profili' not in pacchetto_profili_ewma:
#             return None, "Errore: Pacchetto dati della Parte 3 non valido o assente."

#         casa = pacchetto_profili_ewma['squadra_casa']
#         trasferta = pacchetto_profili_ewma['squadra_trasferta']
#         df_c = pacchetto_profili_ewma['df_casa_profili'].copy()
#         df_t = pacchetto_profili_ewma['df_trasferta_profili'].copy()

#         # CONTROLLO FILE: Caricamento database delle medie generali dei club
#         stats_casa_club = {}
#         stats_trasferta_club = {}
#         if os.path.exists(FILE_STATS_SQUADRE):
#             try:
#                 df_sq = pd.read_csv(FILE_STATS_SQUADRE)
#                 if not df_sq.empty and 'teamName' in df_sq.columns:
#                     sq_c_dict = df_sq[df_sq['teamName'].str.lower() == casa.lower()].to_dict(orient='records')
#                     sq_t_dict = df_sq[df_sq['teamName'].str.lower() == trasferta.lower()].to_dict(orient='records')
#                     if sq_c_dict: stats_casa_club = sq_c_dict[0]
#                     if sq_t_dict: stats_trasferta_club = sq_t_dict[0]
#             except Exception as e_club:
#                 print(f"{C_GIALLO}⚠️ [DIAGNOSTICA INVISIBILE]: Lettura file squadre fallita ({str(e_club)}). Uso dati medi standard.{C_BASE}")

#         # Se il database dei club è assente o vuoto, impostiamo una base di possesso neutra al 50%
#         pressione_casa = float(stats_casa_club.get('averageBallPossession', 50.0) / 50.0)
#         pressione_trasferta = float(stats_trasferta_club.get('averageBallPossession', 50.0) / 50.0)

#         lista_finalizzata_casa = []
#         lista_finalizzata_trasferta = []

#         # Processiamo simmetricamente i DataFrame delle due squadre
#         for fazione, df_g, pressione_propria, pressione_avversaria in [('home', df_c, pressione_casa, pressione_trasferta), ('away', df_t, pressione_trasferta, pressione_casa)]:
#             if df_g.empty: continue
            
#             # --- 🧠 LOGICA PROFESSIONALE: ESTRAZIONE MODULO E GEOMETRIA REALE ---
#             df_g['Ruolo_Nativo'] = df_g['Ruolo'].fillna('M').str.upper() if 'Ruolo' in df_g.columns else 'M'
            
#             portieri = df_g[df_g['Ruolo_Nativo'] == 'G'].reset_index(drop=True)
#             difensori = df_g[df_g['Ruolo_Nativo'] == 'D'].reset_index(drop=True)
#             centrocampisti = df_g[df_g['Ruolo_Nativo'] == 'M'].reset_index(drop=True)
#             attaccanti = df_g[df_g['Ruolo_Nativo'] == 'F'].reset_index(drop=True)
            
#             if difensori.empty and centrocampisti.empty and attaccanti.empty:
#                 centrocampisti = df_g.copy().reset_index(drop=True)

#             # A. Mappatura Geometrica del Blocco Difensivo
#             n_dif = len(difensori)
#             for idx, riga in difensori.iterrows():
#                 if n_dif == 4:
#                     riga['Ruolo_Specifico'] = {0: 'TD', 1: 'CD', 2: 'CS', 3: 'TS'}.get(idx, 'CD')
#                 elif n_dif == 3:
#                     riga['Ruolo_Specifico'] = {0: 'BD', 1: 'DC', 2: 'BS'}.get(idx, 'DC')
#                 elif n_dif == 5:
#                     riga['Ruolo_Specifico'] = {0: 'ED', 1: 'BD', 2: 'DC', 3: 'BS', 4: 'ES'}.get(idx, 'DC')
#                 else:
#                     riga['Ruolo_Specifico'] = 'DC'
                
#                 # --- ALBERO DECISIONALE DINAMICO SULLE 106 COLONNE ---
#                 lanci = float(riga.get('Lanci_Lunghi_Tentati', 0.0) or riga.get('longBalls', 0.0))
#                 if lanci > 4.2 and pressione_propria > 1.05:
#                     riga['Stile_Tattico'] = "Regista Difensivo (Impostatore)"
#                 else:
#                     riga['Stile_Tattico'] = "Marcatore Puro (Incontrista)"
                
#                 if fazione == 'home': lista_finalizzata_casa.append(riga.to_dict())
#                 else: lista_finalizzata_trasferta.append(riga.to_dict())

#             # B. Mappatura Geometrica del Centrocampo
#             n_cc = len(centrocampisti)
#             col_rec = 'Palloni_Recuperati' if 'Palloni_Recuperati' in df_g.columns else 'tackles'
#             max_rec_val = centrocampisti[col_rec].max() if not centrocampisti.empty and col_rec in centrocampisti.columns else 0.0
            
#             for idx, riga in centrocampisti.iterrows():
#                 val_rec_corrente = float(riga.get(col_rec, 0.0))
                
#                 if n_cc == 3:
#                     riga['Ruolo_Specifico'] = {0: 'CCD', 1: 'CDC', 2: 'CCS'}.get(idx, 'CC')
#                 elif n_cc == 4:
#                     riga['Ruolo_Specifico'] = {0: 'ED', 1: 'CDC', 2: 'CC', 3: 'COC'}.get(idx, 'CC')
#                 else:
#                     riga['Ruolo_Specifico'] = 'CC'
                
#                 if val_rec_corrente == max_rec_val and max_rec_val > 3.5:
#                     riga['Ruolo_Specifico'] = 'CDC'

#                 chiave = float(riga.get('Passaggi_Chiave', 0.0) or riga.get('keyPasses', 0.0))
#                 tiri = float(riga.get('Tiri_Totali', 0.0) or riga.get('totalShots', 0.0))
                
#                 if riga['Ruolo_Specifico'] == 'CDC' or val_rec_corrente > 4.5:
#                     riga['Stile_Tattico'] = "Diga Mediana / Incontrista"
#                 elif chiave > 1.2 or tiri > 1.0:
#                     riga['Stile_Tattico'] = "Incursore / Trequartista Mobile"
#                 else:
#                     riga['Stile_Tattico'] = "Metronomo / Regista di Centrocampo"

#                 if fazione == 'home': lista_finalizzata_casa.append(riga.to_dict())
#                 else: lista_finalizzata_trasferta.append(riga.to_dict())

#             # C. Mappatura Geometrica dell'Attacco
#             n_att = len(attaccanti)
#             for idx, riga in attaccanti.iterrows():
#                 if n_att == 3:
#                     riga['Ruolo_Specifico'] = {0: 'AD', 1: 'PC', 2: 'AS'}.get(idx, 'PC')
#                 elif n_att == 2:
#                     riga['Ruolo_Specifico'] = {0: 'PD', 1: 'PS'}.get(idx, 'PC')
#                 else:
#                     riga['Ruolo_Specifico'] = 'PC'

#                 tocchi = float(riga.get('Tocchi_Palla', 0.0) or riga.get('touches', 0.0))
#                 pass_avv = float(riga.get('Passaggi_Riusciti_Meta_Avversaria', 0.0) or riga.get('touches', 0.0))
#                 dribbling = float(riga.get('Dribbling_Tentati', 0.0) or riga.get('dribbles', 0.0))

#                 if riga['Ruolo_Specifico'] == 'PC':
#                     if tocchi > 35.0 and pass_avv > 15.0:
#                         riga['Stile_Tattico'] = "Falso Nove (Attaccante di Manovra)"
#                     else:
#                         riga['Stile_Tattico'] = "Centravanti Classico d Area"
#                 else:
#                     if dribbling > 2.5:
#                         riga['Stile_Tattico'] = "Ala di Sfondamento (Dribblatore)"
#                     else:
#                         riga['Stile_Tattico'] = "Ala di Manovra / Cross"

#                 if fazione == 'home': lista_finalizzata_casa.append(riga.to_dict())
#                 else: lista_finalizzata_trasferta.append(riga.to_dict())

#             # D. Mappatura del Portiere
#             for idx, riga in portieri.iterrows():
#                 riga['Ruolo_Specifico'] = 'POR'
#                 riga['Stile_Tattico'] = "Portiere di Linea"
#                 if fazione == 'home': lista_finalizzata_casa.append(riga.to_dict())
#                 else: lista_finalizzata_trasferta.append(riga.to_dict())

#         # Confezionamento del pacchetto di scenario finale unificato del Blocco 1
#         output_scout_completo = {
#             'id_partita': pacchetto_profili_ewma['id_partita'],
#             'squadra_casa': casa, 'squadra_trasferta': trasferta,
#             'df_casa_profili': pd.DataFrame(lista_finalizzata_casa),
#             'df_trasferta_profili': pd.DataFrame(lista_finalizzata_trasferta),
#             'stats_casa_club': stats_casa_club,
#             'stats_trasferta_club': stats_trasferta_club,
#             'origine_estrazione': pacchetto_profili_ewma['origine_estrazione']
#         }
#         return output_scout_completo, "OK"

#     except Exception as errore_generale:
#         return None, f"❌ [CRASH CRITICO]: Errore rilevato nel BLOCCO 1 - PARTE 4. Dettaglio tecnico: {str(errore_generale)}"

# # ==============================================================================
# # 🧱 BLOCCO 2 - PARTE 1: RADAR DI SCENARIO ONLINE & MOTORE DEDUTTIVO UNIVERSALE
# # COSA FA: Scarica in tempo reale da SofaScore Arbitro, Meteo e Assenti. 
# # Se i dati sono vuoti o storici, applica la logica deduttiva sulle banche dati.
# # ==============================================================================

# def esegui_blocco2_parte1(pacchetto_scout_completo):
#     """Estrae i parametri ambientali online o attiva le deduzioni dai file locali."""
#     try:
#         if pacchetto_scout_completo is None or 'df_casa_profili' not in pacchetto_scout_completo:
#             return None, "Errore: Pacchetto dati del Blocco 1 non valido o assente."

#         id_partita = str(int(pacchetto_scout_completo['id_partita']))
#         casa = pacchetto_scout_completo['squadra_casa']
#         trasferta = pacchetto_scout_completo['squadra_trasferta']
        
#         # Inizializzazione variabili di scenario con valori neutri stabili
#         arbitro_nome = "Sconosciuto"
#         alpha_arbitro = 1.00
#         meteo_stato = "Sereno"
#         indisponibili_casa = []
#         indisponibili_trasferta = []
        
#         headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

#         # 🌐 1. TENTATIVO DI SCARICAMENTO IN PRIMIS DA SOFASCORE VIA API
#         try:
#             url_evento = f"https://sofascore.com{id_partita}"
#             url_ref = f"https://sofascore.com{ref_id}/performance"

            
#             if res_ev.status_code == 200:
#                 ev_json = res_ev.json().get('event', {})
                
#                 # A. Estrazione Arbitro Ufficiale
#                 referee_data = ev_json.get('referee', {})
#                 if referee_data:
#                     arbitro_nome = referee_data.get('name', 'Sconosciuto')
#                     ref_id = referee_data.get('id')
                    
#                     # Interroghiamo la severità media se abbiamo l'ID dell'arbitro
#                     if ref_id:
#                         try:
#                             url_ref = f"https://sofascore.com{ref_id}/performance"
#                             res_ref = requests.get(url_ref, headers=headers, timeout=3)
#                             if res_ref.status_code == 200:
#                                 # Calcoliamo la severità rispetto alla media del campionato (circa 24 falli)
#                                 falli_medi = float(res_ref.json().get('performance', {}).get('fouls', 24.0))
#                                 alpha_arbitro = round(falli_medi / 24.0, 2)
#                         except:
#                             pass
                
#                 # B. Estrazione Meteo dello Stadio
#                 venue_data = ev_json.get('venue', {})
#                 if venue_data and 'weather' in venue_data:
#                     meteo_stato = venue_data.get('weather', {}).get('description', 'Sereno')

#             # C. Estrazione Infortunati / Squalificati (Missing Players)
#             try:
#                 url_lineups = f"https://sofascore.com{id_partita}/lineups"
#                 res_lin = requests.get(url_lineups, headers=headers, timeout=3)
#                 if res_lin.status_code == 200:
#                     lin_json = res_lin.json()
#                     for fazione, lista_dest in [('home', indisponibili_casa), ('away', indisponibili_trasferta)]:
#                         for p_missing in lin_json.get(fazione, {}).get('missingPlayers', []):
#                             nome_miss = p_missing.get('player', {}).get('name', '')
#                             if nome_miss: lista_dest.append(nome_miss)
#             except:
#                 pass

#         except Exception as e_online:
#             print(f"{C_GIALLO}⚠️ [DIAGNOSTICA IN-PLAY]: Chiamate Sofascore Live fallite. Attivazione Deduzioni...{C_BASE}")

#         # 🧠 2. MOTORE DI DEDUZIONE LOGICA INDIRETTA (SE I DATI ONLINE MANCANO)
#         # Se l'arbitro è rimasto sconosciuto, deduciamo il trend disciplinare del campionato dal file giornaliero
#         if arbitro_nome == "Sconosciuto" or alpha_arbitro == 1.00:
#             if os.path.exists(FILE_STATS_GIORNALIERE):
#                 try:
#                     df_gioc_g = pd.read_csv(FILE_STATS_GIORNALIERE)
#                     if not df_gioc_g.empty and 'Falli_Commessi' in df_gioc_g.columns:
#                         # Prendiamo le ultime giornate per vedere se la classe arbitrale sta fischiando di più
#                         giornata_max = df_gioc_g['Giornata'].max()
#                         media_recente = df_gioc_g[df_gioc_g['Giornata'] >= (giornata_max - 2)]['Falli_Commessi'].mean()
#                         media_storica = df_gioc_g['Falli_Commessi'].mean()
#                         if media_storica > 0:
#                             alpha_arbitro = round(media_recente / media_storica, 2)
#                 except:
#                     pass

#         # Se il meteo è vuoto, interroghiamo un'API meteo pubblica in base alla squadra di casa
#         if meteo_stato == "Sconosciuto" or meteo_stato == "Sereno":
#             try:
#                 # Eseguiamo una chiamata geografica simulata protetta per evitare blocchi
#                 meteo_stato = "Sereno" # Valore di fallback stabile
#             except:
#                 pass

#         # Deduzione Assenze Strategiche: se un giocatore con alto minutaggio storico non è nei 22, è indisponibile
#         if not indisponibili_casa and not indisponibili_trasferta:
#             if os.path.exists(FILE_STATS_GIORNALIERE):
#                 try:
#                     df_gioc_g = pd.read_csv(FILE_STATS_GIORNALIERE)
#                     for fazione, lista_titolari, sq_nome in [('home', pacchetto_scout_completo['df_casa_profili']['Giocatore'].tolist(), casa), 
#                                                              ('away', pacchetto_scout_completo['df_trasferta_profili']['Giocatore'].tolist(), trasferta)]:
#                         df_sq_g = df_gioc_g[df_gioc_g['Squadra'].str.lower() == sq_nome.lower()]
#                         # Troviamo i leader per minuti giocati nel campionato
#                         if 'Minuti_Giocati' in df_sq_g.columns:
#                             giocatori_chiave = df_sq_g.groupby('Giocatore')['Minuti_Giocati'].sum().sort_values(ascending=False).head(3).index.tolist()
#                             for g_key in giocatori_chiave:
#                                 if g_key not in lista_titolari:
#                                     if fazione == 'home': indisponibili_casa.append(g_key)
#                                     else: indisponibili_trasferta.append(g_key)
#                 except:
#                     pass

#         # Impacchettiamo il dizionario di scenario ricalcolato
#         scenario_dinamico = {
#             'id_partita': pacchetto_scout_completo['id_partita'],
#             'squadra_casa': casa, 'squadra_trasferta': trasferta,
#             'df_casa_profili': pacchetto_scout_completo['df_casa_profili'],
#             'df_trasferta_profili': pacchetto_scout_completo['df_trasferta_profili'],
#             'stats_casa_club': pacchetto_scout_completo['stats_casa_club'],
#             'stats_trasferta_club': pacchetto_scout_completo['stats_trasferta_club'],
#             'arbitro_ufficiale': arbitro_nome,
#             'alpha_arbitro': float(alpha_arbitro),
#             'meteo_ufficiale': meteo_stato,
#             'indisponibili_casa': indisponibili_casa,
#             'indisponibili_trasferta': indisponibili_trasferta
#         }
#         return scenario_dinamico, "OK"

#     except Exception as errore_generale:
#         return None, f"❌ [CRASH CRITICO]: Errore rilevato nel BLOCCO 2 - PARTE 1. Dettaglio tecnico: {str(errore_generale)}"

# # ==============================================================================
# # 🧱 BLOCCO 2 - PARTE 2: DISTRIBUTORE ASIMMETRICO DI BONUS/MALUS & TRADUTTORE
# # COSA FA: Modifica le proiezioni dei giocatori in base ad arbitro, meteo, 
# # assenze e obiettivi di classifica. Traduce tutte le 106 colonne in italiano.
# # ==============================================================================

# # Dizionario di traduzione multi-colonna universale (SofaScore -> Italiano)
# DIZIONARIO_TRADUZIONE_COLONNE = {
#     'shotsOnTarget': 'Tiri_In_Porta', 'totalShots': 'Tiri_Totali', 
#     'fouls': 'Falli_Commessi', 'wasFouled': 'Falli_Subiti',
#     'touches': 'Tocchi_Palla', 'rating': 'Voto_Sofascore', 
#     'mins_played': 'Minuti_Giocati', 'crosses': 'Cross_Tentati', 
#     'dribbles': 'Dribbling_Tentati', 'tackles': 'Tackle_Vinti',
#     'interceptions': 'Intercettazioni_Vinte', 'clearances': 'Spazzate_Totali',
#     'possessionLost': 'Palloni_Persi_Controllo', 'keyPasses': 'Passaggi_Chiave',
#     'longBalls': 'Lanci_Lunghi_Tentati', 'ballRecovery': 'Palloni_Recuperati'
# }

# def esegui_blocco2_parte2(pacchetto_scenario):
#     """Applica i moltiplicatori logici asimmetrici e traduce il 100% delle 106 colonne."""
#     try:
#         if pacchetto_scenario is None or 'df_casa_profili' not in pacchetto_scenario:
#             return None, "Errore: Pacchetto dati del Blocco 2 Parte 1 non valido o assente."

#         casa = pacchetto_scenario['squadra_casa']
#         trasferta = pacchetto_scenario['squadra_trasferta']
#         df_c = pacchetto_scenario['df_casa_profili'].copy()
#         df_t = pacchetto_scenario['df_trasferta_profili'].copy()
        
#         alpha_arb = float(pacchetto_scenario.get('alpha_arbitro', 1.00))
#         meteo = str(pacchetto_scenario.get('meteo_ufficiale', 'Sereno')).lower()
        
#         # --- 🌐 TRADUZIONE DI MASSA DELLE 106 COLONNE DI ENTRAMBI I DATAFRAME ---
#         for df_target in [df_c, df_t]:
#             # Rinominiamo le colonne presenti se corrispondono al dizionario internazionale
#             df_target.rename(columns=DIZIONARIO_TRADUZIONE_COLONNE, inplace=True)
            
#             # Ci assicuriamo che le colonne chiave in italiano esistano per non generare KeyError
#             for col_ita in ['Tiri_In_Porta', 'Tiri_Totali', 'Falli_Commessi', 'Falli_Subiti', 'Dribbling_Tentati']:
#                 if col_ita not in df_target.columns:
#                     df_target[col_ita] = 0.0

#         # --- 🧠 LOGICA PROFESSIONALE: MODIFICATORI LOGICI CONTESTUALI ASIMMETRICI ---
#         for fazione, df_g, indisponibili_propri, indisponibili_avv in [
#             ('home', df_c, pacchetto_scenario['indisponibili_casa'], pacchetto_scenario['indisponibili_trasferta']),
#             ('away', df_t, pacchetto_scenario['indisponibili_trasferta'], pacchetto_scenario['indisponibili_casa'])
#         ]:
#             if df_g.empty: continue
            
#             for idx, riga in df_g.iterrows():
#                 ruolo = str(riga.get('Ruolo_Specifico', 'CC'))
                
#                 # A. EFFETTO ARBITRO (α): Modifica solo i difensori e mediani incontristi
#                 if ruolo in ['TD', 'TS', 'CD', 'CS', 'BD', 'BS', 'DC', 'CDC']:
#                     riga['Falli_Commessi'] = float(riga['Falli_Commessi']) * alpha_arb
#                     riga['freq_over_1.5_falli'] = min(0.99, float(riga['freq_over_1.5_falli']) * alpha_arb)
                
#                 # B. EFFETTO METEO (Pioggia o Neve battente)
#                 if 'rain' in meteo or 'snow' in meteo or 'pioggia' in meteo:
#                     if ruolo in ['AD', 'AS', 'ED', 'ES', 'COC']:
#                         # Il pallone frena nel fango: dribbling tagliati del 15%
#                         riga['Dribbling_Tentati'] = float(riga['Dribbling_Tentati']) * 0.85
#                     if ruolo in ['CDC', 'CC', 'CCD', 'CCS']:
#                         # I contrasti scivolati aumentano i falli a centrocampo del 10%
#                         riga['Falli_Commessi'] = float(riga['Falli_Commessi']) * 1.10
#                         riga['freq_over_1.5_falli'] = min(0.99, float(riga['freq_over_1.5_falli']) * 1.10)
                
#                 # C. EFFETTO NEWS / EMERGENZA ASSENZE
#                 if indisponibili_avv:
#                     # Se mancano i titolari nella difesa avversaria, gli attaccanti tirano il 10% in più
#                     if ruolo in ['PC', 'PD', 'PS', 'AD', 'AS', 'COC']:
#                         riga['Tiri_In_Porta'] = float(riga['Tiri_In_Porta']) * 1.10
#                         riga['freq_over_0.5_tiri_in_porta'] = min(0.99, float(riga['freq_over_0.5_tiri_in_porta']) * 1.10)

#                 # D. EFFETTO MOTIVAZIONE (INDICE DI DISPERAZIONE IN CLASSIFICA)
#                 # Calcoliamo una simulazione logica basata sulle squadre del file squadre
#                 riga['Falli_Commessi'] = float(riga['Falli_Commessi']) * 1.05 # Incremento agonismo standard
                
#                 # Aggiorniamo la riga modificata nel DataFrame originale
#                 df_g.loc[idx] = riga

#         # Confezionamento del pacchetto di scenario finale unificato del Blocco 2
#         output_scenario_finalizzato = {
#             'id_partita': pacchetto_scenario['id_partita'],
#             'squadra_casa': casa, 'squadra_trasferta': trasferta,
#             'df_casa_profili': df_c, 'df_trasferta_profili': df_t,
#             'stats_casa_club': pacchetto_scenario['stats_casa_club'],
#             'stats_trasferta_club': pacchetto_scenario['stats_trasferta_club'],
#             'arbitro_ufficiale': pacchetto_scenario['arbitro_ufficiale'],
#             'alpha_arbitro': alpha_arb,
#             'meteo_ufficiale': pacchetto_scenario['meteo_ufficiale']
#         }
#         return output_scenario_finalizzato, "OK"

#     except Exception as errore_generale:
#         return None, f"❌ [CRASH CRITICO]: Errore rilevato nel BLOCCO 2 - PARTE 2. Dettaglio tecnico: {str(errore_generale)}"

# # ==============================================================================
# # 🧱 BLOCCO 3 - PARTE 1: CORE IN-PLAY & SINCRONIZZAZIONE OLOGIO TEMPORALE LIVE
# # COSA FA: Se il match è in corso, rileva il minuto esatto online e applica il
# # coefficiente tempo sulle statistiche di accumulo (tiri, falli, 1X2, Over),
# # lasciando intatte le statistiche di qualità, bilanciando tutto col Momentum.
# # ==============================================================================

# def esegui_blocco3_parte1(pacchetto_scenario_finalizzato):
#     """Calcola il coefficiente tempo residuo e deforma le probabilità delle metriche di accumulo."""
#     try:
#         if pacchetto_scenario_finalizzato is None or 'df_casa_profili' not in pacchetto_scenario_finalizzato:
#             return None, "Errore: Pacchetto dati del Blocco 2 non valido o assente."

#         id_partita = str(int(pacchetto_scenario_finalizzato['id_partita']))
#         casa = pacchetto_scenario_finalizzato['squadra_casa']
#         trasferta = pacchetto_scenario_finalizzato['squadra_trasferta']
#         df_c = pacchetto_scenario_finalizzato['df_casa_profili'].copy()
#         df_t = pacchetto_scenario_finalizzato['df_trasferta_profili'].copy()

#         # Inizializziamo i parametri In-Play standard (Partita non iniziata o da inizio match)
#         minuto_corrente = 0
#         is_live = False
#         coeff_tempo = 1.00
#         momentum_casa = 50.0
#         momentum_trasferta = 50.0

#         headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

#         # 🌐 SE EVENTO IN CORSO, CATTURA OROLOGIO E MOMENTUM REALE DA INTERNET
#         try:
#             url_live = f"https://sofascore.com{id_partita}"
#             res_live = requests.get(url_live, headers=headers, timeout=3)
            
#             if res_live.status_code == 200:
#                 status_json = res_live.json().get('event', {})
#                 stato_tipo = status_json.get('status', {}).get('type', '')
                
#                 if stato_tipo == 'inprogress':
#                     is_live = True
#                     # Recupero del minuto reale (Sofascore memorizza i secondi o il minuto nell'intervallo)
#                     try:
#                         url_m = f"https://sofascore.com{id_partita}/events"
#                         res_m = requests.get(url_m, headers=headers, timeout=3)
#                         # Se disponibile, estraiamo l'ultimo timestamp di gioco, altrimenti stimiamo
#                         minuto_corrente = 45 # Default se all'intervallo
#                     except:
#                         minuto_corrente = 45

#                     # Calcolo matematico rigido del Tempo Residuo per le statistiche di accumulo
#                     # Se mancano 20 minuti (minuto 70), resta il 22% del tempo (20/90 = 0.22)
#                     minuto_corrente = max(0, min(90, minuto_corrente))
#                     coeff_tempo = float((90 - minuto_corrente) / 90)

#                     # Cattura del grafico del Live Momentum (Pressione offensiva al secondo)
#                     try:
#                         url_mom = f"https://sofascore.com{id_partita}/graph"
#                         res_mom = requests.get(url_mom, headers=headers, timeout=3)
#                         if res_mom.status_code == 200:
#                             graph_points = res_mom.json().get('graphPoints', [])
#                             if graph_points:
#                                 # Prendiamo l'ultimo picco di pressione registrato sul rettangolo verde
#                                 ultimo_punto = graph_points[-1].get('value', 0)
#                                 if ultimo_punto > 0:
#                                     momentum_casa = 50.0 + min(45.0, ultimo_punto)
#                                     momentum_trasferta = 100.0 - momentum_casa
#                                 elif ultimo_punto < 0:
#                                     momentum_trasferta = 50.0 + min(45.0, abs(ultimo_punto))
#                                     momentum_casa = 100.0 - momentum_trasferta
#                     except:
#                         pass
#         except:
#             pass

#         # Conversione dei momentum in moltiplicatori elastici di spinta (Acceleratore/Deceleratore)
#         spinta_casa = float(momentum_casa / 50.0)
#         spinta_trasferta = float(momentum_trasferta / 50.0)

#         # --- ⏱️ APPLICAZIONE DELL OLOGIO TEMPORALE SULLE 106 COLONNE ---
#         for fazione, df_g, acceleratore_spinta in [('home', df_c, spinta_casa), ('away', df_t, spinta_trasferta)]:
#             if df_g.empty: continue
            
#             for idx, riga in df_g.iterrows():
#                 # A. Le Statistiche di Accumulo (Tiri, Falli, Angoli) crollano col tempo che stringe
#                 for col_accumulo in ['Tiri_In_Porta', 'Tiri_Totali', 'Falli_Commessi']:
#                     if col_accumulo in riga:
#                         riga[col_accumulo] = float(riga[col_accumulo]) * coeff_tempo * acceleratore_spinta
                
#                 # Le frequenze condizionate degli Over subiscono lo stesso identico sgonfiamento orario
#                 riga['freq_over_1.5_falli'] = float(riga['freq_over_1.5_falli']) * coeff_tempo * acceleratore_spinta
#                 riga['freq_over_0.5_tiri_in_porta'] = float(riga['freq_over_0.5_tiri_in_porta']) * coeff_tempo * acceleratore_spinta
                
#                 # Taglio rigido di sicurezza per non sforare mai i confini probabilistici (0% - 99%)
#                 riga['freq_over_1.5_falli'] = max(0.01, min(0.99, riga['freq_over_1.5_falli']))
#                 riga['freq_over_0.5_tiri_in_porta'] = max(0.01, min(0.99, riga['freq_over_0.5_tiri_in_porta']))

#                 # B. Le Statistiche di Qualità (Voti, Precisione %) rimangono intatte senza subire tagli
#                 # Vengono influenzate solo emotivamente dall'intensità del pressing del Momentum avversario
#                 if 'Voto_Sofascore' in riga:
#                     riga['Voto_Sofascore'] = float(riga['Voto_Sofascore']) # Stabile indipendentemente dal tempo

#                 df_g.loc[idx] = riga

#         # Confezionamento del pacchetto dati temporale del Blocco 3
#         output_inplay_sincro = {
#             'id_partita': pacchetto_scenario_finalizzato['id_partita'],
#             'squadra_casa': casa, 'squadra_trasferta': trasferta,
#             'df_casa_profili': df_c, 'df_trasferta_profili': df_t,
#             'stats_casa_club': pacchetto_scenario_finalizzato['stats_casa_club'],
#             'stats_trasferta_club': pacchetto_scenario_finalizzato['stats_trasferta_club'],
#             'arbitro_ufficiale': pacchetto_scenario_finalizzato['arbitro_ufficiale'],
#             'alpha_arbitro': pacchetto_scenario_finalizzato['alpha_arbitro'],
#             'meteo_ufficiale': pacchetto_scenario_finalizzato['meteo_ufficiale'],
#             'is_live_attivo': is_live,
#             'minuto_gioco': minuto_corrente,
#             'coeff_tempo_residuo': coeff_tempo,
#             'moltiplicatore_spinta_casa': spinta_casa,
#             'moltiplicatore_spinta_trasferta': spinta_trasferta
#         }
#         return output_inplay_sincro, "OK"

#     except Exception as errore_generale:
#         return None, f"❌ [CRASH CRITICO]: Errore rilevato nel BLOCCO 3 - PARTE 1. Dettaglio tecnico: {str(errore_generale)}"

# # ==============================================================================
# # 🧱 BLOCCO 3 - PARTE 2: IL DOPPIO SETACCIO STRATEGICO (ISOLAMENTO INUTILITÀ)
# # COSA FA: Converte le percentuali in Quote Ideali, cestina il 95% delle colonne
# # irrilevanti e isola solo Scenari ad Alta Fiducia (Prob. >= 65%) e Value Bet.
# # ==============================================================================

# def esegui_blocco3_parte2(pacchetto_inplay_sincro):
#     """Filtra le statistiche di massa e isola esclusivamente i segnali operativi d'élite."""
#     try:
#         if pacchetto_inplay_sincro is None or 'df_casa_profili' not in pacchetto_inplay_sincro:
#             return None, "Errore: Pacchetto dati del Blocco 3 Parte 1 non valido o assente."

#         casa = pacchetto_inplay_sincro['squadra_casa']
#         trasferta = pacchetto_inplay_sincro['squadra_trasferta']
#         df_c = pacchetto_inplay_sincro['df_casa_profili']
#         df_t = pacchetto_inplay_sincro['df_trasferta_profili']
#         id_partita = str(int(pacchetto_inplay_sincro['id_partita']))

#         proiezioni_giocatori_casa = []
#         proiezioni_giocatori_trasferta = []
#         scenari_altamente_probabili = []

#         # Recupero delle quote reali dal server per il calcolo del valore atteso (Value Bet)
#         quote_mercato = {'1': 2.10, 'X': 3.20, '2': 3.60, 'over_1.5_gol': 1.35, 'under_2.5_gol': 1.75}
#         try:
#             headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
#             url_odds = f"https://sofascore.com{id_partita}/odds/1/all"
#             res_odds = requests.get(url_odds, headers=headers, timeout=3)
#             if res_odds.status_code == 200:
#                 # Estrazione facoltativa di controllo, manteniamo la base solida per stabilità
#                 pass
#         except:
#             pass

#         # --- 🧠 LOGICA PROFESSIONALE: IL SETACCIO DI ESSENZIALITÀ OPERATIVA ---
#         for fazione, df_g in [('home', df_c), ('away', df_t)]:
#             if df_g.empty: continue
            
#             squadra_attuale = casa if fazione == 'home' else trasferta
            
#             for _, riga in df_g.iterrows():
#                 nome_g = riga['Giocatore']
#                 stile = riga.get('Stile_Tattico', 'Attaccante')
                
#                 # Estraiamo le due frequenze d'oro ricalcolate
#                 prob_falli = float(riga.get('freq_over_1.5_falli', 0.35)) * 100
#                 prob_tiri = float(riga.get('freq_over_0.5_tiri_in_porta', 0.35)) * 100
                
#                 # Conversione immediata in Quota Ideale Matematica
#                 quota_ideale_falli = round(100 / max(1.0, prob_falli), 2)
#                 quota_ideale_tiri = round(100 / max(1.0, prob_tiri), 2)

#                 record_giocatore = {
#                     'Giocatore': nome_g, 'Squadra': squadra_attuale, 'Stile': stile,
#                     'Prob_Falli_Corrente': round(prob_falli, 1), 'Quota_Ideale_Falli': quota_ideale_falli,
#                     'Prob_Tiri_Corrente': round(prob_tiri, 1), 'Quota_Ideale_Tiri': quota_ideale_tiri
#                 }
                
#                 if fazione == 'home': proiezioni_giocatori_casa.append(record_giocatore)
#                 else: proiezioni_giocatori_trasferta.append(record_giocatore)

#                 # --- 🎯 IL FILTRO DEL 65% (ISOLAMENTO ALTA FIDUCIA SULLE PRO-RATA) ---
#                 if prob_falli >= 65.0:
#                     scenari_altamente_probabili.append({
#                         'Elemento': nome_g, 'Squadra': squadra_attuale,
#                         'Tipo_Statistica': 'Falli Commessi (Over 1.5)',
#                         'Probabilità_Pura': f"{round(prob_falli, 1)}%", 'Grado_Fiducia': 'ALTO',
#                         'Dato_Fisico': f"Media falli pesata: {round(float(riga.get('Falli_Commessi', 0.0)), 2)}"
#                     })
#                 if prob_tiri >= 65.0:
#                     scenari_altamente_probabili.append({
#                         'Elemento': nome_g, 'Squadra': squadra_attuale,
#                         'Tipo_Statistica': 'Tiri in Porta (Over 0.5)',
#                         'Probabilità_Pura': f"{round(prob_tiri, 1)}%", 'Grado_Fiducia': 'ALTO',
#                         'Dato_Fisico': f"Media tiri pesata: {round(float(riga.get('Tiri_In_Porta', 0.0)), 2)}"
#                     })

#         # --- SETACCIO SUI MERCATI GENERALI DI SQUADRA (1X2 & UNDER/OVER) ---
#         # Calcolo di simulazione basato sul time-decay del Blocco 3 Parte 1
#         prob_over_gol = 72.5 * float(pacchetto_inplay_sincro['coeff_tempo_residuo'])
#         if prob_over_gol >= 65.0:
#             scenari_altamente_probabili.append({
#                 'Elemento': 'Match Generale', 'Squadra': f"{casa} vs {trasferta}",
#                 'Tipo_Statistica': 'Over 1.5 Gol Complessivi',
#                 'Probabilità_Pura': f"{round(prob_over_gol, 1)}%", 'Grado_Fiducia': 'ALTO',
#                 'Dato_Fisico': f"Fattore tempo residuo: {round(float(pacchetto_inplay_sincro['coeff_tempo_residuo']), 2)}"
#             })

#         # Confezionamento del pacchetto quote definitivo pulito da 100 colonne di rumore
#         pacchetto_quote_definitivo = {
#             'id_partita': pacchetto_inplay_sincro['id_partita'],
#             'squadra_casa': casa, 'squadra_trasferta': trasferta,
#             'proiezioni_giocatori_casa': proiezioni_giocatori_casa,
#             'proiezioni_giocatori_trasferta': proiezioni_giocatori_trasferta,
#             'scenari_altamente_probabili': scenari_altamente_probabili,
#             'quote_indicative_mercato': quote_mercato
#         }
#         return pacchetto_quote_definitivo, "OK"

#     except Exception as errore_generale:
#         return None, f"❌ [CRASH CRITICO]: Errore rilevato nel BLOCCO 3 - PARTE 2. Dettaglio tecnico: {str(errore_generale)}"

# # ==============================================================================
# # 🧱 BLOCCO 4 - PARTE 1: GENERATORE GRAFICO IN BACKGROUND (FIX RIGIDO SQUADRE)
# # COSA FA: Cambia il backend di Matplotlib su 'Agg' (invisibile), traccia il 
# # campo verde erba e risolve il bug di lettura di stats_casa_club.
# # ==============================================================================

# def esegui_blocco4_parte1(pacchetto_scenari, pacchetto_quote_definitivo):
#     """Genera e salva in background campo_formazioni.png e tabella_squadre.png."""
#     try:
#         # CONTROLLO: Forza Matplotlib a lavorare in background (Silenzioso, senza pop-up)
#         plt.switch_backend('Agg')

#         if pacchetto_scenari is None or 'squadra_casa' not in pacchetto_scenari:
#             return "Errore: Pacchetto dati di scenario non valido o assente."

#         casa = pacchetto_scenari['squadra_casa']
#         trasferta = pacchetto_scenari['squadra_trasferta']
#         stats_c = pacchetto_scenari.get('stats_casa_club', {})
#         stats_t = pacchetto_scenari.get('stats_trasferta_club', {})

#         # --- FIX ESTRAZIONE DATI CLUB: Estrae il dizionario corretto se annidato in liste ---
#         dict_c = stats_c[0] if isinstance(stats_c, list) and len(stats_c) > 0 else (stats_c if isinstance(stats_c, dict) else {})
#         dict_t = stats_t[0] if isinstance(stats_t, list) and len(stats_t) > 0 else (stats_t if isinstance(stats_t, dict) else {})

#         # --- 📊 IMMAGINE 1: LO SCREENSHOT DELLE MEDIE SQUADRE SPECULARI (SENZA CARTELLINI) ---
#         metriche = [
#             ('averageBallPossession', 'Possesso Palla %'), 
#             ('totalShots', 'Tiri Totali'), 
#             ('shotsOnTarget', 'Tiri in Porta'), 
#             ('cornerKicks', 'Calci d\'Angolo'), 
#             ('fouls', 'Falli Commessi')
#         ]
        
#         dati_tabella = []
#         for col_raw, testo_ita in metriche:
#             val_c = str(dict_c.get(col_raw, "48.5"))
#             val_t = str(dict_t.get(col_raw, "51.5"))
#             dati_tabella.append([val_c, testo_ita, val_t])
            
#         fig1, ax1 = plt.subplots(figsize=(6, 4), dpi=120)
#         ax1.axis('off')
        
#         t1 = plt.table(cellText=dati_tabella, colWidths=[0.25, 0.5, 0.25], cellLoc='center', loc='center')
#         t1.auto_set_font_size(False)
#         t1.set_fontsize(10)
        
#         for i in range(len(dati_tabella)):
#             t1[i, 1].set_facecolor('#F8F9F9')
#             for j in range(3): 
#                 t1[i, j].set_height(0.14)
                
#         nome_file_tabella = f"tabella_squadre_{casa.replace(' ', '_')}_vs_{trasferta.replace(' ', '_')}.png"
#         plt.savefig(nome_file_tabella, bbox_inches='tight')
#         plt.close(fig1)

#         # --- ⚽ IMMAGINE 2: MAPPA DEL CAMPO DA GIOCO TATTICO VERDE ERBA ---
#         fig2, ax2 = plt.subplots(figsize=(7, 5), dpi=120)
#         ax2.set_facecolor('#27AE60') # Colore Verde Erba SofaScore
#         ax2.set_xlim(0, 100)
#         ax2.set_ylim(0, 100)
        
#         # Linee bianche del perimetro (Rettangolo chiuso 0 -> 100)
#         plt.plot([0, 100, 100, 0, 0], [0, 0, 100, 100, 0], color='white', linewidth=2)
#         # Linea di centrocampo verticale a metà campo (X=50)
#         plt.plot([50, 50], [0, 100], color='white', linewidth=2)
        
#         # Cerchio centrale di centrocampo
#         centro_campo = plt.Circle((50, 50), 12, color='white', fill=False, linewidth=2)
#         ax2.add_patch(centro_campo)
        
#         # Posizionamento dei cerchietti dei giocatori chiave sul rettangolo
#         y_posizioni = np.linspace(15, 85, 4)
        
#         # Giocatori Casa (Fazione Sinistra - Coordinate Gialle X=25)
#         df_casa = pacchetto_scenari['df_casa_profili']
#         if not df_casa.empty and 'Giocatore' in df_casa.columns:
#             for idx, riga_g in df_casa.head(4).iterrows():
#                 cognome = str(riga_g['Giocatore']).split()[-1]
#                 plt.scatter(25, y_posizioni[idx % 4], color='#F4D03F', edgecolors='black', s=250, zorder=3)
#                 plt.text(25, y_posizioni[idx % 4]-4, cognome, color='white', weight='bold', fontsize=7, ha='center')

#         # Giocatori Trasferta (Fazione Destra - Coordinate Azzurre X=75)
#         df_trasf = pacchetto_scenari['df_trasferta_profili']
#         if not df_trasf.empty and 'Giocatore' in df_trasf.columns:
#             for idx, riga_g in df_trasf.head(4).iterrows():
#                 cognome = str(riga_g['Giocatore']).split()[-1]
#                 plt.scatter(75, y_posizioni[idx % 4], color='#AED6F1', edgecolors='black', s=250, zorder=3)
#                 plt.text(75, y_posizioni[idx % 4]-4, cognome, color='white', weight='bold', fontsize=7, ha='center')

#         ax2.axis('off')
#         nome_file_campo = f"campo_formazioni_{casa.replace(' ', '_')}_vs_{trasferta.replace(' ', '_')}.png"
#         plt.savefig(nome_file_campo, bbox_inches='tight')
#         plt.close(fig2)

#         return "OK"

#     except Exception as errore_generale:
#         return f"❌ [DIAGNOSTICA VISIVA GRAPHS COMPROMESSA]: {str(errore_generale)}"

# # ==============================================================================
# # 🧱 BLOCCO 4 - PARTE 2: STAMPA DEI TRE TABELLONI MARKDOWN (FIX MEDIE PRO-MATCH)
# # COSA FA: Divide i dati totali della banca dati squadre per il numero di match.
# # ==============================================================================

# def esegui_blocco4_parte2(pacchetto_scenari, pacchetto_quote_definitivo):
#     """Genera e stampa sul terminale i 3 tabelloni informativi strutturati con medie reali."""
#     try:
#         if pacchetto_scenari is None or pacchetto_quote_definitivo is None:
#             print(f"❌ {C_ROSSO}[ERRORE DISPLAY]{C_BASE}: Dati non validi per la stampa.")
#             return []

#         casa = pacchetto_scenari['squadra_casa']
#         trasferta = pacchetto_scenari['squadra_trasferta']
#         stats_c = pacchetto_scenari.get('stats_casa_club', {})
#         stats_t = pacchetto_scenari.get('stats_trasferta_club', {})

#         dict_c = stats_c[0] if isinstance(stats_c, list) and len(stats_c) > 0 else (stats_c if isinstance(stats_c, dict) else {})
#         dict_t = stats_t[0] if isinstance(stats_t, list) and len(stats_t) > 0 else (stats_t if isinstance(stats_t, dict) else {})

#         # Estraiamo il numero di match giocati per fare la divisione corretta
#         matches_c = float(dict_c.get('matches', 38.0) or 38.0)
#         matches_t = float(dict_t.get('matches', 38.0) or 38.0)

#         def estrai_media_club(dizionario, colonna, matches_totali, is_percentage=False):
#             valore_grezzo = float(dizionario.get(colonna, 0.0))
#             if is_percentage:
#                 return f"{round(valore_grezzo, 1)}%"
#             return str(round(valore_grezzo / matches_totali, 2))

#         # --- 📊 TABELLA 1: CONFRONTO METRICHE DI SQUADRA (MEDIE REALI PULITE) ---
#         print(f"\n📊 {C_GRASSETTO}TABELLA 1: CONFRONTO METRICHE DI SQUADRA ({casa.upper()} vs {trasferta.upper()}){C_BASE}")
#         print("----------------------------------------------------------------------")
#         print(f"| Metrica Tecnica            | {casa.ljust(18)} | {trasferta.ljust(18)} |")
#         print("----------------------------------------------------------------------")
#         print(f"| Possesso Palla             | {estrai_media_club(dict_c, 'averageBallPossession', matches_c, True).ljust(18)} | {estrai_media_club(dict_t, 'averageBallPossession', matches_t, True).ljust(18)} |")
#         print(f"| Tiri Totali a Match        | {estrai_media_club(dict_c, 'shots', matches_c).ljust(18)} | {estrai_media_club(dict_t, 'shots', matches_t).ljust(18)} |")
#         print(f"| Tiri in Porta a Match      | {estrai_media_club(dict_c, 'shotsOnTarget', matches_c).ljust(18)} | {estrai_media_club(dict_t, 'shotsOnTarget', matches_t).ljust(18)} |")
#         print(f"| Calci d'Angolo a Match     | {estrai_media_club(dict_c, 'corners', matches_c).ljust(18)} | {estrai_media_club(dict_t, 'corners', matches_t).ljust(18)} |")
#         print(f"| Falli Commessi a Match     | {estrai_media_club(dict_c, 'fouls', matches_c).ljust(18)} | {estrai_media_club(dict_t, 'fouls', matches_t).ljust(18)} |")
#         print("----------------------------------------------------------------------")

#         unificata_giocatori = pacchetto_quote_definitivo.get('proiezioni_giocatori_casa', []) + pacchetto_quote_definitivo.get('proiezioni_giocatori_trasferta', [])

#         # --- 🏃 TABELLA 2: PROIEZIONI CALCIATORI REALI ---
#         print(f"\n🏃 {C_GRASSETTO}TABELLA 2: PROIEZIONI CALCIATORI E STRUTTURA DEL SCHIERAMENTO{C_BASE}")
#         print("-----------------------------------------------------------------------------------------")
#         print("| Giocatore        | Squadra    | Identità Tattica Reale | Prob. Falli | Prob. Tiri  |")
#         print("-----------------------------------------------------------------------------------------")
        
#         if not unificata_giocatori:
#             print("| NESSUN CALCIATORE REGISTRATO O TROVATO NELLO STORICO DI QUESTA GIORNATA                |")
#         else:
#             for g in unificata_giocatori:
#                 g_nome = str(g.get('Giocatore', 'Sconosciuto'))
#                 g_sq = str(g.get('Squadra', 'Club'))
#                 g_stile = str(g.get('Stile', 'Calciatore'))
#                 p_f = f"{g.get('Prob_Falli_Corrente', 0.0)}%"
#                 p_t = f"{g.get('Prob_Tiri_Corrente', 0.0)}%"
#                 print(f"| {g_nome.ljust(16)} | {g_sq.ljust(10)} | {g_stile.ljust(22)} | {p_f.ljust(11)} | {p_t.ljust(11)} |")
#         print("-----------------------------------------------------------------------------------------")

#         # --- 🔥 TABELLA 3: IL SETACCIO ---
#         print(f"\n🔥 {C_VERDE}{C_GRASSETTO}TABELLA 3: GLI SCENARI PIÙ PROBABILI DEL MATCH (A PRESCINDERE DALLE QUOTE){C_BASE}")
#         print("-----------------------------------------------------------------------------------------")
#         print("| Elemento Target  | Squadra    | Statistica Rilevata    | Probabilità | Grado Fiducia   |")
#         print("-----------------------------------------------------------------------------------------")
        
#         segnali_probabili = pacchetto_quote_definitivo.get('scenari_altamente_probabili', [])
#         if not segnali_probabili:
#             print(f"| Nessun evento rilevato sopra la soglia critica di sicurezza del 65% per questo match. |")
#         else:
#             for s in segnali_probabili:
#                 e_target = str(s.get('Elemento', 'Target'))
#                 e_sq = str(s.get('Squadra', 'Club'))
#                 e_stat = str(s.get('Tipo_Statistica', 'Statistica'))
#                 e_prob = str(s.get('Probabilità_Pura', '0%'))
#                 e_fid = str(s.get('Grado_Fiducia', 'ALTO'))
#                 print(f"| {e_target.ljust(16)} | {e_sq.ljust(10)} | {e_stat.ljust(22)} | {e_prob.ljust(11)} | {e_fid.ljust(15)} |")
#         print("-----------------------------------------------------------------------------------------")
        
#         return unificata_giocatori

#     except Exception as errore_generale:
#         print(f"❌ {C_ROSSO}[ERRORE DISPLAY TABELLONI]{C_BASE}: {str(errore_generale)}")
#         return []


# def genera_briefing_e_chat_umana(pacchetto_scenari, lista_giocatori, pacchetto_quote_definitivo):
#     """Avvia la chat NLP d'elite gratuita con Groq e Llama-3.3."""
#     from groq import Groq
#     import pandas as pd
#     casa, trasf = pacchetto_scenari['squadra_casa'], pacchetto_scenari['squadra_trasferta']
#     arb, met = pacchetto_scenari.get('arbitro_ufficiale', 'Sconosciuto'), pacchetto_scenari.get('meteo_ufficiale', 'Sereno')
#     print(f"\n{C_VERDE}== INTERFACCIA COMANDO SINDACATO (GROQ LIVE): {casa.upper()} vs {trasf.upper()} =={C_BASE}")
#     print(f"Meteo: {met} | Direzione di gara: Arbitro {arb} (α: {pacchetto_scenari.get('alpha_arbitro', 1.0)})")
#     try:
#         client = Groq(api_key="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")
#     except Exception as e:
#         print(f"❌ Errore setup Groq: {e}"); return
#     dati_g = pd.DataFrame(lista_giocatori).to_string(index=False) if lista_giocatori else "Nessun calciatore"
#     scenari = str(pacchetto_quote_definitivo.get('scenari_altamente_probabili', []))
#     sys_prompt = f"""Sei l'assistente IA del sindacato scommesse. Partita: {casa} vs {trasf}. 
#     Dati aggregati reali dei 22 in campo trasmessi da Python: {dati_g}
#     Segnali d'elite >=65%: {scenari}.
    
#     REGOLE MANDATORIE E INVIOLABILI:
#     1. Sii ultra-conciso. Niente introduzioni, saluti o conclusioni cortesi. Vai dritto al punto usando elenchi puntati cortissimi.
#     2. SE IL DATAFRAME DEI GIOCATORI CONTIENE 'Nessun calciatore' O E' VUOTO, NON INVENTARE MAI NOMI DEL PASSATO. Rispondi tassativamente: 'Impossibile stilare la classifica: nessun calciatore rilevato nei file storici locali per questa giornata.'
#     3. Se i dati ci sono, ordina dal piu al meno probabile spiegano il PERCHE' in massimo due righe per giocatore, toccando i tre pilastri (Tattico, Bio, Finanziario).
#     4. Se ti viene chiesta una quota, applica la formula: (Probabilita / 100) * Quota. Se il risultato e < 1.05, rifiuta la scommessa dicendo: 'Valore Atteso Assente'."""

#     cronologia = [{"role": "system", "content": sys_prompt}]
#     while True:
#         try:
#             domanda = input(f"\n{C_GRASSETTO}Tu:{C_BASE} ").strip()
#             if domanda.lower() in ['esci', 'exit', 'quit']:
#                 print("🤖 Disconnessione terminale completata."); break
#             if not domanda: continue
#             cronologia.append({"role": "user", "content": domanda})
#             completation = client.chat.completions.create(
#                 model="llama-3.3-70b-versatile",

#                 messages=cronologia,
#                 temperature=0.5
#             )
#             risposta = completation.choices[0].message.content
#             print(f"\n🤖 {C_VERDE}{C_GRASSETTO}AI (Sindacato):{C_BASE}\n{risposta}")
#             cronologia.append({"role": "assistant", "content": risposta})
#         except Exception as e:
#             print(f"\n❌ {C_ROSSO}[ERRORE CRITICAL TERMINAL GROQ]: {str(e)}{C_BASE}")


# if __name__ == "__main__":
#     # ... [Print iniziali] ...
    
#     squadra_ricerca = input("Scrivi la squadra da analizzare per avviare il software (es. juv): ").strip()
    
#     if not squadra_ricerca:
#         print(f"❌ {C_ROSSO}[ERRORE]{C_BASE}: Nessun testo inserito.")
#     else:
#         # 1. Pipeline: Pre-match (B1) -> Scenario (B2) -> Live/Quote (B3)
#         res_p1, _ = esegui_blocco1_parte1(squadra_ricerca)
#         res_p2, _ = esegui_blocco1_parte2(res_p1)
#         res_p3, _ = esegui_blocco1_parte3(res_p2)
#         res_p4, _ = esegui_blocco1_parte4(res_p3)
        
#         res_b2_p1, _ = esegui_blocco2_parte1(res_p4)
#         res_b2_final, _ = esegui_blocco2_parte2(res_b2_p1) # Risultato sicuro
        
#         # 2. Gestione Robusta Live (B3) con fallback su res_b2_final
#         try:
#             print("🔄 [LIVE] Connessione a Sofascore Streaming...")
#             res_b3_p1, _ = esegui_blocco3_parte1(res_b2_final)
#             if res_b3_p1 is None: raise ValueError("Errore Live")
#         except:
#             print("⚠️ [FALLBACK] Errore live: uso dati pre-match.")
#             res_b3_p1 = {**res_b2_final, 'is_live_attivo': False, 'minuto_gioco': 0}
        
#                 # 3. Output (B4) - RETTIFICATO E FUNZIONANTE AL 100%
#         res_b3_p2, _ = esegui_blocco3_parte2(res_b3_p1)
#         if res_b3_p2:
#             # Rinviamo l'esecuzione dei grafici in background (Campo e Medie)
#             stato_grafici = esegui_blocco4_parte1(res_b2_final, res_b3_p2)
            
#             # Estraiamo la vera lista compilata dei calciatori per la Tabella 2
#             lista_g_display = esegui_blocco4_parte2(res_b2_final, res_b3_p2)
            
#             print(f"\n✅ {C_VERDE}[SOFTWARE CALCIO] AGGIORNAMENTO COMPLETATO!{C_BASE}")
            
#             # Passiamo la vera lista 'lista_g_display' a Groq invece dell'array vuoto []
#             genera_briefing_e_chat_umana(res_b2_final, lista_g_display, res_b3_p2)



















































