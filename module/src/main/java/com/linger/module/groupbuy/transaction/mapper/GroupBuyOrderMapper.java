package com.linger.module.groupbuy.transaction.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.linger.module.groupbuy.transaction.entity.GroupBuyOrderEntity;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.time.OffsetDateTime;
import java.util.List;

public interface GroupBuyOrderMapper extends BaseMapper<GroupBuyOrderEntity> {

    @Select("SELECT * FROM groupbuy_orders WHERE user_id = #{userId} AND request_id = #{requestId}")
    GroupBuyOrderEntity selectByUserRequest(@Param("userId") Long userId,
                                             @Param("requestId") String requestId);

    @Update("UPDATE groupbuy_orders SET status = 'WAIT_PAY', reservation_id = #{reservationId}, " +
            "pay_deadline = #{payDeadline}, version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{orderId} AND status = 'INIT'")
    int markWaitPay(@Param("orderId") String orderId,
                    @Param("reservationId") String reservationId,
                    @Param("payDeadline") OffsetDateTime payDeadline);

    @Update("UPDATE groupbuy_orders SET status = 'REJECTED', reject_reason = #{reason}, " +
            "version = version + 1, updated_by = 0, updated_at = NOW() WHERE id = #{orderId} AND status = 'INIT'")
    int markRejected(@Param("orderId") String orderId, @Param("reason") String reason);

    @Update("UPDATE groupbuy_orders SET status = 'PAID', payment_no = #{paymentNo}, paid_at = #{paidAt}, " +
            "version = version + 1, updated_by = 0, updated_at = NOW() WHERE id = #{orderId} AND status = 'WAIT_PAY'")
    int markPaid(@Param("orderId") String orderId,
                 @Param("paymentNo") String paymentNo,
                 @Param("paidAt") OffsetDateTime paidAt);

    @Update("UPDATE groupbuy_orders SET status = 'CANCELLED', version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{orderId} AND status = 'WAIT_PAY'")
    int cancelUnpaid(@Param("orderId") String orderId);

    @Update("UPDATE groupbuy_orders SET status = 'GROUP_SUCCESS', version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE group_id = #{groupId} AND status = 'PAID'")
    int markGroupSuccess(@Param("groupId") Long groupId);

    @Update("UPDATE groupbuy_orders SET status = 'REFUNDING', version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE group_id = #{groupId} AND status = 'PAID'")
    int markRefundingByGroup(@Param("groupId") Long groupId);

    @Update("UPDATE groupbuy_orders SET status = 'REFUNDING', version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{orderId} AND status = 'PAID'")
    int markRefunding(@Param("orderId") String orderId);

    @Update("UPDATE groupbuy_orders SET status = 'REFUNDED', version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{orderId} AND status = 'REFUNDING'")
    int markRefunded(@Param("orderId") String orderId);

    @Select("SELECT * FROM groupbuy_orders WHERE status = 'INIT' AND created_at < #{before} ORDER BY created_at LIMIT #{limit}")
    List<GroupBuyOrderEntity> selectStaleInit(@Param("before") OffsetDateTime before,
                                               @Param("limit") int limit);

    @Select("SELECT * FROM groupbuy_orders WHERE status = 'WAIT_PAY' AND pay_deadline <= NOW() " +
            "ORDER BY pay_deadline LIMIT #{limit}")
    List<GroupBuyOrderEntity> selectExpiredUnpaid(@Param("limit") int limit);

    @Select("SELECT * FROM groupbuy_orders WHERE group_id = #{groupId}")
    List<GroupBuyOrderEntity> selectByGroupId(@Param("groupId") Long groupId);
}
