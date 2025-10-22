package com.linger.leetcode.editor.cn;

import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;
import java.util.Queue;

/**
 * @version 1.0
 * @description TreeNode
 * @date 2025/9/22 11:00:23
 */
@NoArgsConstructor
@AllArgsConstructor
@Slf4j
public class TreeNode {
    public int val;
    public TreeNode left;
    public TreeNode right;

    TreeNode(int val) {
        this.val = val;
    }

    // 可变参数创建树（层序遍历）

    /**
     * 检查数组是否合法：
     * <p>
     * 如果数组为空或者第一个元素为 null，直接返回 null。
     * <p>
     * 创建根节点，放入队列：
     * <p>
     * 队列用于存储还需要挂子节点的节点。
     * <p>
     * 遍历数组剩余元素：
     * <p>
     * 每次从队列取出当前节点：
     * <p>
     * 给左节点赋值（如果不是 null），然后入队
     * <p>
     * 给右节点赋值（如果不是 null），然后入队
     * <p>
     * 注意每次取两个数组元素（左、右）
     * <p>
     * 循环直到数组遍历完。
     *
     * @param values
     * @return
     */
    public static TreeNode of(Integer... values) {
        if (values == null || values.length == 0 || values[0] == null) return null;

        TreeNode root = new TreeNode(values[0]);
        Queue<TreeNode> queue = new LinkedList<>();
        queue.offer(root);
        int i = 1;

        while (i < values.length) {
            TreeNode current = queue.poll();
            if (current == null) continue;

            // 左节点
            if (i < values.length && values[i] != null) {
                current.left = new TreeNode(values[i]);
                queue.offer(current.left);
            }
            i++;

            // 右节点
            if (i < values.length && values[i] != null) {
                current.right = new TreeNode(values[i]);
                queue.offer(current.right);
            }
            i++;
        }
        return root;
    }

    public static TreeNode find(TreeNode root, int val) {
        if (root == null) return null;
        if (root.val == val) return root;
        TreeNode left = find(root.left, val);
        if (left != null) return left;
        return find(root.right, val);
    }

    @Override
    public String toString() {
        List<String> result = new ArrayList<>();
        Queue<TreeNode> queue = new LinkedList<>();
        queue.offer(this);

        while (!queue.isEmpty()) {
            TreeNode node = queue.poll();
            if (node == null) {
                result.add("null");
                continue;
            }
            result.add(String.valueOf(node.val));
            // 只有在节点不为空时才加入左右子节点
            if (node.left != null || node.right != null) {
                queue.offer(node.left);
                queue.offer(node.right);
            }
        }

        // 去除末尾多余的 null
        int end = result.size() - 1;
        while (end >= 0 && "null".equals(result.get(end))) {
            end--;
        }
        return result.subList(0, end + 1).toString();
    }

}
