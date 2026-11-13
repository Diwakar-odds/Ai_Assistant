# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
GGUF Model Manager
Centralized Singleton manager for local Llama GGUF models.
Ensures the active GGUF model is loaded cleanly into RAM and shared safely
across intent classification, chat, and voice generation.
"""

import gc
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Unify module aliases so multi-path imports never create duplicate 2GB+ GGUF singletons
_this_gm = sys.modules.get(__name__)
if _this_gm is not None:
    for _gm_alias in (
        "ai_assistant.ai.gguf_model_manager",
        "src.ai_assistant.ai.gguf_model_manager",
        "core_ai.src.ai_assistant.ai.gguf_model_manager",
    ):
        sys.modules.setdefault(_gm_alias, _this_gm)

# Lazily load llama_cpp
try:
    from llama_cpp import Llama, GGML_TYPE_Q8_0
    LLAMA_AVAILABLE = True
except ImportError:
    Llama = None  # type: ignore
    GGML_TYPE_Q8_0 = None
    LLAMA_AVAILABLE = False


def _get_settings_mod():
    mod = sys.modules.get("settings_manager") or sys.modules.get("backend.settings_manager")
    if mod is not None:
        return mod
    backend_dir = str(Path(__file__).resolve().parents[4] / "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    try:
        import settings_manager as sm  # type: ignore
        return sm
    except Exception:
        return None


class GGUFModelManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GGUFModelManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.llm = None
        self.model_path: Optional[Path] = None
        self._loaded_signature: Optional[Tuple[str, int, int]] = None
        self._loaded_request_sig: Optional[Tuple[str, int, int]] = None
        self._infer_lock = threading.Lock()
        self.base_dir = Path(__file__).resolve().parents[4]
        self.model_filename = "pulsar-final-q4_k_m.gguf"
        self._initialized = True

    def _candidate_model_dirs(self) -> List[Path]:
        dirs: List[Optional[Path]] = [
            self.base_dir / "models",
            Path(os.getcwd()) / "models",
            Path(sys.executable).parent / "models",
            Path(sys.executable).parent / "_internal" / "models",
            (Path(getattr(sys, "_MEIPASS", "")) / "models") if getattr(sys, "_MEIPASS", None) else None,
            Path(__file__).resolve().parents[4] / "models",
        ]
        sm = _get_settings_mod()
        if sm is not None:
            try:
                dirs.insert(0, Path(sm.get_bundle_root()) / "models")
                dirs.insert(0, Path(sm.get_writable_root()) / "models")
            except Exception:
                pass

        unique_dirs: List[Path] = []
        seen = set()
        for d in dirs:
            if d is None:
                continue
            try:
                resolved = str(d.resolve())
            except Exception:
                resolved = str(d)
            if resolved not in seen:
                seen.add(resolved)
                unique_dirs.append(d)
        return unique_dirs

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Discover all available .gguf model files across candidate directories."""
        found: List[Dict[str, Any]] = []
        seen_names = set()
        for mdir in self._candidate_model_dirs():
            if not mdir.exists() or not mdir.is_dir():
                continue
            for p in sorted(mdir.glob("*.gguf")):
                key = p.name.lower()
                if key in seen_names:
                    continue
                seen_names.add(key)
                try:
                    size_mb = round(p.stat().st_size / (1024 * 1024), 1)
                except OSError:
                    size_mb = 0.0
                found.append({
                    "id": p.stem,
                    "filename": p.name,
                    "path": str(p.resolve()),
                    "size_mb": size_mb,
                })
        return found

    def resolve_model_path(self, model_name: Optional[str] = None) -> Path:
        """Resolve a requested model name/stem/path or configured setting to an existing .gguf file."""
        sm = _get_settings_mod()
        ai_cfg: Dict[str, Any] = {}
        if sm is not None:
            try:
                ai_cfg = sm.get_ai_settings() or {}
            except Exception:
                ai_cfg = {}

        explicit_req = str(model_name or "").strip()
        is_explicit_specific = explicit_req.lower() not in ("", "gguf", "local", "default", "offline")
        requested_candidates: List[str] = []
        if is_explicit_specific:
            requested_candidates.append(explicit_req)
        else:
            cfg_model = str(ai_cfg.get("defaultModel") or "").strip()
            if cfg_model and not any(tok in cfg_model.lower() for tok in ("gemini", "gpt-", "claude")):
                requested_candidates.append(cfg_model)

            cfg_rel = str((ai_cfg.get("localLlm") or {}).get("modelPath") or "").strip()
            if cfg_rel:
                requested_candidates.append(cfg_rel)

            requested_candidates.extend([
                "pulsar-final-q4_k_m.gguf",
                "pulsar-v2-checkpoint-23000-Q3_K_M.gguf",
                "pulsar-final-q3_k_m.gguf",
                self.model_filename,
            ])

        # 1. Try direct path / settings_manager resolver first
        for req in requested_candidates:
            p = Path(req)
            if p.is_file():
                return p.resolve()
            if not req.lower().endswith(".gguf"):
                p_ext = Path(f"{req}.gguf")
                if p_ext.is_file():
                    return p_ext.resolve()
            if sm is not None and hasattr(sm, "resolve_local_model_path"):
                for rel in (req, f"models/{req}", f"models/{req}.gguf"):
                    try:
                        cand = Path(sm.resolve_local_model_path(rel))
                        if cand.is_file():
                            return cand.resolve()
                    except Exception:
                        pass

        # 2. Scan candidate directories matching exact filename or stem
        dirs = self._candidate_model_dirs()
        for req in requested_candidates:
            req_name = Path(req).name
            names_to_try = [req_name] if req_name.lower().endswith(".gguf") else [f"{req_name}.gguf", req_name]
            for mdir in dirs:
                if not mdir.exists():
                    continue
                for fname in names_to_try:
                    cand = mdir / fname
                    if cand.is_file():
                        return cand.resolve()
                # Case-insensitive stem match
                req_stem = Path(req_name).stem.lower()
                for gfile in mdir.glob("*.gguf"):
                    if gfile.stem.lower() == req_stem:
                        return gfile.resolve()

        # 3. Fallback to first available .gguf ONLY when no specific model was requested
        if not (model_name and str(model_name).strip()):
            for mdir in dirs:
                if mdir.exists():
                    gguf_files = sorted(mdir.glob("*.gguf"))
                    if gguf_files:
                        return gguf_files[0].resolve()

        logger.error(f"Offline GGUF model not found for request={model_name!r}")
        raise FileNotFoundError(
            f"Requested local GGUF model '{model_name}' was not found in models/."
            if (model_name and str(model_name).strip())
            else "Local GGUF model file not found in models/ folder. Please place a .gguf model in models/ or check Settings > AI."
        )

    def _read_requested_runtime_settings(self) -> Tuple[int, bool]:
        """Read configured context window and GPU preference from settings_manager."""
        sm = _get_settings_mod()
        cfg_ctx = 2048
        use_gpu = False
        if sm is not None:
            try:
                cfg_ctx = int(sm.get_context_window())
            except Exception:
                cfg_ctx = 2048
            try:
                ai_cfg = sm.get_ai_settings() or {}
                use_gpu = bool((ai_cfg.get("localLlm") or {}).get("useGpu", False))
            except Exception:
                use_gpu = False
        return max(512, min(4096, cfg_ctx)), use_gpu

    def _compute_runtime_params(self) -> Tuple[int, int, int]:
        """Compute safe (n_ctx, n_gpu_layers, n_threads) from settings and system RAM."""
        target_n_ctx, use_gpu = self._read_requested_runtime_settings()
        try:
            import psutil
            avail_gb = psutil.virtual_memory().available / (1024 ** 3)
            if avail_gb < 0.6:
                target_n_ctx = min(target_n_ctx, 1024)
            elif avail_gb < 2.5:
                target_n_ctx = min(target_n_ctx, 2048)
        except Exception:
            target_n_ctx = min(target_n_ctx, 2048)

        n_gpu_layers = -1 if use_gpu else 0
        cpu_count = os.cpu_count() or 6
        optimal_threads = min(6, max(2, cpu_count))
        return target_n_ctx, n_gpu_layers, optimal_threads

    def unload_model(self) -> None:
        """Unload currently loaded GGUF model and free RAM."""
        if self.llm is not None:
            try:
                close_fn = getattr(self.llm, "close", None)
                if callable(close_fn):
                    close_fn()
            except Exception:
                pass
            self.llm = None
        self.model_path = None
        self._loaded_signature = None
        self._loaded_request_sig = None
        gc.collect()

    def get_model(self, model_name: Optional[str] = None) -> "Llama":
        """
        Return the singleton Llama instance for `model_name` (or configured GGUF model).
        Loads or cleanly reloads into memory if the target model/config changed.
        """
        if not LLAMA_AVAILABLE or Llama is None:
            raise ImportError(
                "llama-cpp-python is not installed in the active Python environment. "
                "Install it in venv to run local GGUF models."
            )

        with self._lock:
            found_path = self.resolve_model_path(model_name=model_name)
            raw_ctx, use_gpu = self._read_requested_runtime_settings()
            req_gpu_layers = -1 if use_gpu else 0
            req_sig = (str(found_path), raw_ctx, req_gpu_layers)

            # Reuse already-loaded model unless target file, contextWindow, or useGpu changed
            if self.llm is not None and self._loaded_request_sig == req_sig:
                return self.llm

            if self.llm is not None:
                logger.info(f"Reloading local GGUF model for new target/config: {found_path.name}")
                with self._infer_lock:
                    self.unload_model()

            # Compute RAM-aware runtime params AFTER unloading any previous GGUF model
            target_n_ctx, target_n_gpu_layers, optimal_threads = self._compute_runtime_params()
            sig = (str(found_path), target_n_ctx, target_n_gpu_layers)

            self.model_path = found_path
            self.model_filename = found_path.name
            logger.info(
                f"Loading offline GGUF model: {self.model_path.name} "
                f"(n_ctx={target_n_ctx}, n_gpu_layers={target_n_gpu_layers}, threads={optimal_threads})"
            )

            def _instantiate(gpu_layers: int, ctx_len: int) -> "Llama":
                # Try high-efficiency Q8_0 KV cache + flash_attn first to reduce RAM by 50%
                if GGML_TYPE_Q8_0 is not None:
                    try:
                        return Llama(
                            model_path=str(found_path),
                            n_gpu_layers=gpu_layers,
                            n_ctx=ctx_len,
                            n_threads=optimal_threads,
                            n_batch=512,
                            use_mlock=False,
                            use_mmap=True,
                            verbose=False,
                            type_k=GGML_TYPE_Q8_0,
                            type_v=GGML_TYPE_Q8_0,
                            flash_attn=True,
                        )
                    except Exception as q8_err:
                        logger.warning(
                            f"Optimized Q8_0 KV-cache init failed ({q8_err}); "
                            "falling back to standard KV-cache."
                        )

                return Llama(
                    model_path=str(found_path),
                    n_gpu_layers=gpu_layers,
                    n_ctx=ctx_len,
                    n_threads=optimal_threads,
                    n_batch=512,
                    use_mlock=False,
                    use_mmap=True,
                    verbose=False,
                )

            try:
                self.llm = _instantiate(target_n_gpu_layers, target_n_ctx)
                self._loaded_signature = sig
                self._loaded_request_sig = req_sig
            except Exception as load_err:
                if target_n_gpu_layers != 0:
                    logger.warning(f"GPU GGUF load failed ({load_err}); retrying on CPU...")
                    self.llm = _instantiate(0, target_n_ctx)
                    self._loaded_signature = (str(found_path), target_n_ctx, 0)
                    self._loaded_request_sig = (str(found_path), raw_ctx, 0)
                else:
                    raise

            logger.info(
                f"Local GGUF model loaded: {self.model_path.name} "
                f"(threads={optimal_threads}, mmap=True, mlock=False)"
            )

        return self.llm

    def is_loaded(self) -> bool:
        """Return True when a GGUF Llama instance is loaded in memory."""
        return self.llm is not None

    def get_status(self) -> Dict[str, Any]:
        """Return GGUF runtime availability, loaded model state, and discovered models."""
        models = self.list_available_models()
        return {
            "available": LLAMA_AVAILABLE,
            "llama_available": LLAMA_AVAILABLE,
            "loaded": self.llm is not None,
            "loaded_model": self.model_path.stem if self.model_path else None,
            "loaded_file": self.model_path.name if self.model_path else None,
            "loaded_path": str(self.model_path) if self.model_path else None,
            "n_ctx": self._loaded_signature[1] if self._loaded_signature else None,
            "n_gpu_layers": self._loaded_signature[2] if self._loaded_signature else None,
            "available_models": models,
        }


# Expose a global instance and helper accessors
gguf_manager = GGUFModelManager()


def get_gguf_manager() -> GGUFModelManager:
    """Return the singleton GGUFModelManager instance."""
    return gguf_manager


def llama_cpp_available() -> bool:
    """Return whether llama-cpp-python is installed and usable."""
    return bool(LLAMA_AVAILABLE)
