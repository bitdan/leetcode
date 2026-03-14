SELECT
    i.seller_sku,
    SUM(COALESCE(i.quantity_ordered, 0)) AS qty_ordered
FROM sale_amazon_order_item i
WHERE i.deleted = b'0'
  AND i.create_time >= NOW() - INTERVAL 30 DAY
  AND i.seller_sku IS NOT NULL
  AND i.seller_sku <> ''
GROUP BY i.seller_sku
ORDER BY qty_ordered DESC
    LIMIT 10;

