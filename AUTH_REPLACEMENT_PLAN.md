# Replace Felix Auth System with Cookie-Based Auth (OpenWebUI Style)

## Goal
Replace the current token-based authentication with a seamless cookie-based system like OpenWebUI uses. No more manual token copying - just login once and you're done.

## Current Problems
1. **Manual token management** - Users have to copy tokens from localStorage
2. **No automatic redirects** - App doesn't auto-redirect to login when needed
3. **WebSocket auth via URL params** - Tokens exposed in URLs
4. **Admin dashboard disconnected** - Requires separate token entry
5. **No session persistence** - Have to re-authenticate frequently

## New System Overview
- **HTTP-only cookies** for session management (secure, browser handles automatically)
- **Automatic redirects** to login page when unauthenticated
- **WebSocket auth via cookies** (not URL params)
- **Long-lived sessions** with auto-refresh (30 days default)
- **Unified experience** - admin dashboard uses same session

---

## Step-by-Step Implementation Plan

### Phase 1: Backend Cookie Authentication (server/auth.py + server/main.py)

#### 1.1 Update AuthManager to support cookies (server/auth.py)
**What to change:**
- Add method `create_session_cookie(username: str, response: Response) -> str`
- Add method `get_session_from_cookie(request: Request) -> Optional[AuthSession]`
- Increase `TOKEN_EXPIRY_HOURS` from 24 to 720 (30 days)

**Exact code to add:**
```python
# Add after the AuthManager.__init__ method (around line 80)

def create_session_cookie(self, username: str, response: Response) -> str:
    """Create a session and set it as a cookie. Returns the token."""
    token = _generate_token()
    now = time.time()
    expires_at = now + (TOKEN_EXPIRY_HOURS * 3600)
    
    session = AuthSession(
        token=token,
        username=username,
        created_at=now,
        expires_at=expires_at,
        ip_address=""
    )
    
    self._sessions[token] = session
    self._save_sessions()
    
    # Set HTTP-only cookie
    response.set_cookie(
        key="felix_session",
        value=token,
        max_age=TOKEN_EXPIRY_HOURS * 3600,  # 30 days in seconds
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True if using HTTPS
        path="/"
    )
    
    logger.info("session_cookie_created", username=username)
    return token

def get_session_from_cookie(self, request: Request) -> Optional[AuthSession]:
    """Get session from cookie."""
    token = request.cookies.get("felix_session")
    if not token:
        return None
    return self.validate_session(token)
```

**File location:** `/home/stacy/felix/felix/server/auth.py`
**Insert after:** Line ~80 (after `__init__` method)

#### 1.2 Update login endpoint to set cookies (server/main.py)
**What to change:**
- Modify `/api/auth/login` endpoint to call `create_session_cookie` instead of just returning token
- Keep token in response body for backwards compatibility

**Find this code (around line 135):**
```python
@app.post("/api/auth/login")
async def login(credentials: LoginRequest):
    """Login endpoint."""
    if not settings.enable_auth:
        return {"error": "Authentication is disabled"}, 400
    
    success, result = auth_manager.login(
        credentials.username, 
        credentials.password
    )
    
    if success:
        return {"token": result, "username": credentials.username}
    return {"error": result}, 401
```

**Replace with:**
```python
@app.post("/api/auth/login")
async def login(credentials: LoginRequest, response: Response):
    """Login endpoint - sets session cookie."""
    if not settings.enable_auth:
        return {"error": "Authentication is disabled"}, 400
    
    success, result = auth_manager.login(
        credentials.username, 
        credentials.password
    )
    
    if success:
        token = result
        # Set cookie for browser
        auth_manager.create_session_cookie(credentials.username, response)
        # Also return token for backwards compatibility
        return {"token": token, "username": credentials.username}
    return {"error": result}, 401
```

**File location:** `/home/stacy/felix/felix/server/main.py`
**Line:** ~135

#### 1.3 Add cookie-based auth dependency (server/main.py)
**What to add:**
- New dependency function `get_current_user_from_cookie` 
- Use alongside or replace existing token-based auth

**Add this code after the `require_auth` function (around line 108):**
```python
def get_current_user_from_cookie(
    request: Request,
    settings: Settings = Depends(get_settings)
) -> Optional[str]:
    """Get current user from session cookie. Returns username or None."""
    if not settings.enable_auth:
        return None  # Auth disabled, no user required
    
    session = auth_manager.get_session_from_cookie(request)
    if session:
        return session.username
    return None

def require_auth_cookie(
    request: Request,
    settings: Settings = Depends(get_settings)
) -> str:
    """Require authentication via cookie. Raises 401 if not authenticated."""
    username = get_current_user_from_cookie(request, settings)
    if username is None and settings.enable_auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    return username
```

**File location:** `/home/stacy/felix/felix/server/main.py`
**Insert after:** Line ~108 (after `require_auth` function)

#### 1.4 Update WebSocket to accept cookies (server/main.py)
**What to change:**
- Modify WebSocket endpoint to read `felix_session` cookie instead of `token` query param
- Keep query param as fallback for backwards compatibility

**Find this code (around line 350):**
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """WebSocket endpoint for real-time voice interaction."""
    settings = get_settings()
    
    # Validate authentication if enabled
    if settings.enable_auth:
        if not token:
            await websocket.close(code=1008, reason="Authentication required")
            return
        session = auth_manager.validate_session(token)
        if not session:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return
        username = session.username
    else:
        username = None
```

**Replace with:**
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """WebSocket endpoint for real-time voice interaction."""
    settings = get_settings()
    
    # Validate authentication if enabled
    if settings.enable_auth:
        # Try cookie first, then fallback to query param
        session_token = websocket.cookies.get("felix_session") or token
        
        if not session_token:
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        session = auth_manager.validate_session(session_token)
        if not session:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return
        username = session.username
    else:
        username = None
```

**File location:** `/home/stacy/felix/felix/server/main.py`
**Line:** ~350

#### 1.5 Add logout endpoint with cookie clearing (server/main.py)
**What to add:**
- New `/api/auth/logout` endpoint that clears the cookie

**Add this code after the login endpoint (around line 150):**
```python
@app.post("/api/auth/logout")
async def logout(response: Response, request: Request):
    """Logout endpoint - clears session cookie."""
    # Get token from cookie
    token = request.cookies.get("felix_session")
    if token:
        auth_manager.logout(token)
    
    # Clear cookie
    response.delete_cookie(key="felix_session", path="/")
    return {"success": True}
```

**File location:** `/home/stacy/felix/felix/server/main.py`
**Insert after:** Line ~150 (after login endpoint)

---

### Phase 2: Frontend Cookie Support (frontend/static/app.module.js)

#### 2.1 Remove manual token management from localStorage
**What to change:**
- Remove `localStorage.getItem('felix-auth-token')` code
- Remove token from WebSocket URL
- Browser will send cookie automatically

**Find this code (around line 80):**
```javascript
const token = localStorage.getItem('felix-auth-token');
let wsUrl = `ws://${window.location.host}/ws`;
if (token) {
    wsUrl += `?token=${token}`;
}
ws = new WebSocket(wsUrl);
```

**Replace with:**
```javascript
// No need to manually get token - browser sends cookie automatically
const wsUrl = `ws://${window.location.host}/ws`;
ws = new WebSocket(wsUrl);
```

**File location:** `/home/stacy/felix/felix/frontend/static/app.module.js`
**Line:** ~80

#### 2.2 Update login handler to not store token (frontend/static/app.module.js)
**What to change:**
- Remove `localStorage.setItem('felix-auth-token', ...)` after login
- Cookie is set by server, no need to store manually

**Find this code (around line 250):**
```javascript
async function handleLogin(username, password) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('felix-auth-token', data.token);
            hideLoginModal();
            connect();
        } else {
            // Show error
        }
    }
}
```

**Replace with:**
```javascript
async function handleLogin(username, password) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
            credentials: 'include'  // Important: include cookies
        });
        
        if (response.ok) {
            // Cookie is set automatically by browser
            // No need to manually store token
            hideLoginModal();
            connect();
        } else {
            const data = await response.json();
            showError(data.error || 'Login failed');
        }
    } catch (error) {
        showError('Login request failed');
    }
}
```

**File location:** `/home/stacy/felix/felix/frontend/static/app.module.js`
**Line:** ~250

#### 2.3 Update checkAuthRequired to use cookies (frontend/static/app.module.js)
**What to change:**
- Remove token header, browser sends cookie automatically
- Add `credentials: 'include'` to fetch calls

**Find this code (around line 200):**
```javascript
async function checkAuthRequired() {
    try {
        const token = localStorage.getItem('felix-auth-token');
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch('/api/auth/user', { headers });
```

**Replace with:**
```javascript
async function checkAuthRequired() {
    try {
        const response = await fetch('/api/auth/user', {
            credentials: 'include'  // Browser sends cookie automatically
        });
```

**File location:** `/home/stacy/felix/felix/frontend/static/app.module.js`
**Line:** ~200

#### 2.4 Add logout button and handler (frontend/static/app.module.js)
**What to add:**
- Logout function that calls `/api/auth/logout`
- Button in UI (add to index.html)

**Add this function:**
```javascript
async function handleLogout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
        
        // Reload page to trigger re-authentication
        window.location.reload();
    } catch (error) {
        console.error('Logout failed:', error);
    }
}

// Export for use in HTML
window.handleLogout = handleLogout;
```

**File location:** `/home/stacy/felix/felix/frontend/static/app.module.js`
**Add at end of file:** After other functions

---

### Phase 3: Update Admin Dashboard (frontend/admin.js)

#### 3.1 Remove manual token input and use cookies (frontend/static/admin.js)
**What to change:**
- Remove token input field functionality
- Use cookies automatically
- Remove localStorage token storage

**Find this code (around line 5-10):**
```javascript
const tokenKey = 'felix-admin-token';
let adminToken = localStorage.getItem(tokenKey) || '';

const tokenInput = document.getElementById('tokenInput');
const saveTokenBtn = document.getElementById('saveToken');

if (tokenInput && adminToken) {
    tokenInput.value = adminToken;
}
```

**Replace with:**
```javascript
// No need for manual token management - using cookies
// Keep variables for backwards compatibility but don't use them
const tokenInput = document.getElementById('tokenInput');
const saveTokenBtn = document.getElementById('saveToken');

// Hide token input if auth is enabled (we use cookies)
if (tokenInput) {
    tokenInput.style.display = 'none';
}
if (saveTokenBtn) {
    saveTokenBtn.style.display = 'none';
}
```

**File location:** `/home/stacy/felix/felix/frontend/static/admin.js`
**Line:** ~5-10

#### 3.2 Update fetchAdmin to use cookies (frontend/static/admin.js)
**What to change:**
- Remove manual Authorization header
- Add `credentials: 'include'`

**Find this code (around line 115):**
```javascript
async function fetchAdmin(path, options = {}) {
    const headers = { ...options.headers };
    
    if (adminToken) {
        headers['Authorization'] = `Bearer ${adminToken}`;
    }
    
    const res = await fetch(path, { ...options, headers });
```

**Replace with:**
```javascript
async function fetchAdmin(path, options = {}) {
    const res = await fetch(path, {
        ...options,
        credentials: 'include'  // Browser sends cookie automatically
    });
```

**File location:** `/home/stacy/felix/felix/frontend/static/admin.js`
**Line:** ~115

#### 3.3 Update admin.html UI (frontend/admin.html)
**What to change:**
- Remove token input field
- Add "Login" redirect message if not authenticated

**Find this code (around line 524):**
```html
<input id="tokenInput" type="password" placeholder="Enter your login token or admin: felix2024">
<button id="saveToken" class="btn btn-primary">Connect</button>
```

**Replace with:**
```html
<div id="authMessage" style="display: none; padding: 12px; background: var(--admin-warning); border-radius: 8px; margin-right: 12px;">
  Please <a href="/" style="color: white; text-decoration: underline;">login on main app</a> first
</div>
```

**File location:** `/home/stacy/felix/felix/frontend/admin.html`
**Line:** ~524

---

### Phase 4: Update Index.html UI (frontend/index.html)

#### 4.1 Add logout button to main app (frontend/index.html)
**What to add:**
- Logout button in settings or header

**Find the settings panel (around line 200) and add:**
```html
<!-- Add after other settings buttons -->
<button id="logoutBtn" class="btn-secondary" onclick="handleLogout()" style="display: none;">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
    <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
  </svg>
  Logout
</button>
```

**File location:** `/home/stacy/felix/felix/frontend/index.html`
**Add in settings panel:** Around line 200

#### 4.2 Show/hide logout button based on auth status (frontend/static/app.module.js)
**What to add:**
- Show logout button only when auth is enabled and user is logged in

**Add this code in the `checkAuthRequired` function after successful auth check:**
```javascript
// Show logout button if authenticated
const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn && data.authenticated) {
    logoutBtn.style.display = 'block';
}
```

**File location:** `/home/stacy/felix/felix/frontend/static/app.module.js`
**Add in:** `checkAuthRequired` function after line ~215

---

### Phase 5: Testing Steps

#### 5.1 Test with auth disabled (ENABLE_AUTH=false)
1. Set `ENABLE_AUTH=false` in `.env`
2. Restart Felix: `./run.sh`
3. Open http://localhost:8000
4. Should work immediately, no login required
5. Admin dashboard should work with token: `felix-admin-2024`

#### 5.2 Test with auth enabled (ENABLE_AUTH=true)
1. Set `ENABLE_AUTH=true` in `.env`
2. Restart Felix: `./run.sh`
3. Open http://localhost:8000
4. Should show login modal automatically
5. Login with: `admin` / `felix2024`
6. Should connect immediately without token copy/paste
7. Close browser and reopen - should NOT ask for login again (cookie persists)
8. Open admin dashboard - should work automatically (same cookie)
9. Click logout - should clear session and require re-login

#### 5.3 Test WebSocket with cookies
1. Open browser DevTools → Network → WS tab
2. Connect to app
3. Check WebSocket connection - should NOT have `?token=` in URL
4. Check cookies - should see `felix_session` cookie

#### 5.4 Test session expiration
1. Login
2. Wait for cookie to expire (or manually delete cookie in DevTools)
3. Try to use app - should show login modal
4. Re-login - should work again

---

### Phase 6: Cleanup (Optional)

#### 6.1 Remove old token-based code
Once everything works with cookies:
- Remove `token` query parameter from WebSocket endpoint
- Remove localStorage token storage code completely
- Remove manual Authorization header code
- Keep backwards compatibility or fully remove old system

#### 6.2 Update documentation
- Update README.md with new auth flow
- Update API.md to document cookie-based auth
- Add note about session duration (30 days)

---

## Summary of Changes

### Backend Files to Edit:
1. `/home/stacy/felix/felix/server/auth.py` - Add cookie methods
2. `/home/stacy/felix/felix/server/main.py` - Update endpoints and WebSocket

### Frontend Files to Edit:
1. `/home/stacy/felix/felix/frontend/static/app.module.js` - Remove token management, use cookies
2. `/home/stacy/felix/felix/frontend/static/admin.js` - Remove token input, use cookies
3. `/home/stacy/felix/felix/frontend/admin.html` - Update UI
4. `/home/stacy/felix/felix/frontend/index.html` - Add logout button

### Key Concepts:
- **HTTP-only cookies** = Browser handles automatically, more secure
- **credentials: 'include'** = Tell fetch() to send cookies with requests
- **response.set_cookie()** = Server sets cookie in browser
- **request.cookies.get()** = Server reads cookie from request
- **No more localStorage** = No manual token storage needed
- **No more token in URL** = Cookies sent automatically with every request

### Migration Path:
- Phase 1-2: Implement cookie auth alongside token auth (backwards compatible)
- Phase 3-4: Update UIs to use cookies
- Phase 5: Test thoroughly
- Phase 6: Remove old token code (optional)

---

## Important Notes for Implementation

1. **Add Response and Request imports** at top of files:
   ```python
   from fastapi import Response, Request
   ```

2. **Test incrementally** - Don't change everything at once:
   - Add cookie methods first
   - Test they work alongside tokens
   - Then remove token code

3. **Keep ENABLE_AUTH=false** while developing to avoid auth issues

4. **Browser cache** - Clear cookies between tests:
   - DevTools → Application → Cookies → Delete all

5. **WebSocket cookies** - Starlette supports cookies in WebSocket handshake automatically

6. **Session duration** - 30 days is standard, adjust `TOKEN_EXPIRY_HOURS` if needed

7. **HTTPS** - Set `secure=True` in cookie if using HTTPS in production

This plan should be straightforward to follow step-by-step. Each section has exact file locations, line numbers, and complete code to add/replace.
