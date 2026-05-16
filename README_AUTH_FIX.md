# 🔐 Google Cloud Authentication Fix

## The Problem
Your application was working yesterday but not today because **Google Cloud service account keys expire daily**. This is a common issue where you need to manually update the JSON credentials file every day.

## The Solution
I've implemented **multiple solutions** to eliminate the daily JSON file change requirement:

1. **Application Default Credentials (ADC)** - Automatic token refresh
2. **Smart Error Handling** - Auto-refresh on expiration
3. **Manual Refresh Endpoint** - Refresh without restarting
4. **Automated Scripts** - Scheduled daily refresh

## What I Fixed

### 1. **Automatic Token Refresh** ✅
- Modified `api.py` to use Google Cloud's Application Default Credentials
- Added automatic credential refresh when tokens expire
- Fallback to service account JSON file if ADC fails

### 2. **Smart Error Handling** ✅
- Detects when credentials are expired
- Automatically refreshes the Vision API client
- Retries failed API calls with fresh credentials

### 3. **Dual Authentication Strategy** ✅
- **Primary**: Application Default Credentials (auto-refresh)
- **Fallback**: Service account JSON file (manual)

### 4. **Manual Refresh API** ✅
- New endpoint: `GET /refresh-credentials`
- Refresh credentials without restarting the application
- Useful for manual intervention when needed

### 5. **Automated Refresh Scripts** ✅
- `refresh_credentials.bat` - Windows batch script
- `refresh_credentials.ps1` - PowerShell script
- Can be scheduled to run automatically

## Quick Fix (No Installation Required)

### Option 1: Use the Manual Refresh Endpoint
When your app stops working:
1. Make sure your API is running
2. Visit: `http://localhost:8000/refresh-credentials`
3. This will refresh your credentials automatically

### Option 2: Use the Automated Scripts
1. **Double-click** `refresh_credentials.bat` or `refresh_credentials.ps1`
2. **Schedule it** to run daily using Windows Task Scheduler

## How to Set Up (One-time setup)

### Option 1: Use the Setup Script (Recommended)
```bash
python setup_gcloud_auth.py
```

This script will:
- Check if Google Cloud CLI is installed
- Authenticate you with Google Cloud
- Set up Application Default Credentials
- Configure your project

### Option 2: Manual Setup
```bash
# Install Google Cloud CLI (if not already installed)
# Download from: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set your project
gcloud config set project groovy-cider-469805-i2

# Set up Application Default Credentials
gcloud auth application-default login
```

## What Happens Now

1. **No More Daily Changes**: Credentials automatically refresh
2. **Automatic Recovery**: If tokens expire, the app refreshes them automatically
3. **Better Reliability**: Multiple authentication methods ensure uptime
4. **Fallback Safety**: Still works with your existing JSON file if needed
5. **Manual Control**: You can refresh credentials anytime via API endpoint
6. **Automation**: Scripts can handle daily refresh automatically

## Files Modified

- `api.py` - Added ADC support, automatic refresh, and manual refresh endpoint
- `requirements.txt` - Added `google-auth` dependency
- `setup_gcloud_auth.py` - Helper script for setup
- `refresh_credentials.bat` - Windows batch script for automation
- `refresh_credentials.ps1` - PowerShell script for automation
- `README_AUTH_FIX.md` - This documentation

## Testing

After setup, your application should:
1. Work without daily JSON file changes
2. Automatically handle credential expiration
3. Show "Using Application Default Credentials" in the logs
4. Fall back to service account if ADC fails
5. Allow manual refresh via `/refresh-credentials` endpoint

## Troubleshooting

### If ADC fails:
- The app will automatically fall back to your JSON file
- Check that you're logged into the correct Google account
- Ensure you have access to the project

### If you still have issues:
- Set `BYPASS_VISION_API=true` as environment variable to skip Vision API temporarily
- Check the console logs for detailed error messages
- Use the manual refresh endpoint: `http://localhost:8000/refresh-credentials`

### Quick Daily Fix:
1. **Run the batch script**: Double-click `refresh_credentials.bat`
2. **Use the API endpoint**: Visit `http://localhost:8000/refresh-credentials`
3. **Restart the application** (if all else fails)

## Benefits

✅ **No more daily JSON file changes**  
✅ **Automatic token refresh**  
✅ **Better reliability**  
✅ **Professional authentication handling**  
✅ **Backward compatibility**  
✅ **Manual refresh option**  
✅ **Automated daily refresh**  

## Daily Usage

### Option 1: Fully Automatic (ADC)
- Set up once, works forever
- No manual intervention needed

### Option 2: Semi-Automatic (Scripts)
- Schedule scripts to run daily
- No manual intervention needed

### Option 3: Manual (API Endpoint)
- Visit refresh endpoint when needed
- Quick and easy

Your application should now work consistently without the daily authentication headaches!
