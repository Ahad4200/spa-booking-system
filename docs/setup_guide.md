# Spa Booking System Setup Guide

## Prerequisites
- Python 3.11+
- PostgreSQL (via Supabase)
- Twilio Account
- OpenAI API Key
- Domain with SSL (for production)

## Step 1: Clone and Setup
```bash
git clone <your-repo>
cd spa-booking-system
```

## Step 2: Database Setup (Supabase)
1. Create a new Supabase project
2. Run SQL scripts in order:
   ```bash
   database/01_create_tables.sql
   database/02_create_functions.sql
   database/03_create_indexes.sql
   ```

## Step 3: Environment Configuration
1. Copy `.env.example` to `.env`
2. Fill in all required values:
   - Twilio credentials
   - OpenAI API key
   - Supabase URL and keys

## Step 4: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

## Step 5: Configure Twilio
1. Buy an Italian phone number (+39)
2. Configure webhooks:
   - Voice URL: `https://your-domain.com/webhook/incoming-call`
   - Status Callback: `https://your-domain.com/webhook/call-status`

## Step 6: Run Development Server
```bash
python app.py
```

## Step 7: Deploy to Production
Use Docker:
```bash
cd deployment
docker-compose up -d
```

Or deploy to cloud:
- Railway.app
- Render.com
- AWS/GCP/Azure