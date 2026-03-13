select seller_sku, sum(quantity_ordered) as qty_ordered
from orders
group by seller_sku
order by qty_ordered desc
