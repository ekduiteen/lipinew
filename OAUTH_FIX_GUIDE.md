# Google OAuth Fix Guide

## ✅ What's Been Fixed

1. **Backend Updated** — Now has correct Google credentials:
   ```
   GOOGLE_CLIENT_ID=639539366972-9lo9pmuq5g62fa49v7nkclnm6n15o2tj.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=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
   ```

2. **Backend Restarted** — Container restarted with new configuration

3. **Frontend Verified** — Running on localhost:3002 with correct env vars in .env.local

---

## ⚠️ What Needs Your Action: Google Cloud Console

The **redirect_uri_mismatch** error indicates Google Cloud Console doesn't have the correct redirect URIs registered.

### Current Setup
- Frontend runs on: `http://localhost:3002`
- Frontend generates redirect_uri: `http://localhost:3002/auth`
- Backend is at: `http://localhost:8000` (tunneled from remote)

### What Google Cloud Console Needs

You must add these "Authorized redirect URIs" to the OAuth app:

```
http://localhost:3000/auth
http://localhost:3001/auth
http://localhost:3002/auth
```

**Important:** Include the `/auth` path — it's not optional.

---

## Steps to Fix in Google Cloud Console

### 1. Open Google Cloud Console
- Go to https://console.cloud.google.com
- Make sure you're in the correct Google Cloud Project

### 2. Navigate to OAuth Credentials
- In the left sidebar, go to **APIs & Services** → **Credentials**
- Find the OAuth 2.0 Client ID: `639539366972-...`
- Click on it to open the details

### 3. Add/Verify Redirect URIs
Under "Authorized redirect URIs" section:

**Current value (if any):**
- [ ] Check if `http://localhost:3000/auth` exists
- [ ] Check if `http://localhost:3001/auth` exists  
- [ ] Check if `http://localhost:3002/auth` exists

**If any are missing:**
1. Click "Add URI"
2. Paste: `http://localhost:3000/auth`
3. Click "Add URI" again
4. Paste: `http://localhost:3001/auth`
5. Click "Add URI" again
6. Paste: `http://localhost:3002/auth`
7. Scroll down and click **"SAVE"**

### 4. Verify Changes Saved
- Google will show a notification: "OAuth client updated"
- The URIs should now appear in the list

---

## Test the OAuth Flow

### Prerequisites (Verify These Are Running)

**Terminal 1 — SSH Tunnel:**
```bash
ssh -p 41447 -L 8000:localhost:8000 -L 8080:localhost:8080 -L 5001:localhost:5001 -L 5432:localhost:5432 -L 6379:localhost:6379 ekduiteen@202.51.2.50
```
✓ Should show: `ekduiteen@remote-server:~$`

**Terminal 2 — Backend (Remote, via Docker):**
Status: ✓ Running (just restarted)

**Terminal 3 — Frontend:**
Status: ✓ Running on localhost:3002

### Test Steps

1. Open browser to: `http://localhost:3002`

2. Click **"Continue with Google"** button

3. You should be redirected to Google login page
   - ✓ This means `/auth` redirect_uri was accepted

4. Log in with your Google account

5. After login, you should see ONE of these:
   - ✓ **Success**: Redirected to `/onboarding` (new user) or `/home` (returning user)
   - ✗ **Error**: Browser shows JSON error message

### If You Get an Error

Open **DevTools** (F12) → **Network** tab:

1. Click "Continue with Google" again
2. Look for a red POST request to `/api/auth/google`
3. Click it and view the **Response** tab
4. You'll see the error details

**Common errors and fixes:**

- `"Google token exchange failed"` — Backend can't reach Google (network issue)
- `"Failed to fetch Google user info"` — Bad credentials
- `"redirect_uri_mismatch"` — URIs not registered in Google Cloud Console

---

## Timeline

- ✅ **Just now**: Backend updated with correct credentials
- ⏳ **Next**: You update Google Cloud Console (2-3 minutes)
- ⏳ **Then**: Test OAuth flow
- ✅ **Success**: User logs in and sees onboarding screen

---

## Troubleshooting

**"Still getting redirect_uri_mismatch"**
- Wait 5-10 seconds after saving in Google Cloud Console (caching)
- Hard refresh in browser: `Ctrl+Shift+Delete` (clear cache) then `Ctrl+Shift+R`
- Check that the `/auth` path is included in the URIs

**"Frontend not reaching backend"**
- Verify SSH tunnel is still running
- Check `http://localhost:8000/health` returns JSON
- Verify `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000` in `.env.local`

**"Backend not connecting to Google"**
- Check backend logs: `docker logs -f lipi-backend` (from remote via SSH)
- Verify internet connectivity: `curl -I https://oauth2.googleapis.com`

---

## Next Steps

1. **Right now**: Update Google Cloud Console with the redirect URIs above
2. **In 30 seconds**: Reload your browser and test the OAuth flow
3. **On success**: You'll see the onboarding screen and can proceed to build LIPI

---

**Everything else is ready. Just need Google Cloud Console configured. Go! 🚀**
