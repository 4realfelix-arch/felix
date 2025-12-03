"""
Image generation tools using ComfyUI
Provides text-to-image, image-to-image, and other AI image generation capabilities
"""

import asyncio
import base64
from pathlib import Path
from typing import Optional
import structlog

from ..registry import tool_registry
from ...comfy_service import get_comfy_service

logger = structlog.get_logger(__name__)

# Default workflow for text-to-image (Stable Diffusion 1.5 format)
DEFAULT_TEXT2IMG_WORKFLOW = {
    "3": {
        "inputs": {
            "seed": 0,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    },
    "4": {
        "inputs": {
            "ckpt_name": "v1-5-pruned.safetensors"
        },
        "class_type": "CheckpointLoaderSimple"
    },
    "5": {
        "inputs": {
            "width": 512,
            "height": 512,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "6": {
        "inputs": {
            "text": "",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "7": {
        "inputs": {
            "text": "text, watermark",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "8": {
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        },
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {
            "filename_prefix": "felix_gen",
            "images": ["8", 0]
        },
        "class_type": "SaveImage"
    }
}


@tool_registry.register(
    description="Generate an image from a text description using AI (Stable Diffusion)",
    category="image"
)
async def generate_image(
    prompt: str,
    negative_prompt: str = "text, watermark, blurry, low quality",
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    cfg_scale: float = 7.0
) -> str:
    """
    Generate an image from a text prompt.
    
    Args:
        prompt: Description of the image to generate
        negative_prompt: Things to avoid in the image
        width: Image width (default 512, multiples of 64)
        height: Image height (default 512, multiples of 64)
        steps: Number of denoising steps (default 20, range 1-150)
        cfg_scale: Classifier-free guidance scale (default 7.0, range 1-30)
    
    Returns:
        Path to generated image or error message
    """
    service = get_comfy_service()
    
    if not service:
        return "❌ Image generation is not available. ComfyUI service is not initialized."
    
    # Start ComfyUI if not running
    if not service.is_running:
        logger.info("starting_comfyui_for_generation")
        started = await service.start()
        if not started:
            return "❌ Failed to start image generation service. Please check ComfyUI installation."
    
    try:
        # Create workflow from template
        workflow = DEFAULT_TEXT2IMG_WORKFLOW.copy()
        
        # Update parameters
        workflow["6"]["inputs"]["text"] = prompt
        workflow["7"]["inputs"]["text"] = negative_prompt
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height
        workflow["3"]["inputs"]["steps"] = steps
        workflow["3"]["inputs"]["cfg"] = cfg_scale
        workflow["3"]["inputs"]["seed"] = -1  # Random seed
        
        logger.info("queueing_image_generation", prompt=prompt[:50])
        
        # Queue the prompt
        prompt_id = await service.queue_prompt(workflow)
        
        # Wait for completion (poll history)
        max_wait = 120  # 2 minutes max
        waited = 0
        
        while waited < max_wait:
            await asyncio.sleep(2)
            waited += 2
            
            history = await service.get_history(prompt_id)
            if prompt_id in history:
                result = history[prompt_id]
                
                # Check if completed
                if "outputs" in result:
                    # Get the image from SaveImage node (node 9)
                    if "9" in result["outputs"]:
                        images = result["outputs"]["9"].get("images", [])
                        if images:
                            img_info = images[0]
                            filename = img_info["filename"]
                            subfolder = img_info.get("subfolder", "")
                            
                            logger.info("image_generated", filename=filename)
                            
                            # Return the image path info
                            image_url = f"{service.base_url}/view?filename={filename}&type=output"
                            if subfolder:
                                image_url += f"&subfolder={subfolder}"
                            
                            return f"✅ Image generated successfully!\n\nPrompt: {prompt}\n\n**View image**: {image_url}\n\n_(Image saved as: {filename})_"
        
        return "⏱️ Image generation timed out. The image may still be processing."
        
    except Exception as e:
        logger.error("image_generation_error", error=str(e))
        return f"❌ Image generation failed: {str(e)}"


@tool_registry.register(
    description="Get the status of ComfyUI image generation service",
    category="image"
)
async def image_service_status() -> str:
    """
    Check the status of the image generation service.
    
    Returns:
        Status information about ComfyUI service
    """
    service = get_comfy_service()
    
    if not service:
        return "❌ ComfyUI service is not available"
    
    if not service.is_running:
        return "⏸️ ComfyUI service is stopped (will start automatically when needed)"
    
    try:
        is_healthy = await service.health_check()
        if not is_healthy:
            return "⚠️ ComfyUI service is running but not responding"
        
        queue_status = await service.get_queue_status()
        queue_running = len(queue_status.get("queue_running", []))
        queue_pending = len(queue_status.get("queue_pending", []))
        
        status = f"✅ ComfyUI service is running\n\n"
        status += f"URL: {service.base_url}\n"
        status += f"Queue: {queue_running} running, {queue_pending} pending"
        
        return status
        
    except Exception as e:
        logger.error("status_check_error", error=str(e))
        return f"⚠️ Error checking status: {str(e)}"


@tool_registry.register(
    description="Start the ComfyUI image generation service manually",
    category="image"
)
async def start_image_service() -> str:
    """
    Manually start the ComfyUI image generation service.
    
    Returns:
        Success or error message
    """
    service = get_comfy_service()
    
    if not service:
        return "❌ ComfyUI service is not available"
    
    if service.is_running:
        return "ℹ️ ComfyUI service is already running"
    
    logger.info("manually_starting_comfyui")
    started = await service.start()
    
    if started:
        return f"✅ ComfyUI service started successfully at {service.base_url}"
    else:
        return "❌ Failed to start ComfyUI service"


@tool_registry.register(
    description="Stop the ComfyUI image generation service manually",
    category="image"
)
async def stop_image_service() -> str:
    """
    Manually stop the ComfyUI image generation service.
    
    Returns:
        Success or error message
    """
    service = get_comfy_service()
    
    if not service:
        return "❌ ComfyUI service is not available"
    
    if not service.is_running:
        return "ℹ️ ComfyUI service is already stopped"
    
    logger.info("manually_stopping_comfyui")
    await service.stop()
    
    return "✅ ComfyUI service stopped"
