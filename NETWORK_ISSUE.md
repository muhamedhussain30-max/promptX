# Network Issue - DNS Resolution Blocked

## Problem

Your network is blocking access to `api-inference.huggingface.co`

**Error**: `[Errno -5] No address associated with hostname`

This means DNS resolution is failing - your network firewall or ISP is blocking HuggingFace API.

## Solutions

### Solution 1: Use Deployed Backend (RECOMMENDED)

**Deploy to Render** where internet access is unrestricted:

1. Go to https://dashboard.render.com/
2. Deploy latest commit (6ff1836)
3. Use the deployed backend: `https://promptx-27td.onrender.com`

**Then access via deployed frontend:**
- Deploy frontend to Vercel
- It will connect to Render backend
- Real AI image generation will work!

### Solution 2: Local Development with Mock Mode

For local testing without deploying:

**Your `.env` is now set to mock mode:**
```env
AI_PROVIDER=mock
```

This will:
- ✅ Generate placeholder images instantly
- ✅ Allow you to test game logic
- ✅ Not require internet access
- ❌ Won't generate real AI images

**To test with mock mode:**
```bash
cd backend
# Install dependencies if needed
pip install -r requirements.txt

# Run backend
python -m uvicorn app.main:app --reload --port 8001
```

Then in another terminal:
```bash
cd frontend
npm run dev
```

Visit `http://localhost:5173` and test the game!

### Solution 3: Network Workarounds (Not Recommended)

If you absolutely need to test locally with real AI:

1. **Mobile Hotspot**: Connect to mobile data
2. **VPN**: Use a VPN to bypass network restrictions
3. **Different Network**: Try a different WiFi/network

**However**, deploying to Render is MUCH easier and is required for the final product anyway!

## Why This Happens

Your network (school/office/ISP) is blocking:
- `api-inference.huggingface.co`
- Possibly other AI service domains

Common in:
- Educational institutions
- Corporate networks
- Some ISPs with content filtering

## Recommended Workflow

### For Development:
1. Use **mock mode** locally (already configured)
2. Test game logic, UI, and flow
3. Deploy to Render when ready for real AI

### For Production:
1. Deploy backend to Render
2. Deploy frontend to Vercel
3. Real AI image generation works!

## Current Status

✅ Local `.env` updated to use **mock mode**  
✅ All code pushed to GitHub (commit 6ff1836)  
⚠️ **Deploy to Render to use real AI image generation**

## Testing Local Mock Mode

1. Start backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8001
   ```

2. Start frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Visit http://localhost:5173

4. Images will generate instantly (mock placeholders)

## Deploy to Production

**Backend (Render):**
1. Go to https://dashboard.render.com/
2. Manual Deploy → Deploy latest commit
3. Wait 3-4 minutes

**Frontend (Vercel):**
1. Connect GitHub repo to Vercel
2. Auto-deploy on push, or manual deploy
3. Environment variables already configured in `.env.production`

**Result:**
- ✅ Real AI image generation works
- ✅ No network restrictions
- ✅ Accessible from anywhere

---

**Bottom Line**: Your network blocks HuggingFace. Use mock mode locally OR deploy to Render for real AI! 🚀
