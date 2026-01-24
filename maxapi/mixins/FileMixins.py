from maxapi.utils import get_dict_value_by_path


class DataBodyMixin:
    def _set_headers(self, file_size, filename):
        self.headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Range": f"0-{file_size - 1}/{file_size}",
            "Content-Length": str(file_size),
            "Connection": "keep-alive",
        }

    def get_body(self, data):
        return data

    async def _parse_response(self, response):
        if await response.text() == f"0-{self.file_size - 1}/{self.file_size}":
            self.uploaded = True


    async def _get_payload_info(self):
        response = await self.send_create_request()
        return get_dict_value_by_path('payload info', response)[0]


class FormDataBodyMixin:
    def get_body(self, data):
        return {
            'file': data
        }