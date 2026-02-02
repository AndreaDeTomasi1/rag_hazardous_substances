import streamlit as st
import chromadb
from chromadb.config import Settings
import requests
import csv
import os
import re
from datetime import datetime

# ------------------ APRI IL DB PERSISTENTE ------------------
chroma_client = chromadb.PersistentClient(
    path="chroma_db",
    settings=Settings()
)

# ------------------ RECUPERA LA COLLECTION ------------------
collection_name = "schedeICSC"
collection = chroma_client.get_collection(collection_name)

# ------------------ ESTRAI LISTA SOSTANZE DAL DB ------------------
# Otteniamo tutti i metadati e ne ricaviamo le sostanze uniche
all_metadatas = collection.get(include=["metadatas"])["metadatas"]
sostanze = sorted(list({m["sostanza"] for m in all_metadatas if "sostanza" in m}))

# ------------------ STREAMLIT ------------------
st.title("💬 Chatbot Chimico con filtro per sostanza")

# Multi-selezione sostanze (l'utente può scegliere più di una)
with st.container():
    st.subheader("Selezione sostanze")
    selected_substances = st.multiselect(
        "Scegli una o più sostanze:",
        sostanze,
        placeholder="Es. ACETONE, ETANOLO, AMMONIACA..."
    )

st.divider()

# ------------------ FUNZIONE DI PULIZIA PER CSV ------------------
def sanitize_for_csv(text: str) -> str:
    if not text:
        return ""

    # rimuove a capo (\n, \r)
    text = text.replace("\n", " ").replace("\r", " ")

    # sostituisce le virgole
    text = text.replace(",", " ")

    # normalizza spazi multipli
    text = re.sub(r"\s+", " ", text)

    return text.strip()

# ------------------ FUNZIONE DI CHATBOT CON RETRIEVAL ------------------
def chatbot_response(query):
    # Recupera documenti simili dalla collection
    # Se trovi un materiale, lo usi come filtro sui metadati
    if selected_substances:
        all_docs = []
        all_metas = []
        for s in selected_substances:
            results = collection.query(
                query_texts=[query],
                n_results=3,
                include=["documents", "metadatas"],
                where={"sostanza": s}  # filtro per sostanza
            )
            all_docs.extend(results["documents"][0])
            all_metas.extend(results["metadatas"][0])
    else:
        results = collection.query(
            query_texts=[query],
            n_results=3,
            include=["documents", "metadatas"]
        )
        all_docs = results["documents"][0]
        all_metas = results["metadatas"][0]

    if not all_docs:
        return "Non ho trovato informazioni rilevanti nei documenti."

    # Concateno i documenti per dare contesto al modello
    docs_with_meta = []
    for doc, meta in zip(all_docs, all_metas):
        sostanza = meta.get("sostanza", "Sostanza non specificata")
        file_name = meta.get('file', 'File non specificato')
        docs_with_meta.append(
            f"[SOSTANZA: {sostanza}, FILE: {file_name}]\n{doc}"
        )
    context = "\n\n".join(docs_with_meta)
    # Prepara i messaggi per Hugging Face
    messages = [
        {"role": "system", "content": "Sei un esperto di sicurezza chimica e schede ICSC."},
        {"role": "user", "content": f"Usando questi documenti:\n{context}\n\nRispondi a: {query}, indicando anche il file in cui ritrovi le informazioni. Usa frasi prese dai documenti."}
    ]

    data = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }

    # Chiamata all'API Open Router
    HF_API_TOKEN = os.getenv("HF_API_TOKEN")
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}", "Content-Type": "application/json"}
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        answer = response.json()["choices"][0]["message"]["content"]
        retrieved_files = [meta.get("file", []) for meta in all_metas] if all_metas else []
        return answer, retrieved_files
    else:
        return f"Errore nella chiamata al modello: {response.status_code}, {response.text}", []

# ------------------ FUNZIONE DI LOGGING ------------------
def log_chat_to_csv(selected_substances, question, answer, retrieved_files):
    file_exists = os.path.isfile(CSV_LOG_PATH)

    with open(CSV_LOG_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # header solo se il file non esiste
        if not file_exists:
            writer.writerow([
                "timestamp",
                "selected_substances",
                "question",
                "answer",
                "retrieved_files"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ";".join(selected_substances) if selected_substances else "",
            sanitize_for_csv(question),
            sanitize_for_csv(answer),
            ";".join(retrieved_files) if retrieved_files else ""
        ])

# ------------------ STREAMLIT ------------------
CSV_LOG_PATH = "chat_log.csv"

with st.container():
    st.subheader("Chatbot")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    def send_message():
        query = st.session_state.user_input
        if query:
            st.session_state.chat_history.append(f"Tu: {query}")
            # Ottieni la risposta tramite retrieval + LLM
            response, retrieved_files = chatbot_response(query)
            st.session_state.chat_history.append(f"Bot: {response}")
            log_chat_to_csv(selected_substances, query, response, retrieved_files)
            st.session_state.user_input = ""

    st.text_input("Scrivi qui il tuo messaggio:", key="user_input", on_change=send_message)

    # Mostra la cronologia
    for msg in st.session_state.chat_history:
        if msg.startswith("Tu:"):
            st.markdown(f"<div style='color: blue'>{msg}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: green'>{msg}</div>", unsafe_allow_html=True)
