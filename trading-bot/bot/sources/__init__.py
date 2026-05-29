"""Adaptadores de dados reais. Cada um converte uma fonte externa em
list[Candle], a unica coisa que o motor entende. Sao OPCIONAIS e so importam
suas dependencias quando usados.
"""

from .feed_config import DataSourceConfig, build_feed

__all__ = ["DataSourceConfig", "build_feed"]
