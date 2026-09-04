package com.linger.module.groupbuy.transaction.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.linger.module.groupbuy.transaction.entity.GroupBuyGroupEntity;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

public interface GroupBuyGroupMapper extends BaseMapper<GroupBuyGroupEntity> {

    @Select("SELECT * FROM groupbuy_groups WHERE id = #{id} FOR UPDATE")
    GroupBuyGroupEntity selectForUpdate(@Param("id") Long id);

    @Update("UPDATE groupbuy_groups SET status = 'OPEN', version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND status = 'INIT'")
    int markOpen(@Param("id") Long id);

    @Update("UPDATE groupbuy_groups SET reserved_count = reserved_count + 1, version = version + 1, " +
            "updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND status = 'OPEN' AND reserved_count < target_count")
    int incrementReserved(@Param("id") Long id);

    @Update("UPDATE groupbuy_groups SET reserved_count = GREATEST(reserved_count - 1, 0), " +
            "version = version + 1, updated_by = 0, updated_at = NOW() WHERE id = #{id}")
    int decrementReserved(@Param("id") Long id);

    @Update("UPDATE groupbuy_groups SET paid_count = paid_count + 1, version = version + 1, " +
            "updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND status = 'OPEN' AND paid_count < target_count")
    int incrementPaid(@Param("id") Long id);

    @Update("UPDATE groupbuy_groups SET paid_count = GREATEST(paid_count - 1, 0), " +
            "reserved_count = GREATEST(reserved_count - 1, 0), version = version + 1, " +
            "updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id}")
    int decrementPaidAndReserved(@Param("id") Long id);

    @Update("UPDATE groupbuy_groups SET status = 'SUCCESS', version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND status = 'OPEN' AND paid_count >= target_count")
    int markSuccess(@Param("id") Long id);

    @Update("UPDATE groupbuy_groups SET status = 'FAILED', version = version + 1, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND status = 'OPEN' AND expire_at <= NOW()")
    int markFailedIfExpired(@Param("id") Long id);
}
