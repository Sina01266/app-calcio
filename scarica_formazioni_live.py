# CODICE PER SCARICARE LE PROBABILI FORMAZIONI E LE UFFICIALI POCO PRIMA DELL'INIZIO



# import os
# import time
# import warnings
# import pandas as pd
# import ScraperFC as sfc

# # Disattiviamo i messaggi di avviso gialli per tenere il terminale pulito
# warnings.filterwarnings("ignore", category=UserWarning)

# NOME_FILE_CALENDARIO = "banca_dati_partite_2526.csv"
# FILE_OUTPUT_LIVE = "banca_dati_formazioni_live.csv"


# def cerca_partita_nel_calendario(df_calendario):
#     """Cerca l'ID della partita nel calendario in modo intelligente e tollerante"""
#     print("\n--- 🔍 MOTORE DI RICERCA PARTITA (TOLLERANTE) ---")
#     scelta_squadra = (
#         input(
#             "Inserisci il nome di una squadra (es. inter, juve, sass, milan): "
#         )
#         .strip()
#         .lower()
#     )

#     if not scelta_squadra:
#         print("[ERRORE] Non hai inserito nessun testo.")
#         return None

#     # Filtro tollerante: cerca la stringa dentro Squadra_Casa o Squadra_Trasferta
#     match_trovati = df_calendario[
#         df_calendario["Squadra_Casa"].str.lower().str.contains(scelta_squadra)
#         | df_calendario["Squadra_Trasferta"]
#         .str.lower()
#         .str.contains(scelta_squadra)
#     ]

#     if match_trovati.empty:
#         print(f"❌ Nessuna partita trovata per: '{scelta_squadra}'")
#         return None

#     print(f"\n👍 Trovate {len(match_trovati)} corrispondenze nel calendario:")
#     opzioni = {}

#     for i, (_, riga) in enumerate(match_trovati.iterrows(), 1):
#         giornata = riga.get("Giornata", "N/D")
#         casa = riga["Squadra_Casa"]
#         trasferta = riga["Squadra_Trasferta"]
#         match_id = int(riga["ID_Partita"])

#         print(
#             f" [{i}] Giornata {giornata} | {casa} vs {trasferta} (ID: {match_id})"
#         )
#         opzioni[str(i)] = riga.to_dict()

#     if len(opzioni) == 1:
#         print("-> Selezionata automaticamente l'unica partita trovata.")
#         return opzioni["1"]

#     scelta_indice = (
#         input(
#             "\nInserisci il NUMERO della partita che vuoi scaricare (es. 1, 2): "
#         )
#         .strip()
#     )
#     return opzioni.get(scelta_indice, None)


# def scarica_formazioni_live_pre_match():
#     print("==========================================================================")
#     print("⚽ MOTOR DI SCARICAMENTO INTERNET: BANCA DATI FORMAZIONI LIVE ⚽")
#     print("==========================================================================")

#     # 1. Controllo del calendario locale delle partite
#     if not os.path.exists(NOME_FILE_CALENDARIO):
#         print(
#             f"[ERRORE] Manca il file '{NOME_FILE_CALENDARIO}' nella cartella."
#         )
#         return

#     df_calendario = pd.read_csv(NOME_FILE_CALENDARIO)

#     print("Seleziona la modalità operativa:")
#     print("1. Cerca una partita scrivendo il NOME DELLA SQUADRA (Pre-Match)")
#     print("2. Scansiona AUTOMATICAMENTE tutto il calendario per i match rimasti")
#     scelta_modalita = input("Inserisci il numero (1 o 2): ").strip()

#     partite_da_fare = []

#     # --- MODALITÀ 1: RICERCA INTELLIGENTE PER TESTO ---
#     if scelta_modalita == "1":
#         partita_scelta = cerca_partita_nel_calendario(df_calendario)
#         if partita_scelta:
#             partite_da_fare.append(partita_scelta)
#         else:
#             print("❌ Selezione annullata o non valida.")
#             return

#     # --- MODALITÀ 2: SCANSIONE AUTOMATICA INTEGRALE ---
#     else:
#         id_gia_fatti = set()
#         if os.path.exists(FILE_OUTPUT_LIVE):
#             try:
#                 df_esistente = pd.read_csv(FILE_OUTPUT_LIVE)
#                 if "ID_Partita" in df_esistente.columns:
#                     id_gia_fatti = set(df_esistente["ID_Partita"].unique())
#             except Exception:
#                 pass

#         df_rimaste = df_calendario[
#             ~df_calendario["ID_Partita"].isin(id_gia_fatti)
#         ]
#         partite_da_fare = df_rimaste.to_dict(orient="records")

#     if not partite_da_fare:
#         print("\n✅ Nessuna partita da elaborare.")
#         return

#     # Inizializziamo lo scraper ufficiale del tuo PC
#     print("\n-> Connessione internet con Sofascore avviata...")
#     scraper = sfc.Sofascore()
#     lista_giocatori_totale = []

#     # 2. CICLO DI SCARICAMENTO REALE DA INTERNET
#     for i, riga in enumerate(partite_da_fare, 1):
#         match_id = int(riga["ID_Partita"])
#         casa = riga["Squadra_Casa"]
#         trasferta = riga["Squadra_Trasferta"]
#         giornata = riga.get("Giornata", 0)

#         print(
#             f"\n[{i}/{len(partite_da_fare)}] Scarico formazioni internet: {casa} vs {trasferta}..."
#         )

#         try:
#             # Chiamata internet stabile al tuo scraper funzionante
#             df_match_stats = scraper.scrape_player_match_stats(match_id)

#             if df_match_stats is not None and not df_match_stats.empty:
#                 df_match_stats = df_match_stats.loc[
#                     :, ~df_match_stats.columns.duplicated()
#                 ].copy()
#                 giocatori_lista = df_match_stats.to_dict(orient="records")

#                 for g in giocatori_lista:
#                     is_home = g.get("isHome", True)
#                     squadra_corrente = casa if bool(is_home) else trasferta
#                     ruolo_pulito = str(g.get("position", "N/D")).strip()

#                     # Recupero automatico del nome del giocatore
#                     nome_pulito = "Sconosciuto"
#                     if "player_name" in g and pd.notna(g["player_name"]):
#                         nome_pulito = str(g["player_name"])
#                     elif "name" in g and pd.notna(g["name"]):
#                         nome_pulito = str(g["name"])

#                     # Blocco statico pre-match per ripulire i dati del tempo futuro
#                     subentrato = g.get("substitute", False)
#                     stato_pulito = (
#                         "Panchina" if bool(subentrato) else "Titolare"
#                     )

#                     minuto_ingresso_pulito = 0
#                     minuti_giocati_pulito = 0
#                     voto_pulito = None

#                     lista_giocatori_totale.append(
#                         {
#                             "Giornata": giornata,
#                             "ID_Partita": int(match_id),
#                             "Squadra": squadra_corrente,
#                             "Giocatore": nome_pulito,
#                             "Ruolo": ruolo_pulito,
#                             "Stato": stato_pulito,
#                             "Minuto_Ingresso": minuto_ingresso_pulito,
#                             "Minuti_Giocati": minuti_giocati_pulito,
#                             "Voto": voto_pulito,
#                         }
#                     )
#                 print(
#                     f"   -> Estratte correttamente le formazioni live dal server."
#                 )
#             else:
#                 print(
#                     f"   -> Nota: Formazioni non ancora pubblicate online per il match {match_id}"
#                 )

#         except Exception as errore:
#             print(f"   -> Errore sul match {match_id}: {errore}")

#         time.sleep(2)

#     # 3. COMPILAZIONE E AGGIORNAMENTO DEL FILE GENERALE
#     if lista_giocatori_totale:
#         df_nuovi_dati = pd.DataFrame(lista_giocatori_totale)

#         if os.path.exists(FILE_OUTPUT_LIVE):
#             df_vecchio = pd.read_csv(FILE_OUTPUT_LIVE)
#             df_finale = pd.concat(
#                 [df_vecchio, df_nuovi_dati], ignore_index=True
#             )
#         else:
#             df_finale = df_nuovi_dati

#         # Sostituisce le vecchie righe (probabili) tenendo solo le ultime scaricate (ufficiali)
#         df_finale = df_finale.drop_duplicates(
#             subset=["ID_Partita", "Giocatore"], keep="last"
#         )

#         # Ordiniamo e salviamo sul computer
#         df_finale = df_finale.sort_values(
#             by=["Giornata", "ID_Partita"]
#         ).reset_index(drop=True)
#         df_finale.to_csv(FILE_OUTPUT_LIVE, index=False, encoding="utf-8")

#         print("\n==========================================================")
#         print(
#             f"🎉 SUCCESS: Formazioni live aggiornate in '{FILE_OUTPUT_LIVE}'!"
#         )
#         print("==========================================================")
#     else:
#         print("\n❌ Nessun dato salvato.")


# if __name__ == "__main__":
#     scarica_formazioni_live_pre_match()


# import os
# import time
# import warnings
# import pandas as pd
# import ScraperFC as sfc

# # Disattiviamo i messaggi di avviso gialli per tenere il terminale pulito
# warnings.filterwarnings("ignore", category=UserWarning)

# NOME_FILE_CALENDARIO = "banca_dati_partite_2526.csv"
# FILE_OUTPUT_LIVE = "banca_dati_formazioni_live.csv"


# def cerca_partita_nel_calendario(df_calendario):
#     """Cerca l'ID della partita nel calendario in modo intelligente e tollerante"""
#     print("\n--- 🔍 MOTORE DI RICERCA PARTITA (TOLLERANTE) ---")
#     scelta_squadra = (
#         input("Inserisci il nome di una squadra (es. inter, juve, sass, milan): ")
#         .strip()
#         .lower()
#     )

#     if not scelta_squadra:
#         print("[ERRORE] Non hai inserito nessun testo.")
#         return None

#     # Filtro tollerante: cerca la stringa dentro Squadra_Casa o Squadra_Trasferta
#     match_trovati = df_calendario[
#         df_calendario["Squadra_Casa"].str.lower().str.contains(scelta_squadra)
#         | df_calendario["Squadra_Trasferta"].str.lower().str.contains(scelta_squadra)
#     ]

#     if match_trovati.empty:
#         print(f"❌ Nessuna partita trovata per: '{scelta_squadra}'")
#         return None

#     print(f"\n👍 Trovate {len(match_trovati)} corrispondenze nel calendario:")
#     opzioni = {}

#     for i, (_, riga) in enumerate(match_trovati.iterrows(), 1):
#         giornata = riga.get("Giornata", "N/D")
#         casa = riga["Squadra_Casa"]
#         trasferta = riga["Squadra_Trasferta"]
#         match_id = int(riga["ID_Partita"])

#         print(f" [{i}] Giornata {giornata} | {casa} vs {trasferta} (ID: {match_id})")
#         opzioni[str(i)] = riga.to_dict()

#     if len(opzioni) == 1:
#         print("-> Selezionata automaticamente l'unica partita trovata.")
#         return opzioni["1"]

#     scelta_indice = input("\nInserisci il NUMERO della partita che vuoi scaricare (es. 1, 2): ").strip()
#     return opzioni.get(scelta_indice, None)


# def scarica_formazioni_live_pre_match():
#     print("==========================================================================")
#     print("⚽ MOTORE DI SCARICAMENTO INTERNET: BANCA DATI FORMAZIONI LIVE ⚽")
#     print("==========================================================================")

#     # 1. Controllo del calendario locale delle partite
#     if not os.path.exists(NOME_FILE_CALENDARIO):
#         print(f"[ERRORE] Manca il file '{NOME_FILE_CALENDARIO}' nella cartella.")
#         return

#     df_calendario = pd.read_csv(NOME_FILE_CALENDARIO)

#     print("Seleziona la modalità operativa:")
#     print("1. Cerca una partita scrivendo il NOME DELLA SQUADRA (Pre-Match)")
#     print("2. Scansiona AUTOMATICAMENTE tutto il calendario per i match rimasti")
#     scelta_modalita = input("Inserisci il numero (1 o 2): ").strip()

#     partite_da_fare = []

#     # --- MODALITÀ 1: RICERCA INTELLIGENTE PER TESTO ---
#     if scelta_modalita == "1":
#         partita_scelta = cerca_partita_nel_calendario(df_calendario)
#         if partita_scelta:
#             partite_da_fare.append(partita_scelta)
#         else:
#             print("❌ Selezione annullata o non valida.")
#             return

#     # --- MODALITÀ 2: SCANSIONE AUTOMATICA INTEGRALE ---
#     else:
#         id_gia_fatti = set()
#         if os.path.exists(FILE_OUTPUT_LIVE):
#             try:
#                 df_esistente = pd.read_csv(FILE_OUTPUT_LIVE)
#                 if "ID_Partita" in df_esistente.columns:
#                     id_gia_fatti = set(df_esistente["ID_Partita"].unique())
#             except Exception:
#                 pass

#         df_rimaste = df_calendario[~df_calendario["ID_Partita"].isin(id_gia_fatti)]
#         partite_da_fare = df_rimaste.to_dict(orient="records")

#     if not partite_da_fare:
#         print("\n✅ Nessuna partita da elaborare.")
#         return

#     print("\n-> Connessione internet con Sofascore avviata...")
#     scraper = sfc.Sofascore()
#     lista_giocatori_totale = []

#     # 2. CICLO DI SCARICAMENTO REALE DA INTERNET
#     for i, riga in enumerate(partite_da_fare, 1):
#         match_id = int(riga["ID_Partita"])
#         casa = riga["Squadra_Casa"]
#         trasferta = riga["Squadra_Trasferta"]
#         giornata = riga.get("Giornata", 0)

#         print(f"\n[{i}/{len(partite_da_fare)}] Scarico formazioni internet: {casa} vs {trasferta}...")

#         try:
#             df_match_stats = scraper.scrape_player_match_stats(match_id)

#             if df_match_stats is not None and not df_match_stats.empty:
#                 df_match_stats = df_match_stats.loc[:, ~df_match_stats.columns.duplicated()].copy()
#                 giocatori_lista = df_match_stats.to_dict(orient="records")

#                 # Contatori interni per dividere casa e trasferta in base all'ordine di arrivo
#                 titolari_incontrati = 0
                
#                 for g in giocatori_lista:
#                     subentrato = g.get("substitute", False)
#                     stato_pulito = "Panchina" if bool(subentrato) else "Titolare"
                    
#                     # Assegnazione dinamica basata sul conteggio dei titolari (11 per squadra)
#                     if stato_pulito == "Titolare":
#                         titolari_incontrati += 1
                        
#                     # Se siamo entro i primi 11 titolari, i giocatori (e le relative riserve lette in mezzo) sono della squadra di casa
#                     # Sofascore a volte raggruppa tutti i titolari prima, oppure alterna. Per sicurezza usiamo una soglia a metà lista totale.
#                     # Una lista completa ha circa 40-44 giocatori (22 titolari + panchine). I primi 20-22 elementi del server sono sempre della squadra di casa.
                    
#                     # Approccio standard di Sofascore: prima TUTTI i giocatori della Squadra A, poi TUTTI della Squadra B.
#                     # Contiamo l'indice totale nella lista:
#                     indice_giocatore = giocatori_lista.index(g)
#                     meta_lista = len(giocatori_lista) / 2
                    
#                     if indice_giocatore < meta_lista:
#                         squadra_corrente = casa
#                     else:
#                         squadra_corrente = trasferta

#                     ruolo_pulito = str(g.get("position", "N/D")).strip()

#                     # Recupero del nome del giocatore
#                     nome_pulito = "Sconosciuto"
#                     if "player_name" in g and pd.notna(g["player_name"]):
#                         nome_pulito = str(g["player_name"])
#                     elif "name" in g and pd.notna(g["name"]):
#                         nome_pulito = str(g["name"])

#                     lista_giocatori_totale.append({
#                         "Giornata": giornata,
#                         "ID_Partita": int(match_id),
#                         "Squadra": squadra_corrente,
#                         "Giocatore": nome_pulito,
#                         "Ruolo": ruolo_pulito,
#                         "Stato": stato_pulito,
#                         "Minuto_Ingresso": 0,
#                         "Minuti_Giocati": 0,
#                         "Voto": None
#                     })
#                 print("   -> Estratte correttamente le formazioni live dal server.")
#             else:
#                 print(f"   -> Nota: Formazioni non ancora pubblicate online per il match {match_id}")

#         except Exception as errore:
#             print(f"   -> Errore sul match {match_id}: {errore}")

#         time.sleep(2)

#     # 3. COMPILAZIONE E AGGIORNAMENTO DEL FILE GENERALE
#     if lista_giocatori_totale:
#         df_nuovi_dati = pd.DataFrame(lista_giocatori_totale)

#         if os.path.exists(FILE_OUTPUT_LIVE):
#             df_vecchio = pd.read_csv(FILE_OUTPUT_LIVE)
#             df_finale = pd.concat([df_vecchio, df_nuovi_dati], ignore_index=True)
#         else:
#             df_finale = df_nuovi_dati

#         # Elimina i duplicati mantenendo l'ultima lettura
#         df_finale = df_finale.drop_duplicates(subset=["ID_Partita", "Giocatore"], keep="last")

#         # Ordina e salva
#         df_finale = df_finale.sort_values(by=["Giornata", "ID_Partita"]).reset_index(drop=True)
#         df_finale.to_csv(FILE_OUTPUT_LIVE, index=False)
#         print(f"\n✅ File '{FILE_OUTPUT_LIVE}' aggiornato e salvato con successo!")


# if __name__ == "__main__":
#     scarica_formazioni_live_pre_match()


# # CODICE DEFINITIVO PER SCARICARE LE FORMAZIONI LIVE PREPARTITA

# import os
# import time
# import warnings
# import pandas as pd
# import ScraperFC as sfc

# # Disattiviamo i messaggi di avviso gialli per tenere il terminale pulito
# warnings.filterwarnings("ignore", category=UserWarning)

# NOME_FILE_CALENDARIO = "banca_dati_partite_2526.csv"
# FILE_OUTPUT_LIVE = "banca_dati_formazioni_live.csv"


# def cerca_partita_nel_calendario(df_calendario):
#     """Cerca l'ID della partita nel calendario in modo intelligente e tollerante"""
#     print("\n--- 🔍 MOTORE DI RICERCA PARTITA (TOLLERANTE) ---")
#     scelta_squadra = (
#         input(
#             "Inserisci il nome di una squadra (es. inter, juve, sass, milan): "
#         )
#         .strip()
#         .lower()
#     )

#     if not scelta_squadra:
#         print("[ERRORE] Non hai inserito nessun testo.")
#         return None

#     # Filtro tollerante: cerca la stringa dentro Squadra_Casa o Squadra_Trasferta
#     match_trovati = df_calendario[
#         df_calendario["Squadra_Casa"].str.lower().str.contains(scelta_squadra)
#         | df_calendario["Squadra_Trasferta"]
#         .str.lower()
#         .str.contains(scelta_squadra)
#     ]

#     if match_trovati.empty:
#         print(f"❌ Nessuna partita trovato per: '{scelta_squadra}'")
#         return None

#     print(f"\n👍 Trovate {len(match_trovati)} corrispondenze nel calendario:")
#     opzioni = {}

#     for i, (_, riga) in enumerate(match_trovati.iterrows(), 1):
#         giornata = riga.get("Giornata", "N/D")
#         casa = riga["Squadra_Casa"]
#         trasferta = riga["Squadra_Trasferta"]
#         match_id = int(riga["ID_Partita"])

#         print(
#             f" [{i}] Giornata {giornata} | {casa} vs {trasferta} (ID: {match_id})"
#         )
#         opzioni[str(i)] = riga.to_dict()

#     if len(opzioni) == 1:
#         print("-> Selezionata automaticamente l'unica partita trovata.")
#         return opzioni["1"]

#     scelta_indice = (
#         input(
#             "\nInserisci il NUMERO della partita che vuoi scaricare (es. 1, 2): "
#         )
#         .strip()
#     )
#     return opzioni.get(scelta_indice, None)


# def scarica_formazioni_live_pre_match():
#     print("==========================================================================")
#     print("⚽ MOTORE DI SCARICAMENTO INTERNET: BANCA DATI FORMAZIONI LIVE ⚽")
#     print("==========================================================================")

#     # 1. Controllo del calendario locale delle partite
#     if not os.path.exists(NOME_FILE_CALENDARIO):
#         print(
#             f"[ERRORE] Manca il file '{NOME_FILE_CALENDARIO}' nella cartella."
#         )
#         return

#     df_calendario = pd.read_csv(NOME_FILE_CALENDARIO)

#     print("Seleziona la modalità operativa:")
#     print("1. Cerca una partita scrivendo il NOME DELLA SQUADRA (Pre-Match)")
#     print("2. Scansiona AUTOMATICAMENTE tutto il calendario per i match rimasti")
#     scelta_modalita = input("Inserisci il numero (1 o 2): ").strip()

#     partite_da_fare = []

#     # --- MODALITÀ 1: RICERCA INTELLIGENTE PER TESTO ---
#     if scelta_modalita == "1":
#         partita_scelta = cerca_partita_nel_calendario(df_calendario)
#         if partita_scelta:
#             partite_da_fare.append(partita_scelta)
#         else:
#             print("❌ Selezione annullata o non valida.")
#             return

#     # --- MODALITÀ 2: SCANSIONE AUTOMATICA INTEGRALE ---
#     else:
#         id_gia_fatti = set()
#         if os.path.exists(FILE_OUTPUT_LIVE):
#             try:
#                 df_esistente = pd.read_csv(FILE_OUTPUT_LIVE)
#                 if "ID_Partita" in df_esistente.columns:
#                     id_gia_fatti = set(df_esistente["ID_Partita"].unique())
#             except Exception:
#                 pass

#         df_rimaste = df_calendario[
#             ~df_calendario["ID_Partita"].isin(id_gia_fatti)
#         ]
#         partite_da_fare = df_rimaste.to_dict(orient="records")

#     if not partite_da_fare:
#         print("\n✅ Nessuna partita da elaborare.")
#         return

#     # Inizializziamo lo scraper ufficiale del tuo PC
#     print("\n-> Connessione internet con Sofascore avviata...")
#     scraper = sfc.Sofascore()
#     lista_giocatori_totale = []

#     # 2. CICLO DI SCARICAMENTO REALE DA INTERNET
#     for i, riga in enumerate(partite_da_fare, 1):
#         match_id = int(riga["ID_Partita"])
#         casa = riga["Squadra_Casa"]
#         trasferta = riga["Squadra_Trasferta"]
#         giornata = riga.get("Giornata", 0)

#         print(
#             f"\n[{i}/{len(partite_da_fare)}] Scarico formazioni internet: {casa} vs {trasferta}..."
#         )

#         try:
#             # Chiamata internet stabile al tuo scraper funzionante
#             df_match_stats = scraper.scrape_player_match_stats(match_id)

#             if df_match_stats is not None and not df_match_stats.empty:
#                 df_match_stats = df_match_stats.loc[
#                     :, ~df_match_stats.columns.duplicated()
#                 ].copy()
#                 giocatori_lista = df_match_stats.to_dict(orient="records")

#                 for g in giocatori_lista:
#                     is_home = g.get("isHome", True)
#                     squadra_corrente = casa if bool(is_home) else trasferta
#                     ruolo_pulito = str(g.get("position", "N/D")).strip()

#                     # Recupero automatico del nome del giocatore
#                     nome_pulito = "Sconosciuto"
#                     if "player_name" in g and pd.notna(g["player_name"]):
#                         nome_pulito = str(g["player_name"])
#                     elif "name" in g and pd.notna(g["name"]):
#                         nome_pulito = str(g["name"])

#                     # Blocco statico pre-match per ripulire i dati del tempo futuro
#                     subentrato = g.get("substitute", False)
#                     stato_pulito = (
#                         "Panchina" if bool(subentrato) else "Titolare"
#                     )

#                     minuto_ingresso_pulito = 0
#                     minuti_giocati_pulito = 0
#                     voto_pulito = None

#                     lista_giocatori_totale.append(
#                         {
#                             "Giornata": giornata,
#                             "ID_Partita": int(match_id),
#                             "Squadra": squadra_corrente,
#                             "Giocatore": nome_pulito,
#                             "Ruolo": ruolo_pulito,
#                             "Stato": stato_pulito,
#                             "Minuto_Ingresso": minuto_ingresso_pulito,
#                             "Minuti_Giocati": minuti_giocati_pulito,
#                             "Voto": voto_pulito,
#                         }
#                     )
#                 print(
#                     f"   -> Estratte correttamente le formazioni live dal server."
#                 )
#             else:
#                 print(
#                     f"   -> Nota: Formazioni non ancora pubblicate online per il match {match_id}"
#                 )

#         except Exception as errore:
#             print(f"   -> Errore sul match {match_id}: {errore}")

#         time.sleep(2)

#     # 3. COMPILAZIONE E AGGIORNAMENTO DEL FILE GENERALE
#     if lista_giocatori_totale:
#         df_nuovi_dati = pd.DataFrame(lista_giocatori_totale)

#         if os.path.exists(FILE_OUTPUT_LIVE):
#             df_vecchio = pd.read_csv(FILE_OUTPUT_LIVE)
#             df_finale = pd.concat(
#                 [df_vecchio, df_nuovi_dati], ignore_index=True
#             )
#         else:
#             df_finale = df_nuovi_dati

#         # Sostituisce le vecchie righe (probabili) tenendo solo le ultime scaricate (ufficiali)
#         df_finale = df_finale.drop_duplicates(
#             subset=["ID_Partita", "Giocatore"], keep="last"
#         )

#         # Ordiniamo e salviamo sul computer
#         df_finale = df_finale.sort_values(
#             by=["Giornata", "ID_Partita"]
#         ).reset_index(drop=True)
#         df_finale.to_csv(FILE_OUTPUT_LIVE, index=False, encoding="utf-8")
#         print("\n=== AGGIORNAMENTO COMPLETATO CON SUCCESSO! ===")


# if __name__ == "__main__":
#     scarica_formazioni_live_pre_match()



# # CODICE DEFINITIVO PER SCARICARE LE FORMAZIONI LIVE PREPARTITA

# import os
# import time
# import warnings
# import pandas as pd
# import ScraperFC as sfc

# # Disattiviamo i messaggi di avviso gialli per tenere il terminale pulito
# warnings.filterwarnings("ignore", category=UserWarning)

# NOME_FILE_CALENDARIO = "banca_dati_partite_2526.csv"
# FILE_OUTPUT_LIVE = "banca_dati_formazioni_live.csv"


# def cerca_partita_nel_calendario(df_calendario):
#     """Cerca l'ID della partita nel calendario in modo intelligente e tollerante"""
#     print("\n--- 🔍 MOTORE DI RICERCA PARTITA (TOLLERANTE) ---")
#     scelta_squadra = (
#         input(
#             "Inserisci il nome di una squadra (es. inter, juve, sass, milan): "
#         )
#         .strip()
#         .lower()
#     )

#     if not scelta_squadra:
#         print("[ERRORE] Non hai inserito nessun testo.")
#         return None

#     # Filtro tollerante: cerca la stringa dentro Squadra_Casa o Squadra_Trasferta
#     match_trovati = df_calendario[
#         df_calendario["Squadra_Casa"].str.lower().str.contains(scelta_squadra)
#         | df_calendario["Squadra_Trasferta"]
#         .str.lower()
#         .str.contains(scelta_squadra)
#     ]

#     if match_trovati.empty:
#         print(f"❌ Nessuna partita trovato per: '{scelta_squadra}'")
#         return None

#     print(f"\n👍 Trovate {len(match_trovati)} corrispondenze nel calendario:")
#     opzioni = {}

#     for i, (_, riga) in enumerate(match_trovati.iterrows(), 1):
#         giornata = riga.get("Giornata", "N/D")
#         casa = riga["Squadra_Casa"]
#         trasferta = riga["Squadra_Trasferta"]
#         match_id = int(riga["ID_Partita"])

#         print(
#             f" [{i}] Giornata {giornata} | {casa} vs {trasferta} (ID: {match_id})"
#         )
#         opzioni[str(i)] = riga.to_dict()

#     if len(opzioni) == 1:
#         print("-> Selezionata automaticamente l'unica partita trovata.")
#         return opzioni["1"]

#     scelta_indice = (
#         input(
#             "\nInserisci il NUMERO della partita che vuoi scaricare (es. 1, 2): "
#         )
#         .strip()
#     )
#     return opzioni.get(scelta_indice, None)


# def scarica_formazioni_live_pre_match():
#     print("==========================================================================")
#     print("⚽ MOTORE DI SCARICAMENTO INTERNET: BANCA DATI FORMAZIONI LIVE ⚽")
#     print("==========================================================================")

#     # 1. Controllo del calendario locale delle partite
#     if not os.path.exists(NOME_FILE_CALENDARIO):
#         print(
#             f"[ERRORE] Manca il file '{NOME_FILE_CALENDARIO}' nella cartella."
#         )
#         return

#     df_calendario = pd.read_csv(NOME_FILE_CALENDARIO)

#     print("Seleziona la modalità operativa:")
#     print("1. Cerca una partita scrivendo il NOME DELLA SQUADRA (Pre-Match)")
#     print("2. Scansiona AUTOMATICAMENTE tutto il calendario per i match rimasti")
#     scelta_modalita = input("Inserisci il numero (1 o 2): ").strip()

#     partite_da_fare = []

#     # --- MODALITÀ 1: RICERCA INTELLIGENTE PER TESTO ---
#     if scelta_modalita == "1":
#         partita_scelta = cerca_partita_nel_calendario(df_calendario)
#         if partita_scelta:
#             partite_da_fare.append(partita_scelta)
#         else:
#             print("❌ Selezione annullata o non valida.")
#             return

#     # --- MODALITÀ 2: SCANSIONE AUTOMATICA INTEGRALE ---
#     else:
#         id_gia_fatti = set()
#         if os.path.exists(FILE_OUTPUT_LIVE):
#             try:
#                 df_esistente = pd.read_csv(FILE_OUTPUT_LIVE)
#                 if "ID_Partita" in df_esistente.columns:
#                     id_gia_fatti = set(df_esistente["ID_Partita"].unique())
#             except Exception:
#                 pass

#         df_rimaste = df_calendario[
#             ~df_calendario["ID_Partita"].isin(id_gia_fatti)
#         ]
#         partite_da_fare = df_rimaste.to_dict(orient="records")

#     if not partite_da_fare:
#         print("\n✅ Nessuna partita da elaborare.")
#         return

#     # Inizializziamo lo scraper ufficiale del tuo PC
#     print("\n-> Connessione internet con Sofascore avviata...")
#     scraper = sfc.Sofascore()
#     lista_giocatori_totale = []

#     # 2. CICLO DI SCARICAMENTO REALE DA INTERNET
#     for i, riga in enumerate(partite_da_fare, 1):
#         match_id = int(riga["ID_Partita"])
#         casa = riga["Squadra_Casa"]
#         trasferta = riga["Squadra_Trasferta"]
#         giornata = riga.get("Giornata", 0)

#         print(
#             f"\n[{i}/{len(partite_da_fare)}] Scarico formazioni internet: {casa} vs {trasferta}..."
#         )

#         try:
#             # Chiamata internet stabile al tuo scraper funzionante
#             df_match_stats = scraper.scrape_player_match_stats(match_id)

#             if df_match_stats is not None and not df_match_stats.empty:
#                 # Risolve l'avviso dei duplicati ripulendo le colonne duplicate
#                 df_match_stats = df_match_stats.loc[
#                     :, ~df_match_stats.columns.duplicated()
#                 ].copy()
#                 giocatori_lista = df_match_stats.to_dict(orient="records")

#                 for g in giocatori_lista:
#                     # --- FIX REALE E DEFINITIVO SU 'teamName' ---
#                     if "teamName" in g and pd.notna(g["teamName"]):
#                         squadra_corrente = str(g["teamName"])
#                     else:
#                         # Fallback se non trova teamName per qualche anomalia del server
#                         is_home = g.get("isHome", g.get("is_home", True))
#                         squadra_corrente = casa if bool(is_home) else trasferta
#                     # --------------------------------------------

#                     ruolo_pulito = str(g.get("position", "N/D")).strip()

#                     # Recupero automatico del nome del giocatore (usa 'name')
#                     nome_pulito = "Sconosciuto"
#                     if "name" in g and pd.notna(g["name"]):
#                         nome_pulito = str(g["name"])
#                     elif "player_name" in g and pd.notna(g["player_name"]):
#                         nome_pulito = str(g["player_name"])

#                     # CODICE DEFINITIVO PER SCARICARE LE FORMAZIONI LIVE PREPARTITA










import os
import time
import warnings
import pandas as pd
import ScraperFC as sfc

# Disattiviamo i messaggi di avviso gialli per tenere il terminale pulito
warnings.filterwarnings("ignore", category=UserWarning)

NOME_FILE_CALENDARIO = "banca_dati_calendario_2627.csv"
FILE_OUTPUT_LIVE = "banca_dati_formazioni_live.csv"


def cerca_partita_nel_calendario(df_calendario):
    """Cerca l'ID della partita nel calendario in modo intelligente e tollerante"""
    print("\n--- 🔍 MOTORE DI RICERCA PARTITA (TOLLERANTE) ---")
    scelta_squadra = (
        input(
            "Inserisci il nome di una squadra (es. inter, juve, sass, milan): "
        )
        .strip()
        .lower()
    )

    if not scelta_squadra:
        print("[ERRORE] Non hai inserito nessun testo.")
        return None

    # Filtro tollerante: cerca la stringa dentro Squadra_Casa o Squadra_Trasferta
    match_trovati = df_calendario[
        df_calendario["Squadra_Casa"].str.lower().str.contains(scelta_squadra)
        | df_calendario["Squadra_Trasferta"]
        .str.lower()
        .str.contains(scelta_squadra)
    ]

    if match_trovati.empty:
        print(f"❌ Nessuna partita trovato per: '{scelta_squadra}'")
        return None

    print(f"\n👍 Trovate {len(match_trovati)} corrispondenze nel calendario:")
    opzioni = {}

    for i, (_, riga) in enumerate(match_trovati.iterrows(), 1):
        giornata = riga.get("Giornata", "N/D")
        casa = riga["Squadra_Casa"]
        trasferta = riga["Squadra_Trasferta"]
        match_id = int(riga["ID_Partita"])

        print(
            f" [{i}] Giornata {giornata} | {casa} vs {trasferta} (ID: {match_id})"
        )
        opzioni[str(i)] = riga.to_dict()

    if len(opzioni) == 1:
        print("-> Selezionata automaticamente l'unica partita trovata.")
        return opzioni["1"]

    scelta_indice = (
        input(
            "\nInserisci il NUMERO della partita che vuoi scaricare (es. 1, 2): "
        )
        .strip()
    )
    return opzioni.get(scelta_indice, None)
def scarica_formazioni_live_pre_match():
    print("==========================================================================")
    print("⚽ MOTORE DI SCARICAMENTO INTERNET: BANCA DATI FORMAZIONI LIVE ⚽")
    print("==========================================================================")

    # 1. Controllo del calendario locale delle partite
    if not os.path.exists(NOME_FILE_CALENDARIO):
        print(
            f"[ERRORE] Manca il file '{NOME_FILE_CALENDARIO}' nella cartella."
        )
        return

    df_calendario = pd.read_csv(NOME_FILE_CALENDARIO)

    print("Seleziona la modalità operativa:")
    print("1. Cerca una partita scrivendo il NOME DELLA SQUADRA (Pre-Match)")
    print("2. Scansiona AUTOMATICAMENTE tutto il calendario per i match rimasti")
    scelta_modalita = input("Inserisci il numero (1 o 2): ").strip()

    partite_da_fare = []

    # --- MODALITÀ 1: RICERCA INTELLIGENTE PER TESTO ---
    if scelta_modalita == "1":
        partita_scelta = cerca_partita_nel_calendario(df_calendario)
        if partita_scelta:
            partite_da_fare.append(partita_scelta)
        else:
            print("❌ Selezione annullata o non valida.")
            return

    # --- MODALITÀ 2: SCANSIONE AUTOMATICA INTEGRALE ---
    else:
        id_gia_fatti = set()
        if os.path.exists(FILE_OUTPUT_LIVE):
            try:
                df_esistente = pd.read_csv(FILE_OUTPUT_LIVE)
                if "ID_Partita" in df_esistente.columns:
                    id_gia_fatti = set(df_esistente["ID_Partita"].unique())
            except Exception:
                pass

        df_rimaste = df_calendario[
            ~df_calendario["ID_Partita"].isin(id_gia_fatti)
        ]
        partite_da_fare = df_rimaste.to_dict(orient="records")

    if not partite_da_fare:
        print("\n✅ Nessuna partita da elaborare.")
        return

    # Inizializziamo lo scraper ufficiale del tuo PC
    print("\n-> Connessione internet con Sofascore avviata...")
    scraper = sfc.Sofascore()
    lista_giocatori_totale = []

    # 🛡️ CONTATORE DI SICUREZZA ANTI-CICLO A VUOTO
    errori_consecutivi = 0

    # 2. CICLO DI SCARICAMENTO REALE DA INTERNET
    for i, riga in enumerate(partite_da_fare, 1):
        match_id = int(riga["ID_Partita"])
        casa = riga["Squadra_Casa"]
        trasferta = riga["Squadra_Trasferta"]
        giornata = riga.get("Giornata", 0)

        print(
            f"\n[{i}/{len(partite_da_fare)}] Scarico formazioni internet: {casa} vs {trasferta}..."
        )

        try:
            # Chiamata internet stabile al tuo scraper funzionante
            df_match_stats = scraper.scrape_player_match_stats(match_id)

            if df_match_stats is not None and not df_match_stats.empty:
                # Se scarica con successo, azzeriamo il contatore degli errori consecutivi
                errori_consecutivi = 0
                
                # Risolve l'avviso dei duplicati ripulendo le colonne duplicate
                df_match_stats = df_match_stats.loc[
                    :, ~df_match_stats.columns.duplicated()
                ].copy()
                giocatori_lista = df_match_stats.to_dict(orient="records")

                for g in giocatori_lista:
                    # --- FIX REALE E DEFINITIVO SU 'teamName' ---
                    if "teamName" in g and pd.notna(g["teamName"]):
                        squadra_corrente = str(g["teamName"])
                    else:
                        # Fallback se non trova teamName per qualche anomalia del server
                        is_home = g.get("isHome", g.get("is_home", True))
                        squadra_corrente = casa if bool(is_home) else trasferta
                    # --------------------------------------------

                    # --- 🧠 TRADUTTORE RIGIDO RUOLI PER COMPATIBILITÀ BANCA DATI ---
                    ruolo_raw = str(g.get("position", "N/D")).strip().lower()
                    if ruolo_raw in ['por', 'p', 'gk', 'goalkeeper']:
                        ruolo_pulito = 'G'
                    elif ruolo_raw in ['dif', 'd', 'dc', 'td', 'ts', 'defender']:
                        ruolo_pulito = 'D'
                    elif ruolo_raw in ['cen', 'cc', 'm', 'cdc', 'midfielder']:
                        ruolo_pulito = 'M'
                    elif ruolo_raw in ['att', 'a', 'f', 'pc', 'forward']:
                        ruolo_pulito = 'F'
                    else:
                        ruolo_pulito = ruolo_raw.upper()
                    # ------------------------------------------------------------

                    # Recupero automatico del nome del giocatore (usa 'name')
                    nome_pulito = "Sconosciuto"
                    if "name" in g and pd.notna(g["name"]):
                        nome_pulito = str(g["name"])
                    elif "player_name" in g and pd.notna(g["player_name"]):
                        nome_pulito = str(g["player_name"])

                    # Blocco statico pre-match per azzerare i contatori del tempo futuro
                    subentrato = g.get("substitute", False)
                    stato_pulito = "Panchina" if bool(subentrato) else "Titolare"

                    minuto_ingresso_pulito = 0
                    minuti_giocati_pulito = 0
                    voto_pulito = ""

                    lista_giocatori_totale.append(
                        {
                            "Giornata": giornata,
                            "ID_Partita": int(match_id),
                            "Squadra": squadra_corrente,
                            "Giocatore": nome_pulito,
                            "Ruolo": ruolo_pulito,
                            "Stato": stato_pulito,
                            "Minuto_Ingresso": minuto_ingresso_pulito,
                            "Minuti_Giocati": minuti_giocati_pulito,
                            "Voto": voto_pulito,
                        }
                    )

                print(f"   -> Estratte correttamente le formazioni live dal server.")
            else:
                # Incrementiamo se il server risponde vuoto (formazioni non pronte)
                errori_consecutivi += 1
                print(f"   -> Nota: Formazioni non ancora pubblicate online per il match {match_id}")

        except Exception as errore:
            # Incrementiamo anche in caso di errore di connessione/chiamata fallita
            errori_consecutivi += 1
            print(f"   -> Errore sul match {match_id}: {errore}")

        # 🚨 BLOCCO INTERRUZIONE AUTOMATICA SE CI SONO 3 ERRORI CONSECUTIVI
        if errori_consecutivi >= 3:
            print("\n==========================================================================")
            print("🛑 STOP AUTOMATICO: Rilevati 3 match consecutivi senza formazioni online.")
            print("I server non sono ancora aggiornati. Interrompo il ciclo per evitare spam.")
            print("==========================================================================")
            break

        time.sleep(2)
    # 3. COMPILAZIONE E AGGIORNAMENTO DEL FILE GENERALE INCREMENTALE
    if lista_giocatori_totale:
        df_nuovi_dati = pd.DataFrame(lista_giocatori_totale)

        if os.path.exists(FILE_OUTPUT_LIVE):
            try:
                df_vecchio = pd.read_csv(FILE_OUTPUT_LIVE)
                if df_vecchio.empty:
                    df_finale = df_nuovi_dati
                else:
                    df_finale = pd.concat([df_vecchio, df_nuovi_dati], ignore_index=True)
            except pd.errors.EmptyDataError:
                df_finale = df_nuovi_dati
        else:
            df_finale = df_nuovi_dati

        df_finale = df_finale.drop_duplicates(subset=["ID_Partita", "Giocatore"], keep="last")
        df_finale.to_csv(FILE_OUTPUT_LIVE, index=False, encoding="utf-8")
        
        print(f"\n==========================================================================")
        print(f"🎉 BANCA DATI FORMAZIONI LIVE AGGIORNATA! File: '{FILE_OUTPUT_LIVE}' ({len(df_finale)} righe totali).")
        print(f"==========================================================================")


if __name__ == "__main__":
    scarica_formazioni_live_pre_match()
