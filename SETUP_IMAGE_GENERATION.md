# Image Generation Setup Guide

## What's New

Felix now has **full image generation capabilities** integrated via ComfyUI! 🎨

### Features Added Today (Dec 2, 2024)
- ✅ ComfyUI embedded as a service (runs on port 8188)
- ✅ 4 new image generation tools available
- ✅ Auto-start on-demand (starts when you ask for images)
- ✅ Health monitoring via `/health` endpoint
- ✅ ChatGPT-style message actions (copy, edit, regenerate, speak, save)
- ✅ Total 55 tools registered (51 base + 4 image)

## Quick Start

### 1. Download the Model (First Time Only)

The SD 1.5 model is ~7.2GB and **not** included in the repo. Download it:

```bash
cd /home/stacy/felix/felix/comfy/models/checkpoints
huggingface-cli download runwayml/stable-diffusion-v1-5 v1-5-pruned.safetensors --local-dir . --local-dir-use-symlinks False
```

This will take 3-5 minutes depending on your connection.

### 2. Start Felix

```bash
cd /home/stacy/felix/felix
./run.sh
```

Felix will start on `http://localhost:8000`. ComfyUI will auto-start when needed.

### 3. Generate Images

Just talk to Felix naturally:

- "Generate an image of a cat astronaut in space"
- "Create a cyberpunk cityscape at night"
- "Make me a picture of a fantasy dragon"

Felix will:
1. Auto-start ComfyUI if not running
2. Queue your image generation
3. Return the image URL when complete

## Image Tools Available

1. **`generate_image(prompt, ...)`** - Main text-to-image tool
   - Supports custom size (default 512x512)
   - Configurable steps, CFG scale
   - Negative prompts for quality

2. **`image_service_status()`** - Check if ComfyUI is running

3. **`start_image_service()`** - Manually start ComfyUI

4. **`stop_image_service()`** - Manually stop ComfyUI

## Architecture

```
Felix Voice Agent (port 8000)
    ├── 51 Base Tools (weather, web, memory, music, etc.)
    └── ComfyUIService (port 8188)
        ├── Auto-start on first image request
        ├── Subprocess management (clean shutdown)
        ├── Health monitoring
        └── 4 Image Generation Tools
```

## Model Options

Currently using **Stable Diffusion 1.5** (fast, lightweight, works everywhere).

### Future Options:
- **FLUX** - Higher quality, requires more VRAM
- **SDXL** - Better than SD 1.5, more VRAM
- **Qwen-VL** - Multimodal (text + vision)

We can swap models anytime - just download to `comfy/models/checkpoints/` and update the workflow in `server/tools/builtin/image_tools.py`.

## Troubleshooting

### "Image service not available"
ComfyUI failed to start. Check:
```bash
# Test manual start
cd /home/stacy/felix/felix/comfy
python main.py --listen 127.0.0.1 --port 8188
```

### "Model not found"
Download the model (see step 1 above).

### "400 Bad Request"
The workflow might not match your ComfyUI version. The default workflow is in `server/tools/builtin/image_tools.py` - you can export a new one from ComfyUI using "Save (API Format)".

### Check Service Status
```bash
curl http://localhost:8000/health | jq
```

Should show:
```json
{
  "status": "ok",
  "comfyui": "running"  // or "stopped" if not started yet
}
```

## Advanced: Custom Workflows

1. Open ComfyUI: `http://localhost:8188`
2. Enable Dev Mode (gear icon → Dev Mode)
3. Create your workflow
4. Save (API Format) → downloads `workflow_api.json`
5. Update `DEFAULT_TEXT2IMG_WORKFLOW` in `server/tools/builtin/image_tools.py`

## Files Modified/Added

### New Files:
- `server/comfy_service.py` - ComfyUI lifecycle manager
- `server/tools/builtin/image_tools.py` - 4 image tools
- `comfy/` - Full ComfyUI installation (~500 files)

### Modified Files:
- `server/main.py` - Added ComfyUI startup/shutdown hooks
- `frontend/static/app.module.js` - Enhanced message actions
- `frontend/static/style.css` - User message action buttons
- `.gitignore` - Exclude models and large files

## What's Next?

Potential improvements:
- [ ] Frontend image gallery
- [ ] img2img support (edit existing images)
- [ ] Inpainting (fix parts of images)
- [ ] ControlNet (pose/depth control)
- [ ] Multiple models (FLUX, SDXL)
- [ ] Image history/favorites

## Notes

- ComfyUI models are **NOT** in the git repo (too large)
- Each user needs to download models separately
- SD 1.5 is a good starting point (7.2GB, works on most GPUs)
- FLUX/SDXL require 12GB+ VRAM
- Your MI50 GPUs should handle any model easily

---

**All changes pushed to GitHub!** Clone and download models to get started. 🚀
