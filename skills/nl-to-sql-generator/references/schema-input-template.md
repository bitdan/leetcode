# Schema Input Template

Use this template to collect the minimum information required for natural-language to SQL generation.

## Required

### Business question

- Plain-language request
- Expected aggregation or detail grain
- Time range or date field to use

### Tables

For each table, capture:

- Table name
- Table meaning
- Primary key if known
- Important filters

### Columns

For each relevant column, capture:

- Column name
- Data type
- Business meaning
- Whether it is a metric, dimension, key, or status field

### Relationships

- Join path between tables
- Join keys
- One-to-many or one-to-one notes if known

### Enumerations and business rules

- Status codes and meanings
- Currency, timezone, and unit rules
- Soft-delete flags
- Partition or date column conventions

## Suggested JSON Shape

```json
{
  "question": "统计近30天每个店铺成交订单数，按订单数倒序",
  "tables": [
    {
      "name": "orders",
      "description": "订单主表",
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "bigint",
          "meaning": "订单ID",
          "role": "key"
        },
        {
          "name": "shop_id",
          "type": "bigint",
          "meaning": "店铺ID",
          "role": "dimension"
        },
        {
          "name": "status",
          "type": "varchar",
          "meaning": "订单状态",
          "role": "status"
        },
        {
          "name": "paid_at",
          "type": "datetime",
          "meaning": "支付时间",
          "role": "date"
        }
      ]
    },
    {
      "name": "shops",
      "description": "店铺维表",
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "bigint",
          "meaning": "店铺ID",
          "role": "key"
        },
        {
          "name": "shop_name",
          "type": "varchar",
          "meaning": "店铺名称",
          "role": "dimension"
        }
      ]
    }
  ],
  "joins": [
    {
      "left_table": "orders",
      "left_column": "shop_id",
      "right_table": "shops",
      "right_column": "id",
      "cardinality": "many-to-one"
    }
  ],
  "enums": [
    {
      "column": "orders.status",
      "values": {
        "PAID": "已支付",
        "CANCELLED": "已取消"
      }
    }
  ]
}
```

## Minimum Gate

Do not generate executable SQL until the following are known:

- Which tables to read
- Which columns map to the requested metrics and filters
- Which join keys connect the tables
- Which date or partition column should constrain the time range
