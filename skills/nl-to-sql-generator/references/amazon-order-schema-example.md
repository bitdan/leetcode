# Amazon Order Schema Example

Use this as a small example when the user needs help formatting schema input.

## Tables

- `sale_amazon_order`
  - `amazon_order_id`: order identifier
  - `account`: seller account
  - `site`: marketplace site
  - `order_status`: order status
  - `amount`: order amount
  - `create_time`: order create time

- `sale_amazon_order_item`
  - `amazon_order_id`: joins to `sale_amazon_order.amazon_order_id`
  - `seller_sku`: seller SKU
  - `asin`: Amazon ASIN
  - `quantity_ordered`: ordered quantity
  - `quantity_shipped`: shipped quantity
  - `item_price`: item amount
  - `shipping_price`: shipping amount
  - `refund_amount`: refund amount
  - `sales_commission`: sales commission
  - `create_time`: item create time

## Relationship

- `sale_amazon_order_item.amazon_order_id = sale_amazon_order.amazon_order_id`

## Example question

- "近30天销量最高的10个 SKU"

## Example SQL

```sql
SELECT
    i.seller_sku,
    SUM(i.quantity_ordered) AS qty_ordered
FROM sale_amazon_order_item i
WHERE i.create_time >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY i.seller_sku
ORDER BY qty_ordered DESC
LIMIT 10
```
