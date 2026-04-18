from abc import ABC, abstractmethod

from ...payloads.shared import CamelCaseModel
from ......models import (Contact, BaseMaxObject)
from ...payloads.models import (ContactMappingModel,)

class BaseTranslateMappingModel(ABC):
    @staticmethod
    @abstractmethod
    def translate(mapping_model: CamelCaseModel) -> BaseMaxObject: pass


class TranslateContact(BaseTranslateMappingModel):
    @staticmethod
    def translate(contact: ContactMappingModel) -> Contact: # type: ignore[override]
        return Contact(
            id=contact.id,
            name=contact.names[0].name if contact.names else '',
            description=contact.description,
            first_name=contact.names[0].first_name if contact.names else '',
            last_name=contact.names[0].last_name if contact.names else '',
        )

TRANSLATE_MAPPING_MODELS: dict[type[CamelCaseModel], type[BaseTranslateMappingModel]] = {
    ContactMappingModel: TranslateContact,
}



def translate_models(mapping_obj: CamelCaseModel) -> BaseMaxObject | CamelCaseModel:
    translate_model = TRANSLATE_MAPPING_MODELS.get(type(mapping_obj), None)
    if translate_model is None:
        return mapping_obj

    translated_obj = translate_model.translate(mapping_obj)

    return translated_obj
