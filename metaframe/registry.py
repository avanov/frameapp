from collections import OrderedDict
from typing import NamedTuple, Dict

from .configurator.routes import Route
from .configurator.sums import SumTypeMetaData
from .structures import CompactSerializable


class AppRegistry(NamedTuple):
    """ Application Registry expressed as an immutable structure for use after configuration step.
    """
    routes: Dict[str, Dict[str, Route]]
    sums: Dict[str, SumTypeMetaData]


class _RegistryBuilder(CompactSerializable):
    """ Registry Builder is only used during configuration step, where mutability is convenient.
    """
    __slots__ = ('routes', 'sums')

    def __init__(self) -> None:
        self.routes: Dict[str, Dict[str, Route]] = OrderedDict()
        self.sums: Dict[str, SumTypeMetaData] = OrderedDict()


class predvalseq(tuple):
    """ This class is a copy of ``pyramid.registry.predvalseq``

    A subtype of tuple used to represent a sequence of predicate values """
    pass
