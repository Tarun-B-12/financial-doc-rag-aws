import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def generate_answer(question: str, retrieved_chunks: list) -> dict:
    """Generate a grounded answer from retrieved chunks using Claude Haiku."""
    
    if not retrieved_chunks:
        return {
            "answer": "No relevant documents found to answer this question.",
            "sources": [],
            "grounded": False
        }
    
    # Build context from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks):
        context_parts.append(
            f"[Source {i+1}: {chunk['metadata']['company']} 10-K Filing]\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)
    
    prompt = f"""You are a financial document analyst. Answer the question below using ONLY the provided source documents.

Rules:
1. Only use information explicitly stated in the sources
2. Always cite which source (Source 1, Source 2, etc.) your answer comes from
3. If the sources do not contain enough information to answer the question, say exactly: "The provided documents do not contain sufficient information to answer this question."
4. Never make up numbers, dates, or facts not in the sources
5. Be concise and precise

Source Documents:
{context}

Question: {question}

Answer:"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    
    answer = response.content[0].text
    
    # Check if answer is grounded or not found
    not_found_phrase = "do not contain sufficient information"
    grounded = not_found_phrase not in answer.lower()
    
    # Build source citations
    sources = []
    for i, chunk in enumerate(retrieved_chunks):
        sources.append({
            "source_num": i + 1,
            "company": chunk["metadata"]["company"],
            "file": chunk["metadata"]["source_file"],
            "similarity": chunk["similarity"]
        })
    
    return {
        "answer": answer,
        "sources": sources,
        "grounded": grounded
    }

if __name__ == "__main__":
    # Test with sample retrieved chunks
    from vectorstore import query_vectorstore
    
    test_questions = [
        "What are JPMorgan's primary risk management principles?",
        "What is Apple's revenue recognition policy?",
        "What were Goldman Sachs net revenues?",
        "What is the weather like in Dallas?"  # Should trigger not-found response
    ]
    
    for question in test_questions:
        print(f"\nQ: {question}")
        print("-" * 60)
        
        chunks = query_vectorstore(question, n_results=4)
        result = generate_answer(question, chunks)
        
        print(f"Grounded: {result['grounded']}")
        print(f"Answer: {result['answer'][:400]}...")
        print(f"Sources: {[s['company'] for s in result['sources']]}")
