#!/usr/bin/env python3
"""
Configuration helper script to set up Splitwise group and user mappings.
Run this script once to configure your settings.
"""
import json
from pathlib import Path
from tmobile_splitwise.splitwise_client import client_from_env, get_group_members


CONFIG_PATH = Path(__file__).parent.parent / "private" / "config.json"


def load_config():
    """Load configuration from JSON file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return None


def save_config(config):
    """Save configuration to JSON file."""
    # Ensure the directory exists
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Configuration saved to {CONFIG_PATH}")


def setup_group(s):
    """Interactive setup for Splitwise group."""
    print("\n=== Splitwise Groups ===")
    groups = s.getGroups()

    if not groups:
        print("No groups found. Please create a group in Splitwise first.")
        return None

    print("\nYour Splitwise groups:")
    for i, group in enumerate(groups, 1):
        print(f"{i}. {group.getName()} (ID: {group.getId()})")

    while True:
        try:
            choice = int(input(f"\nSelect group number (1-{len(groups)}): "))
            if 1 <= choice <= len(groups):
                selected_group = groups[choice - 1]
                return {
                    "group_id": selected_group.getId(),
                    "group_name": selected_group.getName()
                }
            else:
                print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a number.")


def setup_user_mappings(s, group_id, owner_names):
    """Interactive setup for user mappings."""
    print("\n=== User Mappings ===")
    members = get_group_members(s, group_id)

    if not members:
        print("No members found in the group.")
        return {}

    print(f"\nMembers in the group:")
    for i, member in enumerate(members, 1):
        first_name = member.getFirstName() or ""
        last_name = member.getLastName() or ""
        print(f"{i}. {first_name} {last_name} (ID: {member.getId()})")

    mappings = {}
    print(f"\nMap phone owners to Splitwise users:")

    for owner in owner_names:
        print(f"\n'{owner}' should be mapped to:")
        while True:
            try:
                choice = int(input(f"Select member number (1-{len(members)}): "))
                if 1 <= choice <= len(members):
                    mappings[owner] = members[choice - 1].getId()
                    print(f"✓ {owner} -> {members[choice - 1].getFirstName()}")
                    break
                else:
                    print("Invalid choice. Try again.")
            except ValueError:
                print("Please enter a number.")

    return mappings


def setup_payer(owner_names):
    """Interactive setup for default payer."""
    print("\n=== Default Payer ===")
    print("Who typically pays the T-Mobile bill?")

    for i, owner in enumerate(owner_names, 1):
        print(f"{i}. {owner}")

    while True:
        try:
            choice = int(input(f"\nSelect payer number (1-{len(owner_names)}): "))
            if 1 <= choice <= len(owner_names):
                return owner_names[choice - 1]
            else:
                print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a number.")


def main():
    """Main configuration setup."""
    print("=" * 50)
    print("T-Mobile Splitwise Agent - Configuration Setup")
    print("=" * 50)

    # Check if config already exists
    existing_config = load_config()
    if existing_config:
        print(f"\n✓ Found existing configuration at {CONFIG_PATH}")
        print("\nCurrent configuration:")
        print(json.dumps(existing_config, indent=2))

        while True:
            choice = input("\nDo you want to (u)pdate or (r)eplace the config? [u/r]: ").lower()
            if choice in ['u', 'r']:
                if choice == 'r':
                    print("\n⚠ This will replace your entire configuration.")
                    confirm = input("Are you sure? [y/n]: ").lower()
                    if confirm != 'y':
                        print("Configuration update cancelled.")
                        return
                    existing_config = None  # Treat as new config
                break
            else:
                print("Please enter 'u' for update or 'r' for replace.")
    else:
        print(f"\n✓ No existing configuration found. Creating new config at {CONFIG_PATH}")

    # Load phone owners
    phone_owners_path = Path(__file__).parent.parent / "private" / "phone_owners.txt"
    if not phone_owners_path.exists():
        print(f"Error: {phone_owners_path} not found!")
        return

    with open(phone_owners_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    owner_names = [line.split(" - ")[1] for line in lines if " - " in line]
    print(f"\nFound {len(owner_names)} phone owners: {', '.join(owner_names)}")

    # Create Splitwise client
    try:
        s = client_from_env()
        current_user = s.getCurrentUser()
        print(f"\n✓ Connected to Splitwise as {current_user.getFirstName()}")
    except Exception as e:
        print(f"\n✗ Error connecting to Splitwise: {e}")
        print("\nMake sure you have set the following environment variables:")
        print("  - SW_CONSUMER_KEY")
        print("  - SW_CONSUMER_SECRET")
        print("  - SW_API_KEY")
        print("\nGet these from: https://secure.splitwise.com/apps")
        return

    # Initialize config with existing values or create new
    config = existing_config if existing_config else {}
    if "splitwise" not in config:
        config["splitwise"] = {}
    if "user_mappings" not in config:
        config["user_mappings"] = {}

    # Setup group
    if existing_config:
        print(f"\nCurrent group: {config['splitwise'].get('group_name')} (ID: {config['splitwise'].get('group_id')})")
        update_group = input("Update group? [y/n]: ").lower()
        if update_group == 'y':
            group_config = setup_group(s)
            if group_config:
                config["splitwise"]["group_id"] = group_config["group_id"]
                config["splitwise"]["group_name"] = group_config["group_name"]
    else:
        group_config = setup_group(s)
        if not group_config:
            return
        config["splitwise"]["group_id"] = group_config["group_id"]
        config["splitwise"]["group_name"] = group_config["group_name"]

    # Setup user mappings
    if existing_config:
        print("\nCurrent user mappings:")
        for owner, user_id in config['user_mappings'].items():
            print(f"  {owner}: {user_id}")
        update_mappings = input("Update user mappings? [y/n]: ").lower()
        if update_mappings == 'y':
            user_mappings = setup_user_mappings(s, config["splitwise"]["group_id"], owner_names)
            config["user_mappings"] = user_mappings
    else:
        user_mappings = setup_user_mappings(s, config["splitwise"]["group_id"], owner_names)
        config["user_mappings"] = user_mappings

    # Setup payer
    if existing_config:
        print(f"\nCurrent payer: {config['splitwise'].get('payer_name')}")
        update_payer = input("Update payer? [y/n]: ").lower()
        if update_payer == 'y':
            payer_name = setup_payer(owner_names)
            config["splitwise"]["payer_name"] = payer_name
    else:
        payer_name = setup_payer(owner_names)
        config["splitwise"]["payer_name"] = payer_name

    # Ensure description template exists
    if "description_template" not in config:
        config["description_template"] = "T-Mobile Bill - {month}/{year}"

    # Save config
    save_config(config)

    print("\n" + "=" * 50)
    print("✓ Configuration complete!")
    print("=" * 50)
    print(f"\nGroup: {config['splitwise']['group_name']} (ID: {config['splitwise']['group_id']})")
    print(f"Payer: {config['splitwise']['payer_name']}")
    print("\nUser mappings:")
    for owner, user_id in config['user_mappings'].items():
        print(f"  {owner}: {user_id}")
    print(f"\nYou can now run the main script to process T-Mobile bills!")


if __name__ == "__main__":
    main()
