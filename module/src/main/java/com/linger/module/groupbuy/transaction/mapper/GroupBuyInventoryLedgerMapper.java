package com.linger.module.groupbuy.transaction.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.linger.module.groupbuy.transaction.entity.GroupBuyInventoryLedgerEntity;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Param;

public interface GroupBuyInventoryLedgerMapper extends BaseMapper<GroupBuyInventoryLedgerEntity> {

    @Insert("INSERT INTO groupbuy_inventory_ledger(activity_id, sku_id, order_id, operation, quantity) " +
            "VALUES(#{activityId}, #{skuId}, #{orderId}, #{operation}, #{quantity}) ON CONFLICT DO NOTHING")
    int insertIgnore(@Param("activityId") Long activityId,
                     @Param("skuId") String skuId,
                     @Param("orderId") String orderId,
                     @Param("operation") String operation,
                     @Param("quantity") Integer quantity);
}

