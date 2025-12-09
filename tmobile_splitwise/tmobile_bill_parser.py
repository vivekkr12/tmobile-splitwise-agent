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

    Month & year should be parsed only form the "bill issue date". Don't get this information from anywhere else.
    Read one time charges only from "THIS BILL SUMMARY" section.
    In the root node, plan should be the total plan amount.
    Divide the plan amount equally between all lines in the line_charges section.
    For owners, use this phone number to owner mapping:
    {phone_owners}

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
