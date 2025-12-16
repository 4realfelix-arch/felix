"""STT backend routing.

Supported backends:
- `faster-whisper` (default)
- `whisper-cpp` (requires a built `whisper-cli` binary + ggml model files)

If `STT_BACKEND=whisper-cpp` is selected but whisper.cpp isn’t available,
this module automatically falls back to `faster-whisper` so the app remains usable.
"""

from typing import Any

import structlog

from ..config import settings

logger = structlog.get_logger()

_active_backend: str = "faster-whisper"


def get_active_stt_backend() -> str:
	"""Return the backend actually in use (may differ from `settings.stt_backend` due to fallback)."""
	return _active_backend


async def _get_faster_whisper_stt() -> Any:
	global _active_backend
	from .whisper import get_stt as get_faster_whisper_stt

	_active_backend = "faster-whisper"
	return await get_faster_whisper_stt()


async def get_stt() -> Any:
	"""Get the configured STT backend instance (with safe fallback)."""
	global _active_backend

	if settings.stt_backend == "whisper-cpp":
		try:
			from .whisper_cpp import get_stt as get_whisper_cpp_stt

			stt = await get_whisper_cpp_stt()
			_active_backend = "whisper-cpp"
			return stt
		except Exception as e:
			logger.warning(
				"stt_backend_fallback",
				requested_backend="whisper-cpp",
				fallback_backend="faster-whisper",
				error=str(e),
			)
			return await _get_faster_whisper_stt()

	return await _get_faster_whisper_stt()


async def transcribe_audio(audio_data: bytes, sample_rate: int = 16000) -> str:
	"""Convenience transcription function routed by backend (with safe fallback)."""
	global _active_backend
	if settings.stt_backend == "whisper-cpp":
		try:
			from .whisper_cpp import transcribe_audio as whisper_cpp_transcribe

			_active_backend = "whisper-cpp"
			return await whisper_cpp_transcribe(audio_data, sample_rate=sample_rate)
		except Exception as e:
			logger.warning(
				"stt_backend_fallback",
				requested_backend="whisper-cpp",
				fallback_backend="faster-whisper",
				error=str(e),
			)

	from .whisper import transcribe_audio as faster_whisper_transcribe

	_active_backend = "faster-whisper"
	return await faster_whisper_transcribe(audio_data)


__all__ = ["get_stt", "transcribe_audio", "get_active_stt_backend"]
