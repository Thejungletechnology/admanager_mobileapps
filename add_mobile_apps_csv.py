#!/usr/bin/env python3
"""
Alternative script with CSV input for adding multiple mobile apps.

This version reads app data from a CSV file for easier bulk operations.
"""

import csv
import sys
from googleads import ad_manager


def load_apps_from_csv(csv_file):
    """
    Load mobile application data from a CSV file.
    
    CSV format (with headers):
    display_name,app_store,app_store_id
    
    Args:
        csv_file (str): Path to the CSV file
    
    Returns:
        list: List of dicts with app data
    """
    apps = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                apps.append({
                    'display_name': row['display_name'].strip(),
                    'app_store': row['app_store'].strip(),
                    'app_store_id': row['app_store_id'].strip(),
                })
        return apps
    except FileNotFoundError:
        print(f"✗ CSV file not found: {csv_file}")
        sys.exit(1)
    except KeyError as e:
        print(f"✗ Missing column in CSV: {e}")
        sys.exit(1)


def add_mobile_applications(apps_data):
    """
    Add mobile applications to Ad Manager account.
    
    Args:
        apps_data (list): List of dicts containing app information
    
    Returns:
        list: Created MobileApplication objects
    """
    import os
    yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'googleads.yaml')
    ad_manager_client = ad_manager.AdManagerClient.LoadFromStorage(path=yaml_path)
    mobile_app_service = ad_manager_client.GetService('MobileApplicationService', version='v202602')
    
    mobile_applications = []
    for app in apps_data:
        mobile_app = {
            'displayName': app['display_name'],
            'appStores': [app['app_store']],
            'appStoreId': app['app_store_id'],
        }
        mobile_applications.append(mobile_app)
    
    created = []
    skipped = []
    for mobile_app in mobile_applications:
        try:
            result = mobile_app_service.createMobileApplications([mobile_app])
            if result:
                app = result[0]
                print(f"  ✓ {mobile_app['displayName']} (ID: {app['id']})")
                created.append(app)
        except Exception as e:
            err = str(e)
            if 'NON_UNIQUE_STORE_ID' in err:
                reason = 'already exists'
            elif 'MISSING_APP_STORE_ENTRY' in err:
                reason = 'not found on Play Store'
            elif 'MISSING_UAM_DATA' in err:
                reason = 'missing store data'
            else:
                reason = err[:80]
            print(f"  ✗ {mobile_app['displayName']} — {reason}")
            skipped.append((mobile_app['displayName'], reason))

    print(f"\nDone: {len(created)} created, {len(skipped)} skipped.")
    if skipped:
        print("\nSkipped apps:")
        for name, reason in skipped:
            print(f"  - {name}: {reason}")
    return created


def main():
    """Main function to add apps from CSV."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Add mobile apps to Ad Manager from CSV')
    parser.add_argument('csv_file', help='Path to CSV file with app data')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Google Ad Manager - Add Mobile Applications (CSV)")
    print("=" * 60 + "\n")
    
    apps = load_apps_from_csv(args.csv_file)
    print(f"Loaded {len(apps)} app(s) from {args.csv_file}")
    add_mobile_applications(apps)


if __name__ == '__main__':
    main()
