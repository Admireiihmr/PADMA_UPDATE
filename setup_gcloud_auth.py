#!/usr/bin/env python3
"""
Google Cloud Authentication Setup Script
This script helps set up Application Default Credentials to avoid daily JSON file changes.
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} successful")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def check_gcloud_installed():
    """Check if gcloud CLI is installed"""
    try:
        result = subprocess.run(["gcloud", "--version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def main():
    print("🔐 Google Cloud Authentication Setup")
    print("=" * 50)
    
    # Check if gcloud is installed
    if not check_gcloud_installed():
        print("❌ Google Cloud CLI (gcloud) is not installed.")
        print("\nTo install gcloud CLI:")
        print("1. Visit: https://cloud.google.com/sdk/docs/install")
        print("2. Download and install for Windows")
        print("3. Restart your terminal and run this script again")
        return
    
    print("✅ Google Cloud CLI is installed")
    
    # Check current authentication status
    print("\n📋 Checking current authentication status...")
    auth_list = subprocess.run(["gcloud", "auth", "list"], capture_output=True, text=True)
    
    if "ACTIVE" in auth_list.stdout:
        print("✅ You are already authenticated")
        print("Current account:", auth_list.stdout.split("ACTIVE")[0].split()[-1])
    else:
        print("❌ No active authentication found")
        
        # Authenticate with Google Cloud
        print("\n🔑 Authenticating with Google Cloud...")
        print("This will open a browser window for you to sign in.")
        
        if run_command("gcloud auth login", "Google Cloud authentication"):
            print("✅ Authentication successful!")
        else:
            print("❌ Authentication failed. Please try again manually:")
            print("gcloud auth login")
            return
    
    # Set the project
    project_id = "groovy-cider-469805-i2"  # From your JSON file
    print(f"\n🏗️  Setting project to: {project_id}")
    
    if run_command(f"gcloud config set project {project_id}", "Project configuration"):
        print("✅ Project set successfully!")
    else:
        print("❌ Failed to set project")
        return
    
    # Set Application Default Credentials
    print("\n🔐 Setting up Application Default Credentials...")
    print("This will create credentials that automatically refresh.")
    
    if run_command("gcloud auth application-default login", "Application Default Credentials setup"):
        print("✅ Application Default Credentials configured successfully!")
        print("\n🎉 Setup complete! Your application should now work without daily JSON file changes.")
        print("\nThe credentials will automatically refresh when needed.")
    else:
        print("❌ Failed to set up Application Default Credentials")
        print("You can still use the service account JSON file as a fallback.")

if __name__ == "__main__":
    main()
