"""NDIS Opportunity Explorer.

A local-first toolkit for analysing the Australian NDIS (National Disability
Insurance Scheme) market and surfacing opportunities for a new disability
service provider.

The package is deliberately small and dependency-light so it can be iterated on
quickly. It is split into clear layers:

- ``config``      - paths, domain taxonomy and tunable defaults
- ``data``        - loading, validation and (optional) user uploads
- ``analysis``    - market sizing, growth and derived metrics
- ``opportunity`` - the transparent, weighted opportunity-scoring model
- ``ai``          - narrative insight generation (LLM optional, rules fallback)
"""

__version__ = "0.1.0"
