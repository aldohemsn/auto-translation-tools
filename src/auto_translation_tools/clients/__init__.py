"""客户端模块"""

from .corenlp_client import CoreNLPClient
from .dict_client import DictClient, LookupResult

__all__ = ["CoreNLPClient", "DictClient", "LookupResult"]
