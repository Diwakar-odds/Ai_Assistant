import os
import platform
import psutil
import logging

logger = logging.getLogger(__name__)

class HardwareDetector:
    @staticmethod
    def detect():
        info = {
            'ram_gb': round(psutil.virtual_memory().total / (1024**3), 1),
            'free_ram_gb': round(psutil.virtual_memory().available / (1024**3), 1),
            'cpu': platform.processor(),
            'engine': 'cpu', # Default fallback
            'acceleration': 'avx2',
            'recommended_tier': 'ultra_light'
        }

        # 1. Check RAM Tier
        if info['free_ram_gb'] >= 6.0:
            info['recommended_tier'] = 'full_power'
        elif info['free_ram_gb'] >= 3.0:
            info['recommended_tier'] = 'balanced'
            
        # 2. Check GPU / NPU
        try:
            import torch
            if torch.cuda.is_available():
                info['engine'] = 'cuda'
                info['acceleration'] = 'gpu'
                logger.info("HardwareDetector: NVIDIA GPU CUDA detected.")
                return info
        except ImportError:
            pass

        # 3. Check for Intel NPU / OpenVINO
        if 'Intel' in info['cpu'] or 'Ultra' in info['cpu']:
            try:
                import openvino
                info['engine'] = 'openvino'
                info['acceleration'] = 'npu'
                logger.info("HardwareDetector: Intel OpenVINO/NPU supported CPU detected.")
                return info
            except ImportError:
                info['acceleration'] = 'intel_avx_missing_openvino'
                logger.info("HardwareDetector: Intel CPU detected, but OpenVINO not installed.")

        # 4. Check for Apple Silicon
        if platform.system() == 'Darwin' and platform.machine() == 'arm64':
            info['engine'] = 'metal'
            info['acceleration'] = 'mps'
            
        logger.info(f"HardwareDetector Results: {info}")
        return info

if __name__ == '__main__':
    print(HardwareDetector.detect())
