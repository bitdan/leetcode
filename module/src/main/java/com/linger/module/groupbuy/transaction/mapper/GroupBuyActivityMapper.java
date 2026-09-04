package com.linger.module.groupbuy.transaction.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.linger.module.groupbuy.transaction.entity.GroupBuyActivityEntity;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

public interface GroupBuyActivityMapper extends BaseMapper<GroupBuyActivityEntity> {

    @Select("SELECT * FROM groupbuy_activities WHERE id = #{id} FOR UPDATE")
    GroupBuyActivityEntity selectForUpdate(@Param("id") Long id);

    @Update("UPDATE groupbuy_activities SET status = 'RUNNING', version = version + 1, " +
            "updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND status = 'READY'")
    int markRunning(@Param("id") Long id);
}
