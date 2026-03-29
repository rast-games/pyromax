class MappingConstantsMeta(type):
    def __repr__(cls):

        attrs = {}

        for CLS in cls.__mro__:
            for attr in CLS.__dict__:

                if attr.startswith('__') and attr.endswith('__') or attr.startswith('_') or attr in attrs:
                    continue

                attrs[attr] = getattr(CLS, attr)


        attrs_str = ' '.join(f'{attr}={value}' for attr, value in attrs.items())
        return f'{cls.__name__}({attrs_str})'


class MappingConstants(metaclass=MappingConstantsMeta):
    def __repr__(self):

        attrs = {}

        for CLS in type(self).__mro__:
            for attr in CLS.__dict__:
                if attr.startswith('__') and attr.endswith('__') or attr.startswith('_') or attr in attrs:
                    continue

                attrs[attr] = getattr(CLS, attr)

        attrs_str = ' '.join(f'{attr}={value}' for attr, value in attrs.items())
        return f'{type(self).__name__}({attrs_str})'