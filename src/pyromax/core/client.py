import asyncio
import logging

from src.pyromax.mapping.bases.BaseMapper import BaseMapper
from src.pyromax.mixins import AsyncInitializerMixin
from src.pyromax.protocol.bases.base import BaseMaxProtocol
from src.pyromax.transtport.bases import BaseTransport
from src.pyromax.transtport.registry import TRANSPORTS
from src.pyromax.transtport.websocket import WebSocketTransport
from src.pyromax.mapping.envelope.v11.Mapper import Mapper
#just for tests
from src.pyromax.protocol.envelope import EnvelopeProtocol
#end



class MaxApi(AsyncInitializerMixin):
    async def _async_init(
            self,
            mapper: type[BaseMapper],
            token: str,
            transport: str = 'websocket',
            transport_options: dict = None,
            protocol: type[BaseMaxProtocol] = EnvelopeProtocol,
            protocol_version='v11',
            **kwargs
    ):
        if transport not in TRANSPORTS:
            raise RuntimeError(f"transport {transport} is not supported")

        transport = await TRANSPORTS[transport](**transport_options)
        protocol = await protocol(transport=transport)
        max_mapper = await mapper(protocol=protocol)

        await asyncio.to_thread(self.__init__, protocol=protocol, transport=transport, transport_options=transport_options, mapper=max_mapper, token=token)

        await self.mapper.initialize_client(
            token=token,
            **kwargs
        )


    def __init__(
            self,
            transport: BaseTransport,
            protocol: BaseMaxProtocol,
            transport_options: dict,
            mapper: BaseMapper,
            token: str,
            # device_id: str = get_random_device_id(),
            # protocol_version='v11',
            # device_type: str = 'WEB',
            # timezone: str = 'Europe/Moscow',
            # screen: str = '1440x2560 1.0x',
            # locale: str = 'ru',
            # device_locale: str = 'ru',
            # os_version: str = 'Linux',
            # app_version: str = '26.2.10',
            # header_user_agent: str = 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
            # device_name: str = 'Firefox',
            # chats_count: int = 40,
            # interactive: bool = True,
            # presence_sync: int = -1,
            # chats_sync: int = 0,
            # contacts_sync: int = 0,
            # drafts_sync: int = 0,
    ):
        self.transport = transport
        self.transport_options = transport_options
        self.protocol = protocol
        self.mapper = mapper
        self.token = token


# class TestMethod:
#     def __init__(self, opcode):
#         self.opcode = opcode
#
#
#     async def __call__(self, request):
#         request.opcode = self.opcode
#
#         return request


async def main():
    max_api = await MaxApi(transport_options={'url': "wss://ws-api.oneme.ru/websocket"}, mapper=Mapper,
                           token='An_Sx6HQ9HDiSXXXIYFVvPDVllVzfdJju7pWlJCeaZsem-hYiI9Ahc7i_81HWfho9m3XOJMLLzuFy5FfXJqSAAOPKfiE4Myc-rEVBMFmJuXRzSMG376pKL4dVDMYMsFL8WGeJ863VwTK59ujuYAVfqo810EneRrGgYrg8BL9va9AVB6CcRuYhopdrVrsKNy1jaVAwwwnJFt9q8TgiwHcFKQdiYcyvsLyE4H9beG-fPszqlPs8jj_ft62Y9eYkcdoe-O7Nf6AZJPxbBuqDX1hUDxa0NmUYySzrzjKo_d3qooTzWgewRT6oKF08yWKjgeZ8_TLsRrORIcwXcqfUdTkdNNH_PzNq_XpmdShsa5VX5yQZXHuASFfIqDAuB-fMDuNbY_DmIAxGe7Dm3pTkhwM5VIkcnRt4EVS-hwnx8WEuQUqO64CZRbwk0MxYpmS0KT1qARzLKy64GwfpveEW1ykIMBQwwHNinj8K0nSZCIrOYqrCJL0CwPNXbJ-SUYxLZIYDPmOH9GXbQPNqhh5myC3LVxF86X-9QsA3X5TLn1LNv98DAG6_cvRSq9OuiOWH1lHEN0jwtvGwmSxaF3udoEfBwp_TyLGtZ1SS9wOwgzr7VSP6WydE2erIS9z6jLXNdAvX37XnFnY0mvxVhQ0Uc-YCb7jz0ZVzCXfcK3Gsa0vCswgislKGHC5GKvA1dRi_ZOSWJjhzPo',
                           )


    logging.basicConfig(level=logging.DEBUG)

    await asyncio.sleep(100000)




if __name__ == '__main__':
    asyncio.run(main())
