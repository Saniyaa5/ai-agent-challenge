# ai-agent-challenge
Coding agent challenge which write custom parsers for Bank statement PDF. The agent reads a sample PDF and CSV, generates a parser script, tests it, and outputs a structured CSV. Supports multiple banks with zero manual tweaks.

---

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Agent Workflow](#agent-workflow)
- [Demo](#demo)

---

## Features
- Automatic parser generation for bank statements (ICICI, SBI, etc.)  
- Self-debugging agent loop (up to 3 correction attempts)  
- Fallback parser if LLM API fails  
- Displays parsed table previews and side-by-side comparison with expected CSV  
- CLI-based for easy execution  

---

## Requirements
- Python 3.9+  
- `pandas`  
- `pdfplumber`  
- `PyPDF2`  
- `requests`  

Install requirements with:

```bash
pip install -r requirements.txt
````

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/<Saniyaa5>/ai-agent-challenge.git
cd ai-agent-challenge
```
## Requirements

pandas
pdfplumber
PyPDF2
requests

2. Set your **Groq API key**:

**Linux/macOS:**

```bash
export GROQ_API_KEY=<YOUR_API_KEY>
```

**Windows PowerShell:**

```powershell
setx GROQ_API_KEY "<YOUR_API_KEY>"
```

---

## Usage

Run the agent for a specific bank (example: ICICI):

```bash
python agent.py --target icici
```

* Reads sample PDF: `data/icici/icici_sample.pdf`
* Reads expected CSV: `data/icici/result.csv`
* Generates parser: `custom_parsers/icici_parser.py`
* Outputs parsed CSV: `data/icici/parsed_output.csv`
* Shows preview of tables in console

You can replace `icici` with another bank (e.g., `sbi`) and provide your PDF/CSV samples to generate a new parser.

---

## Project Structure

```
ai-agent-challenge/
│
├─ agent.py                  # Main agent loop CLI script
├─ custom_parsers/         
│  └─ icici_parser.py        # Generated parser for ICICI bank
├─ data/
│  └─ icici/
│      ├─ icici_sample.pdf
│      ├─ result.csv
│      └─ parsed_output.csv
├─ icici.py                  # Optional static parser
├─ test_agent.py             # Tests for parser output
├─ requirements.txt          # Python dependencies
└─ README.md                 # Project documentation

---

## Agent Workflow

1. **Extract PDF summary**: Reads first pages of PDF to generate a prompt.
2. **Read CSV sample**: Provides expected schema & sample to agent.
3. **Generate parser**: Calls LLM API (Groq) to generate `parse(pdf_path)` function.
4. **Test parser**: Runs generated parser on PDF and compares to CSV using `DataFrame.equals()`.
5. **Self-correction loop**: Up to 3 attempts; if failed, fallback parser is used.
6. **Display output**: Shows parsed table previews and side-by-side comparison in console.

---

## Agent Workflow Diagram

```text
                    ┌─────────────────────┐
                    │   Start Agent CLI   │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Extract PDF Summary │
                    │ & CSV Sample        │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Generate Parser     │
                    │ (LLM API: Groq)    │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Test Parser Output  │
                    │ vs Expected CSV     │
                    └───────┬────────────┘
               ┌──────────────┴─────────────┐
               ▼                            ▼
      ┌─────────────────┐          ┌─────────────────┐
      │ Passed Test?    │  Yes     │ Failed Test?     │
      └───────┬─────────┘          └───────┬─────────┘
              │                             │
              ▼                             ▼
     ┌─────────────────┐         ┌───────────────────────┐
     │ Success! Parser │         │ Self-Correct Loop     │
     │ Generated       │         │ (up to 3 attempts)    │
     └─────────────────┘         └─────────┬─────────────┘
                                           ▼
                               ┌────────────────────────┐
                               │ Use Fallback Parser     │
                               │ if All Attempts Fail    │
                               └────────────────────────┘
                                           │
                                           ▼
                                   ┌─────────────┐
                                   │ End/Output  │
                                   │ CSV File    │
                                   └─────────────┘


## Demo

After cloning and setting the API key:

```bash
python agent.py --target icici
```

**Console Output Example:**

```
[INFO] Using preferred model: llama-3.1-8b-instant
--- Parsed Table Preview ---
         Date Description  Debit Amt  Credit Amt   Balance
0 2025-09-01  ATM WITHDRAW     500.0        0.0   15000.0
1 2025-09-02  ONLINE TRANSFER   0.0     2000.0   17000.0

--- Page 1 Tables ---
Table 1:
['Date', 'Description', 'Debit', 'Credit', 'Balance']
['01-09-2025', 'ATM WITHDRAW', '500', '', '15000']
...
```

---

## Notes

* Supports multiple banks; simply replace `--target <bank>` and provide PDF/CSV samples.
* Follows the “Agent-as-Coder” challenge goals: CLI execution, parser auto-generation, test assertions.
* Can be extended to additional banks by providing new samples in `data/<bank>/`.

---

