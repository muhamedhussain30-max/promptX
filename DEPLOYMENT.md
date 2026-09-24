# PromptX Deployment Guide

## Current Issues & Fixes

### Issue: HuggingFace API 404 Error

**Problem**: Render is still using old code with deprecated HuggingFace API endpoint

**Root Cause**: Render auto-deploy may be disabled or not picking up changes

**Solution**: Manual deployment required

## Deployment Steps

### 1. Verify Local Code (Already Done ✅)

All fixes have been committed to main branch:
- ✅ Commit f0e12c8: HuggingFace Inference Providers API
- ✅ Commit eebe67c: Switch to Stable Diffusion 2.1
- ✅ Commit 1864dc6: Update huggingface-hub to 0.27.0
- ✅ Commit 8c40a5f: Fix API parameters

### 2. Deploy to Render (REQUIRED)

**Option A: Manual Deploy (Recommended)**
1. Go to https://dashboard.render.com/
2. Select your PromptX service
3. Click "Manual Deploy" → "Deploy latest commit"
4. Wait for build to complete (2-3 minutes)

**Option B: Clear Cache & Deploy**
1. Go to https://dashboard.render.com/
2. Select your PromptX service  
3. Go to "Settings" tab
4. Click "Clear build cache & deploy"
5. Wait for build to complete

### 3. Verify Deployment

After deployment completes:

1. **Check Health Endpoint**:
   ```bash
   curl https://promptx-27td.onrender.com/api/health
   ```
   Expected response:
   ```json
   {"status":"ok","version":"1.0.0","provider":"huggingface"}
   ```

2. **Check Logs** in Render dashboard:
   - Should see `huggingface_hub` version 0.27.0 installed
   - No more 404 errors from old API endpoint
   - Image generation should work

3. **Test in Game**:
   - Start a game
   - Submit a prompt
   - Image should generate successfully

## Environment Variables (Already Set ✅)

Required environment variables in Render:
- `AI_PROVIDER=huggingface`
- `HF_TOKEN=<your-huggingface-token>`
- `SECRET_KEY=<your-secret-key>`
- `ALLOWED_ORIGINS=*`

## Technical Details

### What Changed

1. **API Client Initialization**:
   ```python
   # Old (deprecated)
   client = InferenceClient(token=settings.hf_token)
   
   # New (working)
   client = InferenceClient(api_key=settings.hf_token)
   ```

2. **API Call with Provider Routing**:
   ```python
   # Added provider parameter
   client.text_to_image(
       prompt,
       model=IMAGE_GEN_MODEL,
       provider="auto",  # Routes to best provider
       ...
   )
   ```

3. **Model Change**:
   - From: `black-forest-labs/FLUX.1-schnell`
   - To: `stabilityai/stable-diffusion-2-1`
   - Reason: Better availability on free tier

4. **SDK Update**:
   - From: `huggingface-hub>=0.22.2`
   - To: `huggingface-hub>=0.27.0`
   - Reason: Supports new Inference Providers API

## Troubleshooting

### Still Getting 404 Errors?

Check Render logs for API endpoint being used:
- ❌ Bad: `https://huggingface.co/api/inference/models/...`
- ✅ Good: New SDK handles routing internally

If still seeing old endpoint:
1. Render didn't deploy new code
2. Clear build cache and redeploy
3. Check commit hash in Render matches latest (f0e12c8)

### Rate Limiting?

HuggingFace free tier has limits:
- If you get 429 errors, wait a few minutes
- Consider upgrading HuggingFace account for higher limits

### Image Generation Slow?

Stable Diffusion 2.1 takes ~10-20 seconds:
- This is normal for free tier
- Can optimize by reducing steps (currently 20)
- Or upgrade to paid inference providers

## Next Steps After Deploy Works

1. Test full game flow with multiple players
2. Monitor for any errors in Render logs
3. Consider switching back to FLUX if preferred (once API confirmed working)
4. Deploy frontend to Vercel if not already done

## Support

If issues persist after manual deployment:
- Check Render build logs for errors
- Verify commit hash deployed matches f0e12c8
- Ensure all environment variables are set correctly
