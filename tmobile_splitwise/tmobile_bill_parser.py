import json
from tmobile_splitwise.llm_client import call_chat_completions
import PyPDF2

from tmobile_splitwise.data_models import TMobileBill

# Step 1: Extract raw text
def pdf_to_text(path: str) -> str:
    text = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        page_num = 0
        for page in reader.pages:
            text.append(page.extract_text() or "")
            page_num += 1

            if page_num >= 2:
                break

    return "\n".join(text)

# Step 3: Use LLM to parse into structured JSON
def parse_bill_with_llm(text: str) -> TMobileBill:

    with open("private/phone_owners.txt", "r") as f:
        phone_owners = f.read()

    prompt = f"""
    You are a parser for T-Mobile bills.
    Input is noisy text extracted from a PDF.
    Extract the bill into STRICT JSON that follows this schema:
    {{
      "month": "string",    # billing cycle dates
      "year": "string"
      "total_due": float,
      "plan": float,
      "equipment": float,
      "one_time_charges": float,
      "line_charges": [{{"phone": "xxx-xxx-xxxx", "owner": "string", "line_amount": float, "equipment_amount": float, "one_time_amount": float}}],
    }}

    STEP-BY-STEP INSTRUCTIONS:

    STEP 1: Find the "THIS BILL SUMMARY" section in the text. This section has a table with these columns:
    - Line Type | Plans | Equipment | Services | One-time charges | Total

    STEP 2: In the "Totals" row of that table, extract the numeric values from:
    - plan = the Plans column value
    - equipment = the Equipment column value
    - one_time_charges = the One-time charges column value
    - total_due = the Total column value

    STEP 3: Find the "bill issue date" at the top and extract:
    - month = the month name
    - year = the year

    STEP 4: Count how many phone number rows exist (rows starting with "(xxx) xxx-xxxx"). Skip "Account" and "Totals" rows.

    STEP 5: For EACH phone number row, extract this data:
    a) phone = the exact phone number
    b) equipment_amount: Read from the Equipment column of THIS phone's row:
       - If it shows a dollar amount (even if Plans says "Included"), use that amount
       - If it shows "-" or blank, use 0.0
    c) one_time_amount: Read from the One-time charges column of THIS phone's row:
       - If it shows a dollar amount, use that amount
       - If it shows "-" or blank, use 0.0
    d) line_amount: DO NOT read from the Plans column. Instead, calculate:
       line_amount = plan (from STEP 2) ÷ number_of_phone_lines (from STEP 4)
       This splits the total plan cost equally among all lines.
    e) owner: Match from this mapping: {phone_owners}

    STEP 6: CRITICAL CHECK - Even if a line has "Included" in the Plans column, you MUST still read the Equipment column value for that line. Do not assume it's 0.

    Input text:
    {text}
    """

    resp = call_chat_completions(prompt)
    content = resp.choices[0].message.content
    if content is None:
        raise ImportError("No LLM Response")

    if content.startswith("```json"):
        content = content[len("```json"):].strip()
    if content.endswith("```"):
        content = content[:-len("```")].strip()

    # ensure it parses
    data = json.loads(content)
    return TMobileBill(**data)
