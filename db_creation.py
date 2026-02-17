import chromadb
from chromadb.config import Settings
from bs4 import BeautifulSoup
from pathlib import Path

# ------------------ CLIENT CON PERSISTENZA ------------------
# PersistentClient salva automaticamente i dati su disco
chroma_client = chromadb.PersistentClient(
    path="chroma_db",  # cartella dove verranno salvati i dati
    settings=Settings()  # le impostazioni possono restare di default
)

collection_name = "schedeICSC"
# Recupera o crea la collection
collection = chroma_client.get_collection(name=collection_name) if \
    collection_name in [c.name for c in chroma_client.list_collections()] \
    else chroma_client.create_collection(name=collection_name)

# ------------------ FUNZIONE DI PARSING ------------------
def parse_icsc_simple(html_text):
    soup = BeautifulSoup(html_text, "html.parser")

    nome_tag = soup.find("font", size="3")
    if nome_tag:
        nome_sostanza = nome_tag.get_text(strip=True)
    else:
        b_tag = soup.find("b")
        nome_sostanza = b_tag.get_text(strip=True) if b_tag else None

    full_text = soup.get_text(" ", strip=True)
    if nome_sostanza:
        full_text = full_text.replace(nome_sostanza, "", 1).strip()

    return {
        "nome": nome_sostanza,
        "documento": full_text
    }

# ------------------ PROCESSA FILE E INSERISCI ------------------
docs = []
metadatas = []
ids = []

icsc_dir = Path("../SchedeICSC")
html_files = list(icsc_dir.glob("*.HTM"))
print(len(html_files), "file ICSC trovati.")

for html_path in html_files:
    print("Processing:", html_path.name)
    html_text = html_path.read_text(encoding="cp1252", errors="ignore")
    parsed = parse_icsc_simple(html_text)

    doc_content = parsed["documento"]
    nome_sostanza = parsed["nome"]

    if doc_content:
        docs.append(doc_content)
        metadatas.append({
            "sostanza": nome_sostanza,
            "fonte": "ICSC",
            "file": html_path.name
        })
        ids.append(html_path.stem)
    else:
        print(f"⚠️ Documento vuoto per {html_path.name}")

# ------------------ INSERIMENTO ------------------
if docs:
    collection.upsert(
        documents=docs,
        metadatas=metadatas,
        ids=ids
    )
    print("✅ Documenti salvati nella collection con persistenza.")
else:
    print("⚠️ Nessun documento da inserire (docs vuoto)")
