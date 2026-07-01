-- grain: SK_ID_PREV + NUM_INSTALMENT_NUMBER — 1 row per installment payment (ADR-001)
select
    SK_ID_PREV,
    NUM_INSTALMENT_NUMBER,
    SK_ID_CURR
from {{ source('silver', 'silver_installments') }}
