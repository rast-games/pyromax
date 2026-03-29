from src.pyromax.transtport.bases.StreamTransport import StreamTransport
from .registry import register_transport


@register_transport('socket')
class SocketTransport(StreamTransport):
    pass