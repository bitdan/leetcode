package com.linger.module.groupbuy.transaction.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.linger.module.groupbuy.transaction.entity.GroupBuyOutboxEventEntity;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

public interface GroupBuyOutboxEventMapper extends BaseMapper<GroupBuyOutboxEventEntity> {

    @Insert("INSERT INTO groupbuy_outbox_events(id, event_type, aggregate_type, aggregate_id, payload) " +
            "VALUES(#{id}, #{eventType}, #{aggregateType}, #{aggregateId}, CAST(#{payload} AS JSONB))")
    int insertEvent(@Param("id") String id,
                    @Param("eventType") String eventType,
                    @Param("aggregateType") String aggregateType,
                    @Param("aggregateId") String aggregateId,
                    @Param("payload") String payload);

    @Select("WITH candidates AS (" +
            " SELECT id FROM groupbuy_outbox_events" +
            " WHERE (status = 'PENDING' OR (status = 'PROCESSING' AND locked_until < NOW()))" +
            " AND available_at <= NOW() ORDER BY available_at LIMIT #{limit} FOR UPDATE SKIP LOCKED" +
            ") UPDATE groupbuy_outbox_events e SET status = 'PROCESSING', locked_by = #{workerId}, updated_by = 0," +
            " locked_until = NOW() + INTERVAL '30 seconds', updated_at = NOW()" +
            " FROM candidates c WHERE e.id = c.id RETURNING e.*")
    List<GroupBuyOutboxEventEntity> claimBatch(@Param("workerId") String workerId,
                                                @Param("limit") int limit);

    @Update("UPDATE groupbuy_outbox_events SET status = 'DONE', locked_by = NULL, locked_until = NULL, updated_by = 0, " +
            "updated_at = NOW() WHERE id = #{id} AND status = 'PROCESSING' AND locked_by = #{workerId}")
    int markDone(@Param("id") String id, @Param("workerId") String workerId);

    @Update("UPDATE groupbuy_outbox_events SET status = CASE WHEN retry_count + 1 >= #{maxRetries} THEN 'DEAD' ELSE 'PENDING' END, " +
            "retry_count = retry_count + 1, available_at = NOW() + (INTERVAL '1 second' * #{delaySeconds}), " +
            "last_error = #{error}, locked_by = NULL, locked_until = NULL, updated_by = 0, updated_at = NOW() " +
            "WHERE id = #{id} AND locked_by = #{workerId}")
    int markFailed(@Param("id") String id,
                   @Param("workerId") String workerId,
                   @Param("maxRetries") int maxRetries,
                   @Param("delaySeconds") long delaySeconds,
                   @Param("error") String error);
}
