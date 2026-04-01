#!/usr/bin/env python3
"""
Script to add mobile applications to Google Ad Manager account.

This script uses the MobileApplicationService API to create and claim
mobile applications for targeting within your Ad Manager network.
"""

import sys
from googleads import ad_manager


def add_mobile_applications(apps_data):
    """
    Add mobile applications to Ad Manager account.
    
    Args:
        apps_data (list): List of dicts containing app information.
                         Each dict should have:
                         - display_name: str (app display name, max 80 chars)
                         - app_store: str (e.g., "GOOGLE_PLAY", "APPLE_APP_STORE")
                         - app_store_id: str (e.g., bundle ID, package name)
    
    Returns:
        list: Created MobileApplication objects
    """
    # Initialize the Ad Manager client
    ad_manager_client = ad_manager.AdManagerClient.LoadFromStorage()
    mobile_app_service = ad_manager_client.GetService('MobileApplicationService', version='v202602')
    
    # Prepare mobile applications
    mobile_applications = []
    for app in apps_data:
        mobile_app = {
            'displayName': app['display_name'],
            'appStore': app['app_store'],
            'appStoreId': app['app_store_id'],
        }
        mobile_applications.append(mobile_app)
    
    try:
        # Create the mobile applications
        result = mobile_app_service.createMobileApplications(mobile_applications)
        
        if result:
            print(f"✓ Successfully created {len(result)} mobile application(s):\n")
            for app in result:
                print(f"  • {app['displayName']} (ID: {app['id']})")
                print(f"    App Store: {app['appStore']}")
                print(f"    External ID: {app['appStoreId']}\n")
            return result
        else:
            print("No applications were created.")
            return None
            
    except Exception as e:
        print(f"✗ Error creating mobile applications: {e}")
        sys.exit(1)


def main():
    """Main function to demonstrate adding mobile apps."""
    
    # Example: Add mobile applications
    # Replace with your actual app information
    apps_to_add = [
        {
            'display_name': 'My First App',
            'app_store': 'GOOGLE_PLAY',
            'app_store_id': 'com.example.firstapp'
        },
        {
            'display_name': 'My iOS App',
            'app_store': 'APPLE_APP_STORE',
            'app_store_id': 'com.example.iosapp'
        },
        {
            'display_name': 'Another Android App',
            'app_store': 'GOOGLE_PLAY',
            'app_store_id': 'com.example.anotherapp'
        }
    ]
    
    print("=" * 60)
    print("Google Ad Manager - Add Mobile Applications")
    print("=" * 60 + "\n")
    
    add_mobile_applications(apps_to_add)


if __name__ == '__main__':
    main()
