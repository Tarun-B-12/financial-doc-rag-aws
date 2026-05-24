import os
import re
import boto3
import json
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("AWS_BUCKET_NAME")
REGION = os.getenv("AWS_REGION")

s3 = boto3.client("s3", region_name=REGION)

def download_from_s3(s3_key: str, local_path: str):
    """Download a file from S3 to local path."""
    print(f"Downloading {s3_key} from S3...")
    s3.download_file(BUCKET, s3_key, local_path)
    print(f"Downloaded to {local_path}")

def extract_text_from_htm(filepath: str) -> str:
    """Extract clean text from HTM/HTML financial filing."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Remove script and style blocks
    content = re.sub(r'<script[^>]*>.*?</script>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<style[^>]*>.*?</style>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Replace block tags with newlines
    content = re.sub(r'<(p|div|tr|li|h[1-6]|br)[^>]*>', '\n', content, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    content = re.sub(r'<[^>]+>', ' ', content)
    
    # Decode common HTML entities
    content = content.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    content = content.replace('&nbsp;', ' ').replace('&#160;', ' ').replace('&quot;', '"')
    
    # Clean up whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r' {2,}', ' ', content)
    content = '\n'.join(line.strip() for line in content.splitlines() if line.strip())
    
    return content

def chunk_text(text: str, company: str, filename: str, 
               chunk_size: int = 800, overlap: int = 100) -> list:
    """Split text into overlapping chunks with metadata."""
    words = text.split()
    chunks = []
    
    start = 0
    chunk_id = 0
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words)
        
        # Skip chunks that are too short to be meaningful
        if len(chunk_words) > 50:
            chunks.append({
                "chunk_id": f"{filename}_{chunk_id}",
                "company": company,
                "source_file": filename,
                "chunk_index": chunk_id,
                "text": chunk_text,
                "word_count": len(chunk_words)
            })
            chunk_id += 1
        
        start += chunk_size - overlap
    
    return chunks

DOCUMENTS = [
    {"s3_key": "documents/jpmorgan_10k.htm", "filename": "jpmorgan_10k.htm", "company": "JPMorgan Chase"},
    {"s3_key": "documents/goldman_10k.htm",  "filename": "goldman_10k.htm",  "company": "Goldman Sachs"},
    {"s3_key": "documents/apple_10k.htm",    "filename": "apple_10k.htm",    "company": "Apple"},
]

def process_all_documents():
    """Download, extract, chunk, and save all documents."""
    all_chunks = []
    
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    for doc in DOCUMENTS:
        local_path = f"data/raw/{doc['filename']}"
        
        # Download from S3 if not already local
        if not os.path.exists(local_path):
            download_from_s3(doc["s3_key"], local_path)
        
        print(f"Extracting text from {doc['company']}...")
        text = extract_text_from_htm(local_path)
        print(f"Extracted {len(text):,} characters, {len(text.split()):,} words")
        
        print(f"Chunking {doc['company']}...")
        chunks = chunk_text(text, doc["company"], doc["filename"])
        print(f"Created {len(chunks):,} chunks")
        
        # Save processed text
        processed_path = f"data/processed/{doc['filename'].replace('.htm', '.txt')}"
        with open(processed_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        all_chunks.extend(chunks)
        print()
    
    # Save all chunks to JSON
    chunks_path = "data/processed/all_chunks.json"
    with open(chunks_path, "w") as f:
        json.dump(all_chunks, f, indent=2)
    
    print(f"Total chunks across all documents: {len(all_chunks):,}")
    print(f"Chunks saved to {chunks_path}")
    
    return all_chunks

if __name__ == "__main__":
    chunks = process_all_documents()
    
    # Show sample chunk
    print("\nSample chunk:")
    print(f"Company: {chunks[10]['company']}")
    print(f"Chunk ID: {chunks[10]['chunk_id']}")
    print(f"Text preview: {chunks[10]['text'][:300]}...")
