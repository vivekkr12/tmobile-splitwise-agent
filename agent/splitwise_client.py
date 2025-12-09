import os
from splitwise import Splitwise
from splitwise.expense import Expense, ExpenseUser

# Try to load .env file if it exists (override=True to override OS env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    # dotenv not installed, will use environment variables directly
    pass


def client_from_env():
    """
    Create Splitwise client from environment variables using API key authentication.

    Required environment variables:
        - SW_CONSUMER_KEY: Your Splitwise app consumer key
        - SW_CONSUMER_SECRET: Your Splitwise app consumer secret
        - SW_API_KEY: Your Splitwise API key

    Returns:
        Authenticated Splitwise client

    Raises:
        ValueError: If required environment variables are not set
    """
    sw_consumer_key = os.getenv("SW_CONSUMER_KEY")
    sw_consumer_secret = os.getenv("SW_CONSUMER_SECRET")
    sw_api_key = os.getenv("SW_API_KEY")

    if not sw_consumer_key or not sw_consumer_secret or not sw_api_key:
        raise ValueError(
            "Missing Splitwise consumer credentials. Please set:\n"
            "  - SW_CONSUMER_KEY\n"
            "  - SW_CONSUMER_SECRET\n"
            "  - SW_API_KEY\n"
            "in your environment variables or .env file\n"
            "Get your credentials from: https://secure.splitwise.com/apps"
        )

    # Create Splitwise client
    s = Splitwise(sw_consumer_key, sw_consumer_secret, api_key=sw_api_key)
    return s


def check_duplicate_expense(s, group_id, description_contains, month, year):
    """
    Check if an expense with similar description already exists for this month/year in the group.

    Args:
        s: Splitwise client
        group_id: The group ID to filter expenses
        description_contains: String that should be contained in the description
        month: Bill month (e.g., "11")
        year: Bill year (e.g., "2024")

    Returns:
        Tuple of (bool, Expense or None): (True, expense) if duplicate exists, (False, None) otherwise
    """
    # Get expenses for the specific group only
    expenses = s.getExpenses(group_id=group_id, limit=100)

    # Search string to match in description
    search_str = f"{month}/{year}"

    for expense in expenses:
        desc = expense.getDescription() or ""
        if description_contains in desc and search_str in desc:
            return True, expense

    return False, None


def create_group_expense(s, group_id, total, payer_id, shares, description, details=None):
    """
    Create an expense in a Splitwise group.

    Args:
        s: Splitwise client
        group_id: Group ID where expense should be created
        total: Total amount of the expense
        payer_id: User ID of the person who paid
        shares: dict[user_id] = owed_amount - how much each user owes
        description: Description of the expense
        details: Optional details/notes

    Returns:
        Tuple of (Expense, errors)
    """
    expense = Expense()
    expense.setGroupId(group_id)
    expense.setCost(f"{total:.2f}")
    expense.setDescription(description)

    # Use details to store additional info
    if details and hasattr(expense, "setDetails"):
        expense.setDetails(details)

    # Payer pays full amount, others owe their shares
    users = []
    total_owed = sum(shares.values())

    for uid, owed in shares.items():
        u = ExpenseUser()
        u.setId(uid)
        if uid == payer_id:
            # Payer paid the full amount but only owes their share
            u.setPaidShare(f"{total_owed:.2f}")
            u.setOwedShare(f"{owed:.2f}")
        else:
            # Others didn't pay but owe their share
            u.setPaidShare("0.00")
            u.setOwedShare(f"{owed:.2f}")
        users.append(u)

    for u in users:
        expense.addUser(u)

    created, errors = s.createExpense(expense)
    return created, errors


def add_expense_comment(s, expense_id, comment_text):
    """
    Add a comment to an expense.

    Args:
        s: Splitwise client
        expense_id: ID of the expense to comment on
        comment_text: Text content of the comment

    Returns:
        Tuple of (Comment, errors)
    """
    comment, errors = s.createComment(expense_id, comment_text)
    return comment, errors


def create_breakdown_comment(bill, user_mappings):
    """
    Create a formatted comment text showing the itemized breakdown.

    Args:
        bill: TMobileBill object with line charges
        user_mappings: Dict mapping owner names to user IDs

    Returns:
        Formatted comment string
    """
    # Reverse mapping: user_id -> owner_name
    id_to_name = {v: k for k, v in user_mappings.items()}

    lines = ["📱 Line-by-line breakdown:", ""]

    for line_charge in bill.line_charges:
        owner = line_charge.owner

        # Calculate total for this line
        line_total = (
            line_charge.line_amount +
            line_charge.equipment_amount +
            line_charge.one_time_amount
        )

        lines.append(f"{owner}:")
        lines.append(f"  • Line charges: ${line_charge.line_amount:.2f}")

        if line_charge.equipment_amount > 0:
            lines.append(f"  • Equipment: ${line_charge.equipment_amount:.2f}")

        if line_charge.one_time_amount > 0:
            lines.append(f"  • One-time: ${line_charge.one_time_amount:.2f}")

        lines.append(f"  • Subtotal: ${line_total:.2f}")
        lines.append("")

    # Add summary
    lines.append("📊 Bill Summary:")
    lines.append(f"  • Plan: ${bill.plan:.2f}")
    lines.append(f"  • Equipment: ${bill.equipment:.2f}")

    if bill.one_time_charges > 0:
        lines.append(f"  • One-time charges: ${bill.one_time_charges:.2f}")

    lines.append(f"  • Total: ${bill.total_due:.2f}")

    return "\n".join(lines)


def get_group_members(s, group_id):
    """
    Get all members of a Splitwise group.

    Args:
        s: Splitwise client
        group_id: Group ID

    Returns:
        List of group members
    """
    group = s.getGroup(group_id)
    return group.getMembers() if group else []


def find_user_by_name(s, group_id, name):
    """
    Find a user in a group by their first name (case-insensitive).

    Args:
        s: Splitwise client
        group_id: Group ID
        name: Name to search for

    Returns:
        User ID if found, None otherwise
    """
    members = get_group_members(s, group_id)
    name_lower = name.lower()

    for member in members:
        first_name = (member.getFirstName() or "").lower()
        if first_name == name_lower:
            return member.getId()

    return None
