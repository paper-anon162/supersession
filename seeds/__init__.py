"""SupersessionBench seed registry.

Each module in this package authors one or more samples by calling
``pipeline.construction.seeds.register_seed``. The pilot dataset materializer
walks this package to collect every registered seed.
"""
