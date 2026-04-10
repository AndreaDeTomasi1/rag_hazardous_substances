import chromadb
from chromadb.config import Settings
from bs4 import BeautifulSoup
from pathlib import Path
import re
from sentence_transformers import SentenceTransformer

# -------- EMBEDDING MODEL --------
embedding_model = SentenceTransformer(
    "intfloat/e5-base",
    device="cpu"
)

# ------------------ CLIENT CON PERSISTENZA ------------------
chroma_client = chromadb.PersistentClient(
    path="chroma_db",
    settings=Settings()
)

collection_name = "2_schedeICSC"

existing = [c.name for c in chroma_client.list_collections()]
collection = chroma_client.get_collection(collection_name) \
    if collection_name in existing \
    else chroma_client.create_collection(name=collection_name)


# ------------------ UTILS ------------------
def embed_passages(texts):
    texts = [f"passage: {t}" for t in texts]
    return embedding_model.encode(
        texts,
        normalize_embeddings=True
    ).tolist()

def clean_text(text):
    """Normalizza whitespace"""
    return " ".join(text.split())

def remove_substance_name(text, nome):
    if not nome:
        return text
    nome_escaped = re.escape(nome)
    # rimuove il nome come parola intera, case-insensitive
    pattern = rf"\b{nome_escaped}\b"
    cleaned = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return cleaned

def chunk_text(text, max_chars=1200, overlap=150):
    """
    Chunk semplice ma efficace.
    ~1200 char ≈ 300 token.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start += max_chars - overlap

    return chunks

def parse_matrix_table(table):
    rows = []
    row_lengths = []  # Lista per memorizzare il numero di celle per riga

    for row in table.find_all("tr", recursive=False):
        cells = []

        for c in row.find_all("td", recursive=False):
            # Prende il testo separando i <br> con \n
            raw_text = c.get_text(separator="\n", strip=True)
            
            # Aggiunge uno spazio davanti a ogni riga che era preceduta da <br>
            lines = raw_text.split("\n")
            spaced_lines = [(" " + line if i > 0 else line) for i, line in enumerate(lines)]
            
            # Unisce le linee della cella con uno spazio
            cell_text = " ".join(spaced_lines)

            # Normalizza spazi multipli
            cell_text = clean_text(cell_text)
            cells.append(cell_text)

        if cells:
            rows.append(" | ".join(cells))
            row_lengths.append(len(cells))  # Salva il numero di celle nella riga

    return "\n".join(rows), row_lengths

# ------------------ PARSER MIGLIORATO ------------------

def parse_icsc_semantic(html_text):
    soup = BeautifulSoup(html_text, "html.parser")

    # rimuove rumore
    for tag in soup(["script", "style"]):
        tag.decompose()

    # ---- Nome sostanza ----
    nome_tag = soup.find("font", size="3")
    nome = nome_tag.get_text(strip=True) if nome_tag else None

    if not nome:
        b_tag = soup.find("b")
        nome = b_tag.get_text(strip=True) if b_tag else "Sostanza sconosciuta"

    sections = []
    rows = []
    tables = [t for t in soup.find_all("table") if not t.find_parent("table")]

    for table in tables:
        body, row_lengths = parse_matrix_table(table)
        if body:
            body = remove_substance_name(body, nome)
            sections.append(f"Sostanza: {nome}\n{body}")
            rows.append(row_lengths)

    # fallback rarissimo
    if not sections:
        full = clean_text(soup.get_text(" ", strip=True))
        sections = [f"Sostanza: {nome}\n{c}" for c in chunk_text(full)]

    return nome, sections, rows


# ------------------ PROCESSA FILE ------------------

docs = []
metadatas = []
ids = []

icsc_dir = Path("../SchedeICSC")
html_files = list(icsc_dir.glob("*.HTM"))

print(len(html_files), "file ICSC trovati.")
total_chunks = 0

for html_path in html_files:
    print("Processing:", html_path.name)

    html_text = html_path.read_text(encoding="cp1252", errors="ignore")
    nome, chunks, rows = parse_icsc_semantic(html_text)

    merged_chunks = []
    merged_rows = []

    # logica di merge basata su row_length
    current_chunk = chunks[0]
    current_rows = rows[0]
    current_id = 1

    for i in range(1, len(chunks)):
        if all(x == current_rows[0] for x in current_rows):
            check_row = current_rows[0]
        else:
            check_row = 0
        # confronta row_length
        if all(x == rows[i][0] for x in rows[i]) and check_row == rows[i][0]:
            # accorpa chunk con \n
            current_chunk += "\n" + chunks[i]
        else:
            # salva il chunk accumulato
            merged_chunks.append(current_chunk)
            merged_rows.append(current_rows)

            # reset
            current_chunk = chunks[i]
            current_rows = rows[i]
            current_id = i + 1  # aggiorna ID

    # salva l’ultimo chunk
    merged_chunks.append(current_chunk)
    merged_rows.append(current_rows)

    embeddings = embed_passages(merged_chunks)
    for i, (chunk, embedding) in enumerate(zip(merged_chunks, embeddings)):

        collection.upsert(
            documents=[chunk],
            embeddings=[embedding],
            metadatas=[{
                "sostanza": nome,
                "fonte": "ICSC",
                "file": html_path.name
            }],
            ids=[f"{html_path.stem}_{i}"]   # ⚠️ meglio deterministico
        )

        total_chunks += 1

print(f"✅ Salvati {total_chunks} chunk.")