-- Run with: sqlite3 data/supplychain.sqlite3 < data/inspect.sql
.headers on
.mode column

SELECT 'items' AS table_name, COUNT(*) AS row_count FROM items
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'shipments', COUNT(*) FROM shipments
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL SELECT 'orders', COUNT(*) FROM orders;

-- Reproduce the S-104 allocation in SQL; expected result includes O-202 short 15.
WITH due_orders AS (
    SELECT o.order_id, c.customer_name, i.item_name, o.item_id,
           o.qty_needed, o.due_date, o.priority, inv.available_qty,
           s.expected_arrival_date,
           COALESCE(SUM(o.qty_needed) OVER (
               PARTITION BY o.item_id
               ORDER BY o.due_date, o.priority, o.order_id
               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
           ), 0) AS qty_allocated_before
    FROM orders AS o
    JOIN customers AS c USING (customer_id)
    JOIN items AS i USING (item_id)
    JOIN inventory AS inv USING (item_id)
    JOIN shipments AS s USING (item_id)
    WHERE s.shipment_id = 'S-104'
      AND o.due_date <= s.expected_arrival_date
)
SELECT order_id, customer_name, item_name, qty_needed, due_date,
       expected_arrival_date,
       CASE
           WHEN available_qty - qty_allocated_before >= qty_needed THEN 0
           WHEN available_qty - qty_allocated_before <= 0 THEN qty_needed
           ELSE qty_needed - (available_qty - qty_allocated_before)
       END AS qty_uncovered
FROM due_orders
ORDER BY due_date, priority, order_id;
