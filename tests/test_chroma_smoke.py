# tests/test_chroma_smoke.py
from sentence_transformers import SentenceTransformer
import chromadb

def test_multilingual_embedding_and_retrieval():
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    client = chromadb.Client()
    collection = client.create_collection("smoke_test")

    # Documento en polaco
    doc_pl = "Poproszę o kawę z mlekiem."
    embedding = model.encode(doc_pl).tolist()

    collection.add(
        embeddings=[embedding],
        documents=[doc_pl],
        metadatas=[{"nivel": "A2", "idioma": "pl"}],
        ids=["doc1"]
    )

    # Consulta en español — debe encontrar el documento en polaco por significado
    query = "cómo pedir un café"
    query_embedding = model.encode(query).tolist()

    results = collection.query(query_embeddings=[query_embedding], n_results=1)

    assert len(results["documents"][0]) == 1
    print(f"Query ES encontró: {results['documents'][0][0]}")
    print(f"Distancia: {results['distances'][0][0]}")