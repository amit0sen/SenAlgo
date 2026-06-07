"""
SenAlgo Strategy Library — by Amit Kumar Sen
All strategies: SMC, ICT, Elliott Wave, CRT, ORB, Price Action, Multi-Factor
"""
from .elliott_wave import ElliottWaveAnalyzer
from .ict_concepts import ICTEngine
from .candle_range_theory import CRTEngine
from .multi_factor import MultiFactorEngine, ALPHA_REGISTRY

__all__ = [
    "ElliottWaveAnalyzer", "ICTEngine", "CRTEngine",
    "MultiFactorEngine", "ALPHA_REGISTRY",
]
