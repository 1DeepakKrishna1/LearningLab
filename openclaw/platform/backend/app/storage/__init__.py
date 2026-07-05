"""Storage abstraction layer.

Business code depends only on the `Repository` protocol defined here. The default
implementation is JSON-file backed (`JsonRepository`); a SQL/NoSQL implementation can
be introduced later without touching services.
"""
