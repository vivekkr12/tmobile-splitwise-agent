#!/usr/bin/env python3
"""
Configuration helper script to set up Splitwise group and user mappings.
Run this script once to configure your settings.
"""
import json
import os
from pathlib import Path
from agent.splitwise_client import client_from_env, get_group_members


CONFIG_PATH = Path(__file__).parent.parent / "private" / "config.json"


def load_config():
    """Load configuration from JSON file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return None


def save_config(config):
    """Save configuration to JSON file."""
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
        s = client_from_env(None)
        current_user = s.getCurrentUser()
        print(f"\n✓ Connected to Splitwise as {current_user.getFirstName()}")
    except Exception as e:
        print(f"\n✗ Error connecting to Splitwise: {e}")
        print("\nMake sure you have set the following environment variables:")
        print("  - SW_OAUTH1_TOKEN or SW_OAUTH2_ACCESS_TOKEN")
        print("  - SW_OAUTH1_TOKEN_SECRET (for OAuth1)")
        return

    # Setup group
    group_config = setup_group(s)
    if not group_config:
        return

    # Setup user mappings
    user_mappings = setup_user_mappings(s, group_config["group_id"], owner_names)

    # Setup payer
    payer_name = setup_payer(owner_names)

    # Create final config
    config = {
        "splitwise": {
            "group_id": group_config["group_id"],
            "group_name": group_config["group_name"],
            "payer_name": payer_name
        },
        "user_mappings": user_mappings,
        "description_template": "T-Mobile Bill - {month}/{year}"
    }

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
