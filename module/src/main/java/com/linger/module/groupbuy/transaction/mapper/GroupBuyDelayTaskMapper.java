package com.linger.module.groupbuy.transaction.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.linger.module.groupbuy.transaction.entity.GroupBuyDelayTaskEntity;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

public interface GroupBuyDelayTaskMapper extends BaseMapper<GroupBuyDelayTaskEntity> {

    @Select("WITH candidates AS (" +
            " SELECT id FROM groupbuy_delay_tasks" +
            " WHERE (status = 'PENDING' OR (status IN ('CLAIMED', 'RUNNING') AND locked_until < NOW()))" +
            " AND execute_at <= NOW() + (INTERVAL '1 second' * #{loadAheadSeconds})" +
            " ORDER BY execute_at LIMIT #{limit} FOR UPDATE SKIP LOCKED" +
            ") UPDATE groupbuy_delay_tasks t SET status = 'CLAIMED', worker_id = #{workerId}, updated_by = 0," +
            " locked_until = NOW() + (INTERVAL '1 second' * #{lockSeconds}), updated_at = NOW()" +
            " FROM candidates c WHERE t.id = c.id RETURNING t.*")
    List<GroupBuyDelayTaskEntity> claimBatch(@Param("workerId") String workerId,
                                              @Param("limit") int limit,
                                              @Param("loadAheadSeconds") long loadAheadSeconds,
                                              @Param("lockSeconds") long lockSeconds);

    @Insert("INSERT INTO groupbuy_delay_tasks(task_type, business_id, execute_at) " +
            "VALUES(#{taskType}, #{businessId}, #{executeAt}) ON CONFLICT (task_type, business_id) DO NOTHING")
    int insertIgnore(@Param("taskType") String taskType,
                     @Param("businessId") String businessId,
                     @Param("executeAt") java.time.OffsetDateTime executeAt);

    @Update("UPDATE groupbuy_delay_tasks SET status = 'RUNNING', updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND status = 'CLAIMED' AND worker_id = #{workerId} AND locked_until > NOW()")
    int markRunning(@Param("id") Long id, @Param("workerId") String workerId);

    @Update("UPDATE groupbuy_delay_tasks SET status = 'DONE', worker_id = NULL, locked_until = NULL, updated_by = 0, " +
            "updated_at = NOW() WHERE id = #{id} AND status = 'RUNNING' AND worker_id = #{workerId}")
    int markDone(@Param("id") Long id, @Param("workerId") String workerId);

    @Update("UPDATE groupbuy_delay_tasks SET status = CASE WHEN retry_count + 1 >= #{maxRetries} THEN 'DEAD' ELSE 'PENDING' END, " +
            "retry_count = retry_count + 1, execute_at = NOW() + (INTERVAL '1 second' * #{delaySeconds}), " +
            "last_error = #{error}, worker_id = NULL, locked_until = NULL, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND worker_id = #{workerId}")
    int markFailed(@Param("id") Long id,
                   @Param("workerId") String workerId,
                   @Param("maxRetries") int maxRetries,
                   @Param("delaySeconds") long delaySeconds,
                   @Param("error") String error);
}
