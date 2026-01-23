# Deployment Guide

## Architecture

```
GitHub (code)
    ↓
┌─────────────────────────────────────┐
│           Vercel (Frontend)          │
│         Next.js + React PWA          │
│     https://your-app.vercel.app      │
└─────────────────────────────────────┘
                ↓ API calls
┌─────────────────────────────────────┐
│          Render (Backend)            │
│            Python FastAPI            │
│    https://your-app.onrender.com     │
└─────────────────────────────────────┘
                ↓ Database
┌─────────────────────────────────────┐
│         Supabase (Database)          │
│            PostgreSQL                │
└─────────────────────────────────────┘
```

## Step 1: Push to GitHub

```bash
# In the project root
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/whatsup-app.git
git push -u origin main
```

## Step 2: Deploy Backend to Render

1. Go to [render.com](https://render.com) and sign up/login
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: whatsup-backend
   - **Region**: Frankfurt (EU)
   - **Branch**: main
   - **Root Directory**: backend
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

5. Add Environment Variables (in Render dashboard):
   ```
   ENVIRONMENT=production
   DEBUG=false
   ANTHROPIC_API_KEY=your_key
   OPENAI_API_KEY=your_key
   GOOGLE_API_KEY=your_key
   PERPLEXITY_API_KEY=your_key
   SERPAPI_API_KEY=your_key
   SUPABASE_URL=your_url
   SUPABASE_KEY=your_key
   ALLOWED_ORIGINS=https://your-app.vercel.app
   ```

6. Click **Create Web Service**
7. Note your backend URL: `https://whatsup-backend.onrender.com`

## Step 3: Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and sign up/login
2. Click **Add New** → **Project**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: frontend

5. Add Environment Variable:
   ```
   NEXT_PUBLIC_API_URL=https://whatsup-backend.onrender.com
   ```

6. Click **Deploy**

## Step 4: Configure Supabase

1. Go to [supabase.com](https://supabase.com)
2. Create a new project (or use existing)
3. Get your credentials from **Settings** → **API**:
   - Project URL
   - anon/public key
4. Add these to your Render backend environment variables

## Step 5: Update CORS

In Render, update `ALLOWED_ORIGINS` to include your Vercel URL:
```
ALLOWED_ORIGINS=https://your-app.vercel.app
```

## Costs

| Service | Plan | Cost |
|---------|------|------|
| GitHub | Free | $0 |
| Vercel | Hobby | $0 |
| Render | Free | $0 |
| Supabase | Free | $0 |
| **Total** | | **$0/month** |

## Notes

- **Render Free Tier**: Backend spins down after 15 min inactivity. First request after inactivity takes ~30 seconds (cold start).
- **Vercel**: Unlimited deployments, automatic HTTPS
- **Supabase Free Tier**: 500MB database, 2GB bandwidth

## Local Development

```bash
# Frontend
cd frontend
npm install --legacy-peer-deps
npm run dev

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Then edit with your keys
uvicorn app.main:app --reload
```
