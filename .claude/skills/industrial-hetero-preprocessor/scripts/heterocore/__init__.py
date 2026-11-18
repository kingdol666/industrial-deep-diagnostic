"""heterocore — deterministic core of the industrial-hetero-preprocessor (E-1H).

Dependency direction (repo rule): this skill depends on shared + existing assets;
existing assets are NEVER modified to depend on this package. All cross-skill
integration happens via data artifacts (07_hetero/*), never via imports.
"""

__version__ = "1.1.0"
CONTRACT_VERSION = "hetero-features/1.1"
