-- intermediate: join bureau + bureau_balance, deferred to Fabric Warehouse compute (ADR-003)
-- Retired dbt_fabric/models/intermediate/int_bureau_with_balance.sql (ADR-008).
CREATE OR ALTER VIEW dbo.int_bureau_with_balance AS
SELECT
    b.SK_ID_BUREAU,
    b.SK_ID_CURR
FROM silver.silver_bureau AS b;
