import os
import sys
import argparse
import pandas as pd
import requests
import time
import re
import pdfplumber

# ---------------- Paths ----------------
def get_paths(bank: str):
    data_dir = os.path.join("data", bank.lower())
    pdf_file = os.path.join(data_dir, f"{bank.lower()}_sample.pdf")
    csv_file = os.path.join(data_dir, "result.csv")
    output_csv = os.path.join(data_dir, "parsed_output.csv")
    parser_file = os.path.join("custom_parsers", f"{bank.lower()}_parser.py")
    return data_dir, pdf_file, csv_file, output_csv, parser_file

# ---------------- Groq API ----------------
GROQ_API_URL_BASE = "https://api.groq.com/openai/v1"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Groq API key not set. Use environment variable GROQ_API_KEY.")

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

def get_available_models():
    url = f"{GROQ_API_URL_BASE}/models"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return [m["id"] for m in r.json().get("data", [])]

def select_groq_model(preferred=None):
    models = get_available_models()
    print(f"[INFO] Available Groq models: {models}")
    if preferred:
        for m in preferred:
            if m in models:
                print(f"[INFO] Using preferred model: {m}")
                return m
    return "llama-3.1-8b-instant" if "llama-3.1-8b-instant" in models else (models[0] if models else None)

def call_llm_api(prompt: str, model: str, max_retries=3) -> str:
    api_url = f"{GROQ_API_URL_BASE}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an expert Python developer."},
            {"role": "user",   "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.1
    }
    for attempt in range(max_retries):
        try:
            resp = requests.post(api_url, headers=HEADERS, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.HTTPError as e:
            if resp.status_code == 429:
                wait = int(resp.headers.get("retry-after", 0)) or (2 ** attempt) * 5
                print(f"[WARN] Rate limit exceeded. Retrying in {wait} seconds...")
                time.sleep(wait)
                continue
            raise
        except Exception:
            raise
    raise RuntimeError("Failed to get response from Groq API after retries.")

# ---------------- Utilities ----------------
def clean_code(raw: str) -> str:
    raw = raw.strip()
    m = re.search(r"```(?:python)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    return m.group(1).strip() if m else raw.strip("` \n\r\t")

def extract_pdf_summary(pdf_path: str, max_pages=2) -> str:
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:max_pages]:
            txt = page.extract_text()
            if txt: texts.append(txt.strip())
    return "\n".join(texts)

def get_csv_sample(csv_path: str, max_lines=10) -> str:
    with open(csv_path, "r", encoding="utf-8") as f:
        return "".join([next(f, "") for _ in range(max_lines)])

# ---------------- Fallback Parser ----------------
def write_fallback_parser(parser_file):
    fallback = '''\
import pdfplumber
import pandas as pd

def parse(pdf_path: str) -> pd.DataFrame:
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if table:
                    header, *body = table
                    for row in body:
                        if any(cell and cell.strip() for cell in row):
                            while len(row) < 5: row.append(None)
                            date, desc, debit, credit, balance = row[:5]
                            def clean(val):
                                if val is None: return None
                                try: return float(str(val).replace(',', '').replace('₹',''))
                                except: return None
                            rows.append([date, desc, clean(debit), clean(credit), clean(balance)])
    df = pd.DataFrame(rows, columns=["Date","Description","Debit Amt","Credit Amt","Balance"])
    return df
'''
    os.makedirs(os.path.dirname(parser_file), exist_ok=True)
    with open(parser_file, "w", encoding="utf-8") as f:
        f.write(fallback)

# ---------------- Print Tables ----------------
def print_pdf_tables(pdf_path, df_parsed, n_pages=2, n_rows=5):
    print("\n--- Parsed Table Preview ---")
    print(df_parsed.head(n_rows))

    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages[:n_pages], 1):
            tables = page.extract_tables()
            print(f"\n--- Page {idx} Tables ---")
            for t_idx, table in enumerate(tables, 1):
                print(f"\nTable {t_idx}:")
                for r in table[:n_rows]:
                    print(r)

# ---------------- Test Parser ----------------
def test_parser(parser_file, pdf_file, csv_file, output_csv):
    import importlib.util
    spec = importlib.util.spec_from_file_location("parser", parser_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    df_parsed = module.parse(pdf_file)
    df_parsed.to_csv(output_csv, index=False)
    df_ref = pd.read_csv(csv_file)

    cols = ["Date","Description","Debit Amt","Credit Amt","Balance"]
    df_parsed = df_parsed.reindex(columns=cols).fillna(pd.NA).reset_index(drop=True)
    df_ref = df_ref.reindex(columns=cols).fillna(pd.NA).reset_index(drop=True)

    print_pdf_tables(pdf_file, df_parsed)
    try:
        diff = df_ref.compare(df_parsed)
        if not diff.empty:
            print("\nDifferences:\n", diff)
            return False, str(diff)
    except Exception:
        pass
    return df_ref.equals(df_parsed), ""

# ---------------- Agent Loop ----------------
def agent_loop(bank):
    data_dir, pdf_file, csv_file, output_csv, parser_file = get_paths(bank)
    model = select_groq_model(preferred=["llama-3.1-8b-instant", "llama-3.3-70b-versatile"])
    if not model:
        print("[ERROR] No valid Groq model found.")
        sys.exit(1)

    pdf_summary = extract_pdf_summary(pdf_file)
    csv_sample = get_csv_sample(csv_file)
    feedback = ""

    for attempt in range(1, 4):
        print(f"\nAgent attempt {attempt}")
        try:
            prompt = f"""
Given a bank statement PDF sample:
{pdf_summary}

Expected CSV schema and sample:
{csv_sample}

Generate a Python function
    parse(pdf_path: str) -> pandas.DataFrame
that returns columns:
[Date, Description, Debit Amt, Credit Amt, Balance].
Clean currency symbols/commas, handle repeated headers, empty rows, numeric conversion.

Previous feedback/errors:
{feedback}

Return valid Python code only.
"""
            parser_code = call_llm_api(prompt, model)
            parser_code_clean = clean_code(parser_code)
            os.makedirs(os.path.dirname(parser_file), exist_ok=True)
            with open(parser_file, "w", encoding="utf-8") as f:
                f.write(parser_code_clean)

            passed, feedback = test_parser(parser_file, pdf_file, csv_file, output_csv)
            if passed:
                print("✅ Parser passed the test on attempt", attempt)
                return
            print("❌ Parser failed. Feedback used for next attempt.")
        except Exception as e:
            print(f"[ERROR] Exception during attempt {attempt}: {e}")
        time.sleep(1)

    print("[WARN] Using fallback parser due to failures...")
    write_fallback_parser(parser_file)
    passed, _ = test_parser(parser_file, pdf_file, csv_file, output_csv)
    print("✅ Fallback parser passed the test!" if passed else "❌ Fallback parser failed.")

# ---------------- Main ----------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True, help="Target bank (e.g., icici, sbi)")
    args = p.parse_args()
    agent_loop(args.target)

if __name__ == "__main__":
    main()
