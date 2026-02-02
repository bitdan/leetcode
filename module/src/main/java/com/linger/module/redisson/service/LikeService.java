package com.linger.module.redisson.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RSet;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.Set;

/**
 * 朋友圈点赞服务
 * 使用Redisson的Set数据结构存储点赞用户列表
 *
 * @version 1.0
 * @description 朋友圈点赞功能
 * @date 2025/1/21
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class LikeService {

    private final RedissonClient redissonClient;

    /**
     * 点赞key前缀
     */
    private static final String LIKE_KEY_PREFIX = "moment:like:";

    /**
     * 用户点赞的帖子列表key前缀
     */
    private static final String USER_LIKED_KEY_PREFIX = "user:liked:";

    /**
     * 点赞
     *
     * @param momentId 朋友圈动态ID
     * @param userId   用户ID
     * @return true表示点赞成功，false表示已经点过赞
     */
    public boolean like(Long momentId, Long userId) {
        try {
            String likeKey = getLikeKey(momentId);
            String userLikedKey = getUserLikedKey(userId);

            RSet<Long> likeSet = redissonClient.getSet(likeKey);
            RSet<Long> userLikedSet = redissonClient.getSet(userLikedKey);

            // 判断是否已经点赞
            if (likeSet.contains(userId)) {
                log.info("用户{}已经对动态{}点过赞", userId, momentId);
                return false;
            }

            // 添加到点赞集合
            likeSet.add(userId);
            // 添加到用户点赞列表
            userLikedSet.add(momentId);

            log.info("用户{}成功点赞动态{}", userId, momentId);
            return true;
        } catch (Exception e) {
            log.error("点赞异常，momentId: {}, userId: {}", momentId, userId, e);
            return false;
        }
    }

    /**
     * 取消点赞
     *
     * @param momentId 朋友圈动态ID
     * @param userId   用户ID
     * @return true表示取消成功，false表示未点赞
     */
    public boolean unlike(Long momentId, Long userId) {
        try {
            String likeKey = getLikeKey(momentId);
            String userLikedKey = getUserLikedKey(userId);

            RSet<Long> likeSet = redissonClient.getSet(likeKey);
            RSet<Long> userLikedSet = redissonClient.getSet(userLikedKey);

            // 判断是否已经点赞
            if (!likeSet.contains(userId)) {
                log.info("用户{}未对动态{}点赞，无法取消", userId, momentId);
                return false;
            }

            // 从点赞集合中移除
            likeSet.remove(userId);
            // 从用户点赞列表中移除
            userLikedSet.remove(momentId);

            log.info("用户{}成功取消点赞动态{}", userId, momentId);
            return true;
        } catch (Exception e) {
            log.error("取消点赞异常，momentId: {}, userId: {}", momentId, userId, e);
            return false;
        }
    }

    /**
     * 切换点赞状态（如果已点赞则取消，如果未点赞则点赞）
     *
     * @param momentId 朋友圈动态ID
     * @param userId   用户ID
     * @return true表示当前是点赞状态，false表示当前是未点赞状态
     */
    public boolean toggleLike(Long momentId, Long userId) {
        try {
            String likeKey = getLikeKey(momentId);
            String userLikedKey = getUserLikedKey(userId);

            RSet<Long> likeSet = redissonClient.getSet(likeKey);
            RSet<Long> userLikedSet = redissonClient.getSet(userLikedKey);

            boolean isLiked = likeSet.contains(userId);

            if (isLiked) {
                // 取消点赞
                likeSet.remove(userId);
                userLikedSet.remove(momentId);
                log.info("用户{}切换点赞状态：取消点赞动态{}", userId, momentId);
                return false;
            } else {
                // 点赞
                likeSet.add(userId);
                userLikedSet.add(momentId);
                log.info("用户{}切换点赞状态：点赞动态{}", userId, momentId);
                return true;
            }
        } catch (Exception e) {
            log.error("切换点赞状态异常，momentId: {}, userId: {}", momentId, userId, e);
            throw new RuntimeException("切换点赞状态失败", e);
        }
    }

    /**
     * 判断用户是否已点赞
     *
     * @param momentId 朋友圈动态ID
     * @param userId   用户ID
     * @return true表示已点赞，false表示未点赞
     */
    public boolean isLiked(Long momentId, Long userId) {
        try {
            String likeKey = getLikeKey(momentId);
            RSet<Long> likeSet = redissonClient.getSet(likeKey);
            return likeSet.contains(userId);
        } catch (Exception e) {
            log.error("查询点赞状态异常，momentId: {}, userId: {}", momentId, userId, e);
            return false;
        }
    }

    /**
     * 获取点赞数量
     *
     * @param momentId 朋友圈动态ID
     * @return 点赞数量
     */
    public long getLikeCount(Long momentId) {
        try {
            String likeKey = getLikeKey(momentId);
            RSet<Long> likeSet = redissonClient.getSet(likeKey);
            return likeSet.size();
        } catch (Exception e) {
            log.error("查询点赞数量异常，momentId: {}", momentId, e);
            return 0;
        }
    }

    /**
     * 获取点赞用户列表
     *
     * @param momentId 朋友圈动态ID
     * @return 点赞用户ID集合
     */
    public Set<Long> getLikeUsers(Long momentId) {
        try {
            String likeKey = getLikeKey(momentId);
            RSet<Long> likeSet = redissonClient.getSet(likeKey);
            return likeSet.readAll();
        } catch (Exception e) {
            log.error("查询点赞用户列表异常，momentId: {}", momentId, e);
            return Collections.emptySet();
        }
    }

    /**
     * 获取用户点赞的动态列表
     *
     * @param userId 用户ID
     * @return 用户点赞的动态ID集合
     */
    public Set<Long> getUserLikedMoments(Long userId) {
        try {
            String userLikedKey = getUserLikedKey(userId);
            RSet<Long> userLikedSet = redissonClient.getSet(userLikedKey);
            return userLikedSet.readAll();
        } catch (Exception e) {
            log.error("查询用户点赞列表异常，userId: {}", userId, e);
            return Collections.emptySet();
        }
    }

    /**
     * 批量判断用户是否已点赞多个动态
     *
     * @param momentIds 朋友圈动态ID列表
     * @param userId    用户ID
     * @return 已点赞的动态ID集合
     */
    public Set<Long> batchCheckLiked(Set<Long> momentIds, Long userId) {
        try {
            Set<Long> likedMoments = getUserLikedMoments(userId);
            likedMoments.retainAll(momentIds);
            return likedMoments;
        } catch (Exception e) {
            log.error("批量查询点赞状态异常，userId: {}", userId, e);
            return Collections.emptySet();
        }
    }

    /**
     * 删除动态的所有点赞记录（用于删除动态时调用）
     *
     * @param momentId 朋友圈动态ID
     */
    public void deleteAllLikes(Long momentId) {
        try {
            String likeKey = getLikeKey(momentId);
            RSet<Long> likeSet = redissonClient.getSet(likeKey);
            Set<Long> userIds = likeSet.readAll();

            // 从每个用户的点赞列表中移除该动态
            for (Long userId : userIds) {
                String userLikedKey = getUserLikedKey(userId);
                RSet<Long> userLikedSet = redissonClient.getSet(userLikedKey);
                userLikedSet.remove(momentId);
            }

            // 删除点赞集合
            likeSet.delete();

            log.info("成功删除动态{}的所有点赞记录，共{}条", momentId, userIds.size());
        } catch (Exception e) {
            log.error("删除点赞记录异常，momentId: {}", momentId, e);
        }
    }

    /**
     * 清理用户的所有点赞记录（用于测试）
     *
     * @param userId 用户ID
     */
    public void clearUserLikes(Long userId) {
        try {
            String userLikedKey = getUserLikedKey(userId);
            RSet<Long> userLikedSet = redissonClient.getSet(userLikedKey);
            Set<Long> momentIds = userLikedSet.readAll();

            // 从每个动态的点赞列表中移除该用户
            for (Long momentId : momentIds) {
                String likeKey = getLikeKey(momentId);
                RSet<Long> likeSet = redissonClient.getSet(likeKey);
                likeSet.remove(userId);
            }

            // 删除用户点赞列表
            userLikedSet.delete();

            log.info("成功清理用户{}的所有点赞记录，共{}条", userId, momentIds.size());
        } catch (Exception e) {
            log.error("清理用户点赞记录异常，userId: {}", userId, e);
        }
    }

    /**
     * 获取点赞key
     */
    private String getLikeKey(Long momentId) {
        return LIKE_KEY_PREFIX + momentId;
    }

    /**
     * 获取用户点赞列表key
     */
    private String getUserLikedKey(Long userId) {
        return USER_LIKED_KEY_PREFIX + userId;
    }
}

