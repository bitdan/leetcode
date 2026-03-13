# Amazon Order Schema Example

Use this file as a concrete schema payload for testing natural-language to SQL generation against Amazon order data.

## Business Notes

- Order header table: `sale_amazon_order`
- Order item table: `sale_amazon_order_item`
- Join key: `amazon_order_id`
- Suggested default time field for analytics: `o.create_time`
- Soft delete flag: `deleted = b'0'`
- Common tenant filters: `account`, `site`, `shop_id`
- Refund indicator at order level: `refund_flag`
- Monetary fields are stored as `varchar`; cast them before aggregation

## Suggested JSON Input

```json
{
  "question": "近30天 QD-US 销量最高的 10 个 SKU",
  "tables": [
    {
      "name": "sale_amazon_order",
      "alias": "o",
      "description": "亚马逊订单主表，订单粒度",
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "bigint",
          "meaning": "主键",
          "role": "key"
        },
        {
          "name": "amazon_order_id",
          "type": "varchar(50)",
          "meaning": "亚马逊订单号",
          "role": "join_key"
        },
        {
          "name": "order_status",
          "type": "varchar(20)",
          "meaning": "订单状态",
          "role": "status"
        },
        {
          "name": "amount",
          "type": "varchar(20)",
          "meaning": "订单总金额",
          "role": "metric"
        },
        {
          "name": "create_time",
          "type": "datetime",
          "meaning": "创建时间",
          "role": "date"
        },
        {
          "name": "deleted",
          "type": "bit(1)",
          "meaning": "删除标识",
          "role": "flag"
        },
        {
          "name": "account",
          "type": "varchar(16)",
          "meaning": "账号",
          "role": "dimension"
        },
        {
          "name": "site",
          "type": "varchar(16)",
          "meaning": "站点",
          "role": "dimension"
        },
        {
          "name": "shop_id",
          "type": "bigint",
          "meaning": "店铺ID",
          "role": "dimension"
        },
        {
          "name": "refund_flag",
          "type": "varchar(5)",
          "meaning": "退款标识",
          "role": "status"
        }
      ]
    },
    {
      "name": "sale_amazon_order_item",
      "alias": "i",
      "description": "亚马逊订单商品表，订单商品粒度",
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "bigint",
          "meaning": "主键",
          "role": "key"
        },
        {
          "name": "amazon_order_id",
          "type": "varchar(50)",
          "meaning": "亚马逊订单号",
          "role": "join_key"
        },
        {
          "name": "seller_sku",
          "type": "varchar(100)",
          "meaning": "SKU",
          "role": "dimension"
        },
        {
          "name": "asin",
          "type": "varchar(50)",
          "meaning": "ASIN",
          "role": "dimension"
        },
        {
          "name": "title",
          "type": "varchar(500)",
          "meaning": "商品标题",
          "role": "dimension"
        },
        {
          "name": "quantity_ordered",
          "type": "int(11)",
          "meaning": "下单数量",
          "role": "metric"
        },
        {
          "name": "quantity_shipped",
          "type": "int(11)",
          "meaning": "已发货数量",
          "role": "metric"
        },
        {
          "name": "number_of_items",
          "type": "int(11)",
          "meaning": "商品数量",
          "role": "metric"
        },
        {
          "name": "item_price",
          "type": "varchar(20)",
          "meaning": "商品价格",
          "role": "metric"
        },
        {
          "name": "shipping_price",
          "type": "varchar(20)",
          "meaning": "配送价格",
          "role": "metric"
        },
        {
          "name": "sales_commission",
          "type": "varchar(255)",
          "meaning": "销售佣金",
          "role": "metric"
        },
        {
          "name": "refund_amount",
          "type": "varchar(255)",
          "meaning": "退款金额",
          "role": "metric"
        },
        {
          "name": "deleted",
          "type": "bit(1)",
          "meaning": "删除标识",
          "role": "flag"
        },
        {
          "name": "account",
          "type": "varchar(16)",
          "meaning": "账号",
          "role": "dimension"
        },
        {
          "name": "site",
          "type": "varchar(16)",
          "meaning": "站点",
          "role": "dimension"
        },
        {
          "name": "shop_id",
          "type": "bigint",
          "meaning": "店铺ID",
          "role": "dimension"
        }
      ]
    }
  ],
  "joins": [
    {
      "left_table": "sale_amazon_order",
      "left_column": "amazon_order_id",
      "right_table": "sale_amazon_order_item",
      "right_column": "amazon_order_id",
      "cardinality": "one-to-many"
    }
  ],
  "enums": [
    {
      "column": "sale_amazon_order.refund_flag",
      "values": {
        "Y": "退款",
        "N": "未退款"
      }
    }
  ],
  "rules": [
    "涉及金额汇总时，对 varchar 金额字段做 CAST(... AS DECIMAL(18,2))",
    "如无明确说明，时间过滤默认使用 sale_amazon_order.create_time",
    "如无明确说明，查询时默认过滤 o.deleted = b'0' 且 i.deleted = b'0'"
  ]
}
```

## Common Mappings

- “销量”:
    - 优先追问是 `quantity_ordered` 还是 `quantity_shipped`
- “销售额”:
    - `SUM(CAST(i.item_price AS DECIMAL(18,2)))` 或 `SUM(CAST(o.amount AS DECIMAL(18,2)))`
- “退款单”:
    - 可结合 `o.refund_flag`
- “SKU 维度”:
    - `i.seller_sku`
- “ASIN 维度”:
    - `i.asin`

## Recommended Default SQL Pattern

```sql
SELECT i.seller_sku,
       SUM(IFNULL(i.quantity_ordered, 0)) AS qty_ordered
FROM sale_amazon_order_item i
         JOIN sale_amazon_order o
              ON o.amazon_order_id = i.amazon_order_id
WHERE o.deleted = 0
  AND i.deleted = 0
GROUP BY i.seller_sku
ORDER BY qty_ordered DESC
LIMIT 10
```
