from .extension_validity import ExtensionValidityRule
from .link_resolution import LinkResolutionRule
from .okf_conformance import OkfConformanceRule
from .orphan_pages import OrphanPagesRule

ALL_RULES = (OkfConformanceRule(), LinkResolutionRule(), ExtensionValidityRule(), OrphanPagesRule())
