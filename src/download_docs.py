import requests
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("AWS_BUCKET_NAME")
REGION = os.getenv("AWS_REGION")

s3 = boto3.client("s3", region_name=REGION)

HEADERS = {"User-Agent": "Tarun Portfolio Project buildwithtarun@gmail.com"}

def get_latest_10k_url(cik: str, company: str):
    """Find the latest 10-K filing URL from SEC EDGAR API."""
    cik_padded = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    
    print(f"Looking up {company} filings...")
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Failed to get filings for {company}")
        return None
    
    data = response.json()
    filings = data.get("filings", {}).get("recent", {})
    
    forms = filings.get("form", [])
    accession_numbers = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])
    
    for i, form in enumerate(forms):
        if form == "10-K":
            accession = accession_numbers[i].replace("-", "")
            primary_doc = primary_docs[i]
            pdf_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_doc}"
            print(f"Found 10-K for {company}: {pdf_url}")
            return pdf_url
    
    print(f"No 10-K found for {company}")
    return None

def download_and_upload(cik: str, company: str, filename: str):
    url = get_latest_10k_url(cik, company)
    if not url:
        return
    
    print(f"Downloading {company}...")
    response = requests.get(url, headers=HEADERS, timeout=120)
    
    if response.status_code == 200:
        local_path = f"data/raw/{filename}"
        with open(local_path, "wb") as f:
            f.write(response.content)
        size_mb = len(response.content) / 1024 / 1024
        print(f"Saved locally: {local_path} ({size_mb:.1f} MB)")
        
        s3.upload_file(local_path, BUCKET, f"documents/{filename}")
        print(f"Uploaded to S3: s3://{BUCKET}/documents/{filename}")
    else:
        print(f"Failed to download {company}: HTTP {response.status_code}")

COMPANIES = [
    {"cik": "19617",  "company": "JPMorgan Chase", "filename": "jpmorgan_10k.htm"},
    {"cik": "886982", "company": "Goldman Sachs",  "filename": "goldman_10k.htm"},
    {"cik": "320193", "company": "Apple",          "filename": "apple_10k.htm"},
]

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    
    for doc in COMPANIES:
        download_and_upload(doc["cik"], doc["company"], doc["filename"])
        print()
    
    print("Files in S3 bucket:")
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix="documents/")
    for obj in response.get("Contents", []):
        size_mb = obj["Size"] / 1024 / 1024
        print(f"  {obj['Key']} ({size_mb:.1f} MB)")
