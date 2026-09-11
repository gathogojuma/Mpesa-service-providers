# TillTrack Database Recovery Guide

If the free PostgreSQL database expires or is deleted, follow these steps to restore service.

## Step 1: Create a New PostgreSQL Database on Render

1. Go to Render dashboard → "New +" → "Postgres"
2. Name: `mpesa-service-db`
3. Database: `tilltrack`
4. User: `tilltrack`
5. Region: Frankfurt (same as backend)
6. Plan: Free
7. Click "Create Database"
8. Wait 1-2 minutes for it to be ready
9. Copy the "Internal Database URL"

## Step 2: Update Backend Environment Variable

1. Go to Render dashboard → `mpesa-service-backend` service
2. Click "Environment" tab
3. Find `DATABASE_URL` and update it with the new Internal Database URL
4. Click "Save Changes"
5. Wait for automatic redeploy (2-3 minutes)

## Step 3: Re-seed the Database

Once the redeploy is complete, visit:
https://mpesa-service-backend.onrender.com/seed-demo-data

You should see a "success" response with 4 users created.

## Step 4: Verify Login

1. Go to https://mpesa-service-dashboard.onrender.com
2. Login with:
   - Phone: +254700000001
   - PIN: 1234
3. Dashboard should load with 0 transactions (fresh database)

## Step 5: Complete

Total time: ~5 minutes. All code, deployment config, and pipeline remain intact.

## Prevention

Before the 30-day expiration:
- Upgrade to a paid PostgreSQL plan on Render (~$7/month)
- Or set a calendar reminder to migrate to another provider
