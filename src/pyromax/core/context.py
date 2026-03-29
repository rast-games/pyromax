from ..protocol import PROTOCOLS, BaseMaxProtocol
from ..transtport import TRANSPORTS, BaseTransport
from ..mapping import MAPPERS, BaseMapper

PROTOCOLS: dict[str, type[BaseMaxProtocol]]
TRANSPORTS: dict[str, type[BaseTransport]]
MAPPERS: dict[str, type[BaseMapper]]