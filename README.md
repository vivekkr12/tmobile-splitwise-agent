# T-Mobile Splitwise Agent

Automatically parse T-Mobile PDF bills and create expenses in Splitwise with duplicate detection.

## Features

- 📄 Parse T-Mobile PDF bills using LLM
- 💰 Automatically calculate charges per line owner
- 🔄 Create Splitwise expenses with proper split
- 📝 Add itemized breakdown as a comment (shows each person's line charges, equipment, and fees)
- ✅ Duplicate detection by group ID (prevents creating the same bill twice)
- 🎯 Interactive configuration setup

## Prerequisites

1. **Splitwise Account** with API key
2. **Azure OpenAI** or OpenAI API access (for bill parsing)
3. **Python 3.12+**

## Quick Start

### 1. Install Dependencies

```bash
cd tmobile-splitwise-agent
pip install -e .
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
touch .env
```

Edit `.env` with your actual values:

```bash
# OpenAI-compatible LLM endpoint (for bill parsing)
OPENAI_BASE_URL=opnenai_api_base_url
OPENAI_API_KEY=your_api_key
OPENI_MODEL_NAME=openai_model_name

# Splitwise API credentials
SW_CONSUMER_KEY=your_consumer_key
SW_CONSUMER_SECRET=your_consumer_secret
SW_API_KEY=your_api_key
```

### 3. Get Splitwise API Credentials

**Register your app** at https://secure.splitwise.com/apps:
1. Click "Register your application"
2. Fill in the application details (name, description, homepage URL)
3. You'll get:
   - **Consumer Key**
   - **Consumer Secret**
   - **API Key**
4. Add all three to your `.env` file

That's it! The API key provides simple authentication without needing OAuth flows.

### 4. Configure Phone Owners

Add a file `private/phone_owners.txt` with your phone numbers and owners.
Each line contains a phone number and the owner's name, separated by a hyphen:

```
(123) 456-7890 - Satya
(123) 456-7891 - Sundar
(123) 456-7892 - Tim
(123) 456-7893 - Jeff
```

### 5. Run Configuration Helper

This interactive script will help you set up your Splitwise group and user mappings:

```bash
python tmobile_splitwise/config_helper.py
```

**First time setup** - The script will:
- Create the `private` directory automatically if it doesn't exist
- Show all your Splitwise groups
- Let you select which group to use
- Map phone owners to Splitwise users
- Set the default bill payer
- Save configuration to `private/config.json`

**Updating existing configuration** - If `config.json` already exists, you can:
- **(u)pdate**: Selectively update only what you need (group, user mappings, or payer)
- **(r)eplace**: Completely replace the configuration with new values

The script will show your current settings and ask which parts you want to change.

## Usage

### Process a T-Mobile Bill

```bash
python tmobile_splitwise/main.py TMobileBill.pdf
```

### Dry Run (Preview Without Creating)

```bash
python tmobile_splitwise/main.py TMobileBill.pdf --dry-run
```

## How It Works

1. **Extract Text**: Uses PyPDF2 to extract text from the PDF
2. **Parse with LLM**: Sends text to OpenAI (or other LLM) to extract structured data
3. **Calculate Shares**: Determines how much each person owes based on their line charges
4. **Check Duplicates**: Searches Splitwise for existing expenses with the same month/year in the specified group
5. **Create Expense**: Creates a new Splitwise expense if no duplicate found
6. **Add Breakdown Comment**: Automatically adds a detailed line-by-line breakdown as a comment on the expense

## Duplicate Detection

The system checks for duplicate expenses by:
- **Group ID filtering**: Only looks at expenses in your configured group
- **Description matching**: Looks for "T-Mobile Bill" in the description
- **Month/Year matching**: Ensures the same bill period isn't processed twice

This prevents accidentally creating duplicate expenses when running the script multiple times.

## Project Structure

```
tmobile_splitwise/
  ├── main.py              # Main script to process bills
  ├── config_helper.py     # Setup configuration (run once)
  ├── splitwise_client.py  # Splitwise API wrapper with duplicate detection
  ├── tmobile_bill_parser.py # PDF parsing logic
  ├── llm_client.py        # OpenAI client wrapper
  └── data_models.py       # Pydantic data structures

private/
  ├── config.json          # Your configuration (auto-generated)
  └── phone_owners.txt     # Phone number to owner mapping
```

## Configuration File

The `private/config.json` file is automatically created and managed by `config_helper.py`. It looks like this:

```json
{
  "splitwise": {
    "group_id": 100,
    "group_name": "T-Mobile Family",
    "payer_name": "Satya"
  },
  "user_mappings": {
    "Satya": 101,
    "Sundar": 102,
    "Tim": 103,
    "Jeff": 104
  },
  "description_template": "T-Mobile Bill - {month}/{year}"
}
```

**To update your configuration**, simply run:
```bash
python tmobile_splitwise/config_helper.py
```

The script will detect your existing config and let you update specific parts or replace everything. You can also manually edit this file if needed.

## Example Output

```
============================================================
Processing bill: TMobileBill_Nov2024.pdf
============================================================

Step 1: Extracting text from PDF...
✓ Extracted 12543 characters

Step 2: Parsing bill with LLM...
✓ Parsed bill for 11/2024
  Total due: $245.67
  Plan: $120.00
  Equipment: $45.67
  One-time charges: $0.00
  Line charges: 4 lines

Step 3: Calculating shares...
✓ Shares calculated:
  Satya: $61.42
  Sundar: $61.42
  Tim: $61.42
  Jeff: $61.41
  Total: $245.67

Step 4: Connecting to Splitwise...
✓ Connected as Satya

Step 5: Checking for duplicate expenses...
✓ No duplicate found

Step 6: Determining payer...
✓ Payer: Satya (ID: 9876545)

Step 7: Creating expense in Splitwise...
✓ Expense created successfully!
  ID: 1234567890
  Description: T-Mobile Bill - Nov 2024
  Amount: 245.67

Step 8: Adding itemized breakdown comment...
✓ Breakdown comment added successfully!

============================================================
✓ SUCCESS!
============================================================
```

## Itemized Breakdown

After creating the expense, the script automatically adds a comment with a detailed line-by-line breakdown:

```
📱 Line-by-line breakdown:

Satya:
  • Line charges: $46.25
  • Equipment: $18.96
  • One-time: $3.50
  • Subtotal: $68.71

Sundar:
  • Line charges: $46.25
  • Equipment: $11.25
  • Subtotal: $57.50

Tim:
  • Line charges: $46.25
  • Subtotal: $46.25

Jeff:
  • Line charges: $46.25
  • Equipment: $21.67
  • Subtotal: $67.92

📊 Bill Summary:
  • Plan: $185.00
  • Equipment: $51.88
  • One-time charges: $3.50
  • Total: $240.38
```

This breakdown appears as a comment on the expense in Splitwise, allowing everyone to see exactly what they're paying for.

## Troubleshooting

### Configuration Errors

**"Configuration file not found"**
- Run `python tmobile_splitwise/config_helper.py` to set up your configuration.
- The script will automatically create the `private` directory and `config.json` file.

**"Owner 'Name' not found in user mappings"**
- Run `python tmobile_splitwise/config_helper.py` to update your configuration.
- Choose **(u)pdate** and then update just the user mappings.

**Need to change group or payer?**
- Run `python tmobile_splitwise/config_helper.py` and select **(u)pdate**.
- The script will show your current settings and let you update only what you need.
- Your other settings will remain unchanged.

### Splitwise API Errors

**"Error connecting to Splitwise"**

Check that your environment variables are set:
```bash
echo $SW_CONSUMER_KEY
echo $SW_CONSUMER_SECRET
echo $SW_API_KEY
```

Make sure you have all three credentials from https://secure.splitwise.com/apps

### OpenAI API Errors

**"Missing OpenAI configuration"**

Check that your OpenAI environment variables are set:
```bash
echo $OPENAI_BASE_URL
echo $OPENAI_API_KEY
echo $OPENAI_MODEL_NAME
```

### Duplicate Expense Warning

**"Duplicate expense found"**

This is normal! It means you already processed this bill. The system prevents creating the same expense twice by checking:
- Group ID
- Month/Year in description
- "T-Mobile Bill" keyword

This is expected behavior to prevent duplicates when you run the script multiple times.

## Security Notes

- ✅ Never commit `private/config.json` or `.env` files to version control
- ✅ The `.gitignore` is already configured to exclude these files
- ✅ API keys and tokens are sensitive - keep them secure
- ✅ Regenerate your API key if it's accidentally exposed

## Advanced Configuration

### Using Different LLM Providers

The system supports any OpenAI-compatible endpoint:

**Azure OpenAI:**
```bash
OPENAI_BASE_URL=https://<your-azureaifoundry>.openai.azure.com/openai/v1
OPENAI_API_KEY=your_azure_key
```

**OpenAI:**
```bash
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_key
```

**Local Models (e.g., Ollama, LM Studio):**
```bash
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=dummy  # Some local servers require any non-empty value
```

### Customizing Bill Description

Edit `private/config.json`:
```json
{
  "description_template": "T-Mobile - {month}/{year} - Family Plan"
}
```

## Resources

- [Splitwise API Documentation](https://dev.splitwise.com/)
- [Splitwise Python SDK](https://github.com/namaggarwal/splitwise)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
