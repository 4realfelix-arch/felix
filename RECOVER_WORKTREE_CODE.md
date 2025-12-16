# Recover Code from Worktrees

## Context
Cursor created multiple worktrees under `/home/stacy/.cursor/worktrees/felix/` instead of working in the main directory `/home/stacy/felix/felix`. Important code changes may be in these worktrees.

## What Was Worked On (May Be Lost)

### 1. Modular Flyout System
- **Files:**
  - `frontend/static/flyouts/flyout-manager.js` - Core flyout management system
  - `frontend/static/flyouts/history-flyout.js` - Built-in history flyout
  - `frontend/static/flyouts/memory-flyout.js` - Built-in memory browser
  - `frontend/static/flyouts/calendar-flyout.js` - Built-in calendar
  - `frontend/static/flyouts/media-gallery-flyout.js` - Extension media gallery
- **Status:** These were created as modular extensions but may not be in main directory

### 2. Authentication System Updates
- **Files:**
  - `server/main.py` - WebSocket token validation, `/api/auth/user` endpoint fix
  - `server/auth.py` - User management endpoints
  - `frontend/index.html` - Login/register modal
  - `frontend/static/app.module.js` - Authentication flow, `checkAuthRequired()`, login modal handling
- **Key Changes:**
  - `/api/auth/user` should return `{"user": None, "auth_enabled": True}` when no token (not 401)
  - WebSocket should validate token from query params
  - Frontend should show login modal when auth enabled and no token

### 3. Admin Dashboard
- **Files:**
  - `frontend/admin.html` - Tabbed interface (Overview, Users, Sessions, Features, Logs)
  - `frontend/static/admin.js` - User management (create, delete, list)
- **Features:**
  - User section for admins to add/delete users
  - Feature management UI (placeholder)
  - User settings persistence

### 4. CSS Updates
- **File:** `frontend/static/style.css`
- **Changes:**
  - Fixed spacing for `.history-header` and `.history-actions`
  - Added styles for new flyout types (media-gallery, memory-browser, music-visualizer, knowledge-explorer)
  - Login modal styles

### 5. Frontend Integration
- **File:** `frontend/index.html`
- **Changes:**
  - Removed old "code editor" and "terminal" flyout tabs
  - Added new flyout tabs (Media Gallery, Memory Browser, Music Visualizer, Knowledge Explorer)
  - Login modal HTML structure
  - Script tags for flyout-manager.js and flyout modules

## Recovery Steps

### Step 1: Find Latest Worktrees
```bash
# List all worktrees
ls -la /home/stacy/.cursor/worktrees/felix/

# Check modification times to find most recent
find /home/stacy/.cursor/worktrees/felix -type f -name "*.js" -o -name "*.py" -o -name "*.html" | xargs ls -lt | head -20
```

### Step 2: Check for Flyout Files
```bash
# Search for flyout-manager.js
find /home/stacy/.cursor/worktrees/felix -name "flyout-manager.js" -type f

# Search for flyout modules
find /home/stacy/.cursor/worktrees/felix -path "*/flyouts/*.js" -type f
```

### Step 3: Compare Files
For each important file, check if it exists in main and compare:
```bash
# Example: Check if flyout-manager.js exists
ls -la /home/stacy/felix/felix/frontend/static/flyouts/flyout-manager.js

# Compare with worktree version
diff /home/stacy/felix/felix/frontend/static/flyouts/flyout-manager.js \
     /home/stacy/.cursor/worktrees/felix/[WORKTREE_NAME]/frontend/static/flyouts/flyout-manager.js
```

### Step 4: Copy Missing Files
If files are missing from main, copy them:
```bash
# Create directories if needed
mkdir -p /home/stacy/felix/felix/frontend/static/flyouts

# Copy flyout files (replace WORKTREE_NAME with actual name)
cp /home/stacy/.cursor/worktrees/felix/[WORKTREE_NAME]/frontend/static/flyouts/*.js \
   /home/stacy/felix/felix/frontend/static/flyouts/
```

### Step 5: Verify Key Changes

#### Check server/main.py
```bash
# Should have WebSocket token validation
grep -A 5 "token.*query" /home/stacy/felix/felix/server/main.py

# Should return auth_enabled without raising 401
grep -A 10 "/api/auth/user" /home/stacy/felix/felix/server/main.py
```

#### Check app.module.js
```bash
# Should have checkAuthRequired() call in init()
grep -A 3 "checkAuthRequired" /home/stacy/felix/felix/frontend/static/app.module.js

# Should have login modal elements cached
grep "loginModal\|loginForm" /home/stacy/felix/felix/frontend/static/app.module.js
```

#### Check index.html
```bash
# Should have login modal
grep -A 5 "loginModal" /home/stacy/felix/felix/frontend/index.html

# Should have flyout-manager.js script tag
grep "flyout-manager.js" /home/stacy/felix/felix/frontend/index.html
```

## Quick Recovery Script

If you find the most recent worktree, you can copy all important files at once:

```bash
# Set the worktree name
WORKTREE="/home/stacy/.cursor/worktrees/felix/[MOST_RECENT_WORKTREE]"
MAIN="/home/stacy/felix/felix"

# Copy flyout files
mkdir -p "$MAIN/frontend/static/flyouts"
cp "$WORKTREE/frontend/static/flyouts"/*.js "$MAIN/frontend/static/flyouts/" 2>/dev/null

# Copy updated frontend files
cp "$WORKTREE/frontend/index.html" "$MAIN/frontend/index.html"
cp "$WORKTREE/frontend/static/app.module.js" "$MAIN/frontend/static/app.module.js"
cp "$WORKTREE/frontend/static/style.css" "$MAIN/frontend/static/style.css"
cp "$WORKTREE/frontend/admin.html" "$MAIN/frontend/admin.html"
cp "$WORKTREE/frontend/static/admin.js" "$MAIN/frontend/static/admin.js"

# Copy server files
cp "$WORKTREE/server/main.py" "$MAIN/server/main.py"
cp "$WORKTREE/server/auth.py" "$MAIN/server/auth.py" 2>/dev/null
```

## What to Tell the AI

When asking to recover code, say:

> "Recover the code from worktrees. Check RECOVER_WORKTREE_CODE.md for details. The main things missing are:
> 1. Modular flyout system (flyout-manager.js and flyout modules)
> 2. Authentication fixes (server/main.py WebSocket token validation, /api/auth/user fix)
> 3. Login modal integration (app.module.js checkAuthRequired, index.html login modal)
> 4. Admin dashboard updates (admin.html, admin.js)
> 5. CSS updates for new flyouts and login modal"

## After Recovery

1. Verify all files are in `/home/stacy/felix/felix`
2. Test that server starts: `cd /home/stacy/felix/felix && python -m server.main`
3. Test that login modal appears when auth is enabled
4. Test that flyouts work (History, Memory, Calendar, Media Gallery)
5. Test admin dashboard user management

## Notes

- Worktrees were cleaned up, but files may still exist if cleanup didn't complete
- Check `.cursor/worktrees/felix/` for any remaining directories
- Most recent work was likely in worktrees: `dma`, `pzt`, `mhr`, `tlu`, `zvi`, `yfi`, `nzq`
- The modular flyout system was the most recent major feature

