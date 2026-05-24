import os
import json
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = "chroma_db"

def get_embedding_function():
    """Use sentence-transformers for embeddings (free, runs locally)."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

def get_collection():
    """Get or create the ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = get_embedding_function()
    collection = client.get_or_create_collection(
        name="financial_docs",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )
    return collection

def build_vectorstore(chunks_path: str = "data/processed/all_chunks.json"):
    """Embed all chunks and store in ChromaDB."""
    print("Loading chunks...")
    with open(chunks_path, "r") as f:
        chunks = json.load(f)
    
    print(f"Loaded {len(chunks):,} chunks")
    
    collection = get_collection()
    
    # Check if already populated
    existing = collection.count()
    if existing > 0:
        print(f"Vector store already has {existing:,} documents. Skipping rebuild.")
        print("Delete chroma_db/ folder to rebuild from scratch.")
        return collection
    
    print("Building vector store (this takes 2-3 minutes)...")
    
    # Add in batches of 100
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        ids = [c["chunk_id"] for c in batch]
        documents = [c["text"] for c in batch]
        metadatas = [
            {
                "company": c["company"],
                "source_file": c["source_file"],
                "chunk_index": c["chunk_index"],
                "word_count": c["word_count"]
            }
            for c in batch
        ]
        
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"  Indexed {min(i + batch_size, len(chunks))}/{len(chunks)} chunks...")
    
    print(f"\nVector store built. Total documents indexed: {collection.count():,}")
    return collection

def query_vectorstore(question: str, n_results: int = 5, company_filter: str = None):
    """Search the vector store for relevant chunks."""
    collection = get_collection()
    
    where = {"company": company_filter} if company_filter else None
    
    results = collection.query(
        query_texts=[question],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"]
    )
    
    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "similarity": round(1 - results["distances"][0][i], 4)
        })
    
    return chunks

if __name__ == "__main__":
    collection = build_vectorstore()
    
    print("\nTest query: 'What are the primary risk factors?'")
    results = query_vectorstore("What are the primary risk factors?", n_results=3)
    
    for i, r in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Company: {r['metadata']['company']}")
        print(f"  Similarity: {r['similarity']}")
        print(f"  Preview: {r['text'][:200]}...")
