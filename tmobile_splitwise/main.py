#!/usr/bin/env python3
"""
Main script to process T-Mobile bills and create Splitwise expenses.

Usage:
    python tmobile_splitwise/main.py <path_to_bill.pdf>
"""
import sys
import json
from pathlib import Path
from tmobile_splitwise.tmobile_bill_parser import pdf_to_text, parse_bill_with_llm
from tmobile_splitwise.splitwise_client import (
    client_from_env,
    check_duplicate_expense,
    create_group_expense,
    add_expense_comment,
    create_breakdown_comment
)


CONFIG_PATH = Path(__file__).parent.parent / "private" / "config.json"


def load_config():
    """Load configuration from JSON file."""
    if not CONFIG_PATH.exists():
        print(f"Error: Configuration file not found at {CONFIG_PATH}")
        print("Please run 'python tmobile_splitwise/config_helper.py' first to set up your configuration.")
        sys.exit(1)

    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    # Validate config
    if not config.get("splitwise", {}).get("group_id"):
        print("Error: group_id not set in configuration.")
        print("Please run 'python tmobile_splitwise/config_helper.py' to configure.")
        sys.exit(1)

    if not config.get("user_mappings"):
        print("Error: user_mappings not set in configuration.")
        print("Please run 'python tmobile_splitwise/config_helper.py' to configure.")
        sys.exit(1)

    return config


def calculate_shares(bill, user_mappings):
    """
    Calculate how much each user owes based on the bill.

    Args:
        bill: TMobileBill object
        user_mappings: Dict mapping owner names to Splitwise user IDs

    Returns:
        Dict[user_id, amount] - how much each user owes
    """
    shares = {}

    # Each person pays for their line charges
    for line_charge in bill.line_charges:
        owner = line_charge.owner
        if owner not in user_mappings:
            print(f"Warning: Owner '{owner}' not found in user mappings. Skipping.")
            continue

        user_id = user_mappings[owner]
        if user_id not in shares:
            shares[user_id] = 0.0

        # Add line amount, equipment, and one-time charges for this user
        shares[user_id] += line_charge.line_amount
        shares[user_id] += line_charge.equipment_amount
        shares[user_id] += line_charge.one_time_amount

    return shares


def process_bill(pdf_path, config, dry_run=False):
    """
    Process a T-Mobile bill PDF and create Splitwise expenses.

    Args:
        pdf_path: Path to the PDF bill
        config: Configuration dict
        dry_run: If True, don't actually create the expense

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Processing bill: {pdf_path}")
    print(f"{'='*60}\n")

    # Step 1: Extract text from PDF
    print("Step 1: Extracting text from PDF...")
    try:
        raw_text = pdf_to_text(pdf_path)
        print(f"✓ Extracted {len(raw_text)} characters")
    except Exception as e:
        print(f"✗ Error extracting text: {e}")
        return False

    # Step 2: Parse bill with LLM
    print("\nStep 2: Parsing bill with LLM...")
    try:
        bill = parse_bill_with_llm(raw_text)
        print(f"✓ Parsed bill for {bill.month}/{bill.year}")
        print(f"  Total due: ${bill.total_due:.2f}")
        print(f"  Plan: ${bill.plan:.2f}")
        print(f"  Equipment: ${bill.equipment:.2f}")
        print(f"  One-time charges: ${bill.one_time_charges:.2f}")
        print(f"  Line charges: {len(bill.line_charges)} lines")
    except Exception as e:
        print(f"✗ Error parsing bill: {e}")
        return False

    # Step 3: Calculate shares
    print("\nStep 3: Calculating shares...")
    user_mappings = config["user_mappings"]
    shares = calculate_shares(bill, user_mappings)

    if not shares:
        print("✗ No shares calculated. Check your configuration.")
        return False

    print("✓ Shares calculated:")
    for user_id, amount in shares.items():
        # Find owner name for this user_id
        owner = next((k for k, v in user_mappings.items() if v == user_id), "Unknown")
        print(f"  {owner}: ${amount:.2f}")

    total_shares = sum(shares.values())
    print(f"  Total: ${total_shares:.2f}")

    # Step 4: Connect to Splitwise
    print("\nStep 4: Connecting to Splitwise...")
    try:
        s = client_from_env()
        current_user = s.getCurrentUser()
        print(f"✓ Connected as {current_user.getFirstName()}")
    except Exception as e:
        print(f"✗ Error connecting to Splitwise: {e}")
        return False

    # Step 5: Check for duplicates
    print("\nStep 5: Checking for duplicate expenses...")
    group_id = config["splitwise"]["group_id"]
    description_template = config.get("description_template", "T-Mobile Bill - {month}/{year}")

    is_duplicate, existing_expense = check_duplicate_expense(
        s, group_id, "T-Mobile Bill", bill.month, bill.year
    )

    if is_duplicate:
        print(f"✗ Duplicate expense found!")
        print(f"  Description: {existing_expense.getDescription()}")
        print(f"  Amount: ${existing_expense.getCost()}")
        print(f"  ID: {existing_expense.getId()}")
        print("\nSkipping creation to avoid duplicate.")
        return False

    print("✓ No duplicate found")

    # Step 6: Get payer ID
    print("\nStep 6: Determining payer...")
    payer_name = config["splitwise"]["payer_name"]
    payer_id = user_mappings.get(payer_name)

    if not payer_id:
        print(f"✗ Payer '{payer_name}' not found in user mappings")
        return False

    print(f"✓ Payer: {payer_name} (ID: {payer_id})")

    # Step 7: Create expense
    description = description_template.format(month=bill.month, year=bill.year)
    details = f"Total due: ${bill.total_due:.2f}"

    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN - Would create expense:")
        print("="*60)
        print(f"Description: {description}")
        print(f"Details: {details}")
        print(f"Group ID: {group_id}")
        print(f"Total: ${total_shares:.2f}")
        print(f"Payer: {payer_name} (ID: {payer_id})")
        print("\nShares:")
        for user_id, amount in shares.items():
            owner = next((k for k, v in user_mappings.items() if v == user_id), "Unknown")
            print(f"  {owner}: ${amount:.2f}")

        # Show what the breakdown comment would look like
        print("\n" + "="*60)
        print("Would add this breakdown comment:")
        print("="*60)
        breakdown_text = create_breakdown_comment(bill, user_mappings)
        print(breakdown_text)

        return True

    print("\nStep 7: Creating expense in Splitwise...")
    try:
        created, errors = create_group_expense(
            s, group_id, total_shares, payer_id, shares, description, details
        )

        if errors:
            print(f"✗ Errors occurred:")
            print(f"  {errors}")
            return False

        if created:
            expense_id = created.getId()
            print(f"✓ Expense created successfully!")
            print(f"  ID: {expense_id}")
            print(f"  Description: {created.getDescription()}")
            print(f"  Amount: ${created.getCost()}")

            # Step 8: Add itemized breakdown as a comment
            print("\nStep 8: Adding itemized breakdown comment...")
            try:
                breakdown_text = create_breakdown_comment(bill, user_mappings)
                comment, comment_errors = add_expense_comment(s, expense_id, breakdown_text)

                if comment_errors:
                    print(f"⚠ Warning: Could not add comment: {comment_errors}")
                    print("  (Expense was created successfully)")
                elif comment:
                    print(f"✓ Breakdown comment added successfully!")
                else:
                    print(f"⚠ Warning: Comment creation returned no result")

            except Exception as e:
                print(f"⚠ Warning: Error adding comment: {e}")
                print("  (Expense was created successfully)")

            return True
        else:
            print(f"✗ Failed to create expense (no error details)")
            return False

    except Exception as e:
        print(f"✗ Error creating expense: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python tmobile_splitwise/main.py <path_to_bill.pdf> [--dry-run]")
        print("\nExample:")
        print("  python tmobile_splitwise/main.py TMobileBill_Nov2024.pdf")
        print("  python tmobile_splitwise/main.py TMobileBill_Nov2024.pdf --dry-run")
        sys.exit(1)

    pdf_path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    # Load configuration
    config = load_config()

    # Process the bill
    success = process_bill(pdf_path, config, dry_run)

    if success:
        print("\n" + "="*60)
        print("✓ SUCCESS!")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("✗ FAILED")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
