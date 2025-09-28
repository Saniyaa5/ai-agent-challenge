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
