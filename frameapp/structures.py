import json
from typing import Dict, Callable, List, Optional, Iterable, Set, Any

from .configurator.renderers import ExtendedJSONEncoder


encode_json = ExtendedJSONEncoder().encode


class CompactSerializable:
    """ Whenever you inherit from this object, make sure that you define `__slots__` in your child classes.
    """
    __slots__ = tuple()
    IN_MODIFIERS: Dict[str, Callable] = {}
    OUT_MODIFIERS: Dict[str, Callable] = {
        'str': str,
        'json': json.dumps,
    }
    DEFAULT_IN_MODIFIERS: Dict[str, List[str]] = {}
    DEFAULT_OUT_MODIFIERS: Dict[str, List[str]] = {}

    def as_dict(self,
                fields: Optional[Iterable[str]] = None,
                exclude: Optional[Set[str]] = None) -> Dict[str, Any]:
        """ Returns a dictionary representation of itself, adhering provided fields and modifiers.
        """
        if exclude is None:
            exclude = set()
        if not fields:
            fields = (k for k in self.__slots__ if k not in exclude)

        rv = {}
        for f in fields:
            split = f.split('|')
            field, modifiers = split[0], split[1:]
            field = field.strip()
            v = getattr(self, field)
            for m in modifiers:
                v = self.apply_modifier(m.strip(), v)
            else:
                default_modifiers = self.DEFAULT_OUT_MODIFIERS.get(field, [])
                for m in default_modifiers:
                    v = self.apply_modifier(m, v)
            rv[field] = v
        return rv

    def apply_modifier(self, modifier: str, value: Any) -> Any:
        if modifier.startswith('.'):
            # applying a method of the value
            value = getattr(value, modifier[1:])()
        else:
            value = self.OUT_MODIFIERS[modifier](value)
        return value

    def __str__(self) -> str:
        """ Serialize the object by passing it to ``str()``.
        """
        return encode_json(self.as_dict())

    def __bytes__(self) -> bytes:
        return bytes(self.__str__(), 'utf-8')
