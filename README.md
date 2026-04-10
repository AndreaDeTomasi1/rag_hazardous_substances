# 🧪 RAG ICSC Chatbot

Questo progetto implementa un'architettura **Retrieval-Augmented Generation (RAG)** per interrogare le **schede pubbliche ICSC (International Chemical Safety Cards)**, consentendo agli utenti di ottenere informazioni sulla sicurezza chimica tramite un chatbot interattivo.

Le schede ICSC sono pubblicamente disponibili al seguente link:  
🔗 https://chemicalsafety.ilo.org/dyn/icsc/showcard.listCards3?p_lang=it

---

## 📌 Obiettivo del Progetto

L'obiettivo è costruire un sistema che:

- 📚 **Indicizzi** le schede ICSC in lingua italiana.
- 🔍 **Recuperi** le informazioni più rilevanti tramite ricerca semantica.
- 🤖 **Generi risposte contestualizzate** utilizzando un modello di linguaggio.
- 💬 **Permetta l’interazione** con gli utenti attraverso un’interfaccia web.
- 📝 **Registri le conversazioni** per analisi e miglioramento del sistema.

---

## 🏗️ Architettura RAG

Il sistema segue la classica pipeline RAG:

1. **Ingestion** – Download e parsing delle schede ICSC.
2. **Chunking** – Suddivisione dei documenti in segmenti semantici.
3. **Embedding** – Trasformazione dei chunk in vettori numerici.
4. **Vector Store** – Memorizzazione degli embedding in ChromaDB.
5. **Retrieval** – Recupero dei documenti più rilevanti rispetto alla query.
6. **Generation** – Generazione della risposta tramite un LLM.
7. **Interfaccia Utente** – Chatbot sviluppato con Streamlit.
8. **Logging** – Salvataggio delle conversazioni in un file CSV.

---

## 📁 Struttura del Progetto

```text
.
├── chroma_db/            # Directory contenente il database vettoriale ChromaDB
├── db_creation.py        # Script per la creazione iniziale del database
├── 2_db_creation.py      # Versione migliorata con chunking ottimizzato dei file HTML
├── chatbot_app.py        # Applicazione Streamlit per il chatbot RAG
├── chat_log.csv          # File CSV per il salvataggio dei log delle conversazioni
└── README.md             # Documentazione del progetto
```

## 🤖 Modelli LLM tramite OpenRouter

Questo progetto utilizza **OpenRouter** per l’accesso ai modelli di linguaggio (LLM) e di embedding. OpenRouter fornisce un’interfaccia unificata che consente di integrare facilmente modelli provenienti da diversi provider (come OpenAI, Anthropic, Meta, Google e altri) utilizzando una singola API.

### 🔗 Cos'è OpenRouter?

**OpenRouter** è una piattaforma che permette di:
- Accedere a molteplici modelli LLM tramite un'unica API.
- Semplificare il cambio di modello senza modificare significativamente il codice.
- Ottimizzare costi e prestazioni scegliendo il modello più adatto al caso d’uso.
- Garantire maggiore flessibilità e scalabilità dell’architettura RAG.

Per maggiori informazioni, visita il sito ufficiale:  
👉 https://openrouter.ai/
