"""
ComfyUI Integration Service
Manages ComfyUI as an embedded service within Felix
"""

import os
import sys
import asyncio
import subprocess
import httpx
import structlog
from pathlib import Path
from typing import Optional, Dict, Any
import signal

logger = structlog.get_logger(__name__)

class ComfyUIService:
    """Manages ComfyUI as an embedded service"""
    
    def __init__(self, 
                 comfy_dir: str = None,
                 host: str = "127.0.0.1",
                 port: int = 8188):
        """
        Initialize ComfyUI service
        
        Args:
            comfy_dir: Path to ComfyUI installation (defaults to felix/comfy)
            host: Host to bind ComfyUI server to
            port: Port to bind ComfyUI server to
        """
        self.comfy_dir = Path(comfy_dir) if comfy_dir else Path(__file__).parent.parent / "comfy"
        self.host = host
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.client: Optional[httpx.AsyncClient] = None
        self._is_ready = False
        
        if not self.comfy_dir.exists():
            raise FileNotFoundError(f"ComfyUI directory not found: {self.comfy_dir}")
        
        logger.info("comfy_service_initialized", 
                   comfy_dir=str(self.comfy_dir),
                   host=self.host, 
                   port=self.port)
    
    @property
    def base_url(self) -> str:
        """Get the base URL for ComfyUI API"""
        return f"http://{self.host}:{self.port}"
    
    @property
    def is_running(self) -> bool:
        """Check if ComfyUI process is running"""
        return self.process is not None and self.process.poll() is None
    
    async def start(self) -> bool:
        """
        Start ComfyUI server as subprocess
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            logger.warning("comfy_already_running")
            return True
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env['COMFYUI_PORT'] = str(self.port)
            env['COMFYUI_HOST'] = self.host
            
            # Start ComfyUI server
            cmd = [
                sys.executable,
                "main.py",
                "--listen", self.host,
                "--port", str(self.port),
            ]
            
            logger.info("starting_comfyui", cmd=" ".join(cmd), cwd=str(self.comfy_dir))
            
            self.process = subprocess.Popen(
                cmd,
                cwd=self.comfy_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group for clean shutdown
            )
            
            # Wait for server to be ready
            self._is_ready = await self._wait_for_ready(timeout=30)
            
            if self._is_ready:
                # Create HTTP client
                self.client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=httpx.Timeout(30.0)
                )
                logger.info("comfyui_started", url=self.base_url)
                return True
            else:
                logger.error("comfyui_failed_to_start")
                await self.stop()
                return False
                
        except Exception as e:
            logger.error("comfyui_start_error", error=str(e))
            await self.stop()
            return False
    
    async def _wait_for_ready(self, timeout: int = 30) -> bool:
        """
        Wait for ComfyUI server to be ready
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if ready, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if not self.is_running:
                logger.error("comfyui_process_died")
                return False
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/system_stats", timeout=2.0)
                    if response.status_code == 200:
                        logger.info("comfyui_ready")
                        return True
            except (httpx.RequestError, httpx.TimeoutException):
                pass
            
            await asyncio.sleep(1)
        
        logger.error("comfyui_ready_timeout")
        return False
    
    async def stop(self):
        """Stop ComfyUI server"""
        if self.client:
            await self.client.aclose()
            self.client = None
        
        if self.process:
            try:
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if not stopped
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait()
                
                logger.info("comfyui_stopped")
            except Exception as e:
                logger.error("comfyui_stop_error", error=str(e))
            finally:
                self.process = None
                self._is_ready = False
    
    async def health_check(self) -> bool:
        """
        Check if ComfyUI is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        if not self.is_running or not self.client:
            return False
        
        try:
            response = await self.client.get("/system_stats")
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        if not self.client:
            raise RuntimeError("ComfyUI service not started")
        
        response = await self.client.get("/queue")
        response.raise_for_status()
        return response.json()
    
    async def get_history(self, prompt_id: str = None) -> Dict[str, Any]:
        """Get prompt history"""
        if not self.client:
            raise RuntimeError("ComfyUI service not started")
        
        url = f"/history/{prompt_id}" if prompt_id else "/history"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def queue_prompt(self, prompt: Dict[str, Any]) -> str:
        """
        Queue a workflow prompt for execution
        
        Args:
            prompt: ComfyUI workflow prompt dictionary
            
        Returns:
            Prompt ID
        """
        if not self.client:
            raise RuntimeError("ComfyUI service not started")
        
        payload = {
            "prompt": prompt,
            "client_id": "felix"
        }
        
        response = await self.client.post("/prompt", json=payload)
        response.raise_for_status()
        result = response.json()
        
        prompt_id = result.get("prompt_id")
        logger.info("prompt_queued", prompt_id=prompt_id)
        return prompt_id
    
    async def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """
        Get generated image
        
        Args:
            filename: Image filename
            subfolder: Subfolder within folder_type
            folder_type: Type of folder (output, input, temp)
            
        Returns:
            Image bytes
        """
        if not self.client:
            raise RuntimeError("ComfyUI service not started")
        
        params = {
            "filename": filename,
            "type": folder_type
        }
        if subfolder:
            params["subfolder"] = subfolder
        
        response = await self.client.get("/view", params=params)
        response.raise_for_status()
        return response.content
    
    async def interrupt(self):
        """Interrupt current execution"""
        if not self.client:
            raise RuntimeError("ComfyUI service not started")
        
        response = await self.client.post("/interrupt")
        response.raise_for_status()
        logger.info("execution_interrupted")
    
    async def clear_queue(self):
        """Clear the execution queue"""
        if not self.client:
            raise RuntimeError("ComfyUI service not started")
        
        payload = {"clear": True}
        response = await self.client.post("/queue", json=payload)
        response.raise_for_status()
        logger.info("queue_cleared")


# Global singleton instance
_comfy_service: Optional[ComfyUIService] = None

def get_comfy_service() -> Optional[ComfyUIService]:
    """Get the global ComfyUI service instance"""
    return _comfy_service

async def initialize_comfy_service(auto_start: bool = True) -> Optional[ComfyUIService]:
    """
    Initialize the global ComfyUI service
    
    Args:
        auto_start: Whether to automatically start ComfyUI on initialization
        
    Returns:
        ComfyUIService instance or None if initialization failed
    """
    global _comfy_service
    
    try:
        _comfy_service = ComfyUIService()
        
        if auto_start:
            success = await _comfy_service.start()
            if not success:
                logger.warning("comfyui_autostart_failed")
                _comfy_service = None
                return None
        
        return _comfy_service
    except FileNotFoundError as e:
        logger.warning("comfyui_not_found", error=str(e))
        return None
    except Exception as e:
        logger.error("comfyui_init_error", error=str(e))
        return None

async def shutdown_comfy_service():
    """Shutdown the global ComfyUI service"""
    global _comfy_service
    
    if _comfy_service:
        await _comfy_service.stop()
        _comfy_service = None
