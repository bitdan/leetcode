package com.linger.module.groupbuy.transaction.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.linger.module.groupbuy.transaction.entity.GroupBuyMemberEntity;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

public interface GroupBuyMemberMapper extends BaseMapper<GroupBuyMemberEntity> {

    @Update("UPDATE groupbuy_members SET status = 'PAID', updated_by = 0, updated_at = NOW() " +
            "WHERE order_id = #{orderId} AND status = 'RESERVED'")
    int markPaid(@Param("orderId") String orderId);

    @Update("UPDATE groupbuy_members SET status = 'CONFIRMED', updated_by = 0, updated_at = NOW() " +
            "WHERE group_id = #{groupId} AND status = 'PAID'")
    int markConfirmedByGroup(@Param("groupId") Long groupId);

    @Update("UPDATE groupbuy_members SET status = 'CANCELLED', updated_by = 0, updated_at = NOW() " +
            "WHERE order_id = #{orderId} AND status = 'RESERVED'")
    int cancelReservation(@Param("orderId") String orderId);

    @Update("UPDATE groupbuy_members SET status = 'REFUNDING', updated_by = 0, updated_at = NOW() " +
            "WHERE group_id = #{groupId} AND status = 'PAID'")
    int markRefundingByGroup(@Param("groupId") Long groupId);

    @Update("UPDATE groupbuy_members SET status = 'REFUNDING', updated_by = 0, updated_at = NOW() " +
            "WHERE order_id = #{orderId} AND status = 'PAID'")
    int markRefunding(@Param("orderId") String orderId);

    @Update("UPDATE groupbuy_members SET status = 'REFUNDED', updated_by = 0, updated_at = NOW() " +
            "WHERE order_id = #{orderId} AND status = 'REFUNDING'")
    int markRefunded(@Param("orderId") String orderId);
}
