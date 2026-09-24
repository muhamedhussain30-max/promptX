# PromptX Troubleshooting Guide

## Register/Login Failed Issue

### Problem
Login and registration are failing in the deployed application.

### Root Causes & Solutions

#### 1. **Backend Not Deployed** ❌
**Symptom**: Frontend can't connect to API endpoints
**Solution**: Deploy to Render manually

1. Go to https://dashboard.render.com/
2. Select your PromptX service
3. Click "Manual Deploy" → "Deploy latest commit"
4. Wait for deployment to complete

#### 2. **Environment Variables Missing** ⚠️
**Check Render Environment Variables**:
- `SECRET_KEY` - Required for JWT tokens
- `ALLOWED_ORIGINS` - Should include your frontend URL
- `DATABASE_URL` - Should be set automatically by Render

**To Verify**:
1. Go to Render dashboard
2. Select your service
3. Go to "Environment" tab
4. Ensure all variables are set

#### 3. **Database Not Initialized** ⚠️
**Symptom**: 500 errors or "table doesn't exist"
**Solution**: The backend auto-creates tables on startup, but verify:

```bash
# Check Render logs for:
"Creating tables for SQLite database..."
"Tables created successfully"
```

#### 4. **CORS Issues** 🌐
**Symptom**: Browser console shows CORS errors
**Solution**: Verify `ALLOWED_ORIGINS` in Render includes:
- Your Vercel domain
- `*` (for development - not recommended for production)

Example:
```
ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```

#### 5. **Frontend Environment Variables** 🔧
**Check these files exist**:
- `frontend/.env.production` (for Vercel deployment)
- `frontend/.env.local` (for local development)

**Should contain**:
```env
# .env.production (Vercel)
VITE_API_URL=https://promptx-27td.onrender.com
VITE_WS_URL=wss://promptx-27td.onrender.com

# .env.local (Local dev)
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

## Testing Login/Registration

### On Deployed Site (Vercel)

1. **Open Browser DevTools** (F12)
2. **Go to Network tab**
3. **Try to register/login**
4. **Check the request**:
   - Should go to `https://promptx-27td.onrender.com/api/auth/register` or `/login`
   - Status code 200 = success
   - Status code 404 = backend not deployed
   - Status code 500 = server error (check Render logs)
   - CORS error = ALLOWED_ORIGINS not set

### Test Backend Directly

```bash
# Test health endpoint
curl https://promptx-27td.onrender.com/api/health

# Expected response:
{"status":"ok","version":"1.0.0","provider":"huggingface"}

# Test registration
curl -X POST https://promptx-27td.onrender.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test123!",
    "display_name": "Test User"
  }'
```

## Common Error Messages

### "Unable to connect" or Network Error
- **Cause**: Backend not deployed or wrong URL
- **Fix**: Deploy backend to Render, verify VITE_API_URL

### "401 Unauthorized"
- **Cause**: Wrong credentials
- **Fix**: Try registering a new account first

### "409 Conflict" - Username already taken
- **Cause**: User already exists
- **Fix**: Try a different username or login instead

### "500 Internal Server Error"
- **Cause**: Backend error (database, missing env vars)
- **Fix**: Check Render logs for detailed error message

### CORS Error in Browser Console
```
Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy
```
- **Cause**: ALLOWED_ORIGINS not configured
- **Fix**: Add your frontend URL to ALLOWED_ORIGINS in Render

## Quick Diagnostic Checklist

Run through this checklist:

- [ ] Backend deployed to Render (check dashboard)
- [ ] Backend health endpoint returns 200 OK
- [ ] Environment variables set in Render
- [ ] Frontend .env.production has correct Render URL
- [ ] Frontend deployed to Vercel
- [ ] Browser network tab shows requests going to Render URL
- [ ] No CORS errors in browser console

## Still Not Working?

### 1. Check Render Logs
```
1. Go to Render dashboard
2. Select your service
3. Click "Logs" tab
4. Look for errors around auth endpoints
```

### 2. Check Browser Console
```
F12 → Console tab
Look for:
- Network errors
- CORS errors
- 404/500 responses
```

### 3. Manual Test Backend
Use the curl commands above to verify backend is working

### 4. Redeploy Everything
Sometimes a clean deploy fixes issues:
```
1. Render: "Clear build cache & deploy"
2. Vercel: Redeploy from dashboard
3. Clear browser cache
4. Try again
```

## Local Development Setup

If you want to run locally for testing:

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Now visit http://localhost:5173 and test!
