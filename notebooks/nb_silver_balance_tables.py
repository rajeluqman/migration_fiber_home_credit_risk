"""Fabric Spark Notebook stub — Silver transform for the balance tables
(bureau_balance.csv, POS_CASH_balance.csv, credit_card_balance.csv).

Not yet implemented. Ports from the parent repo's `glue/glue_silver_balance_tables.py`.
bureau_balance is the 27M-row table — size the Fabric Spark node pool against the parent
repo's proven headroom (`migration/benchmarks/INFRA_BASELINE.md`). Depends only on
`nb_silver_application.py` completing (docs/PIPELINE_SPEC.md §5.2).
"""
