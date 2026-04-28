"""Instantiate the Sydor T4U beam position monitor for 4IDG (gsydor)."""

__all__ = ["gsydor"]

from ..utils._logging_setup import logger
from .quadems import SydorEMRO

logger.info(__file__)

gsydor = SydorEMRO("4idgSydor:T4U_BPM:", name="gsydor", labels=("detector",))
