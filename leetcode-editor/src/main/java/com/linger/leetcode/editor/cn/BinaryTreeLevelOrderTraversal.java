//给你二叉树的根节点 root ，返回其节点值的 层序遍历 。 （即逐层地，从左到右访问所有节点）。 
//
// 
//
// 示例 1： 
// 
// 
//输入：root = [3,9,20,null,null,15,7]
//输出：[[3],[9,20],[15,7]]
// 
//
// 示例 2： 
//
// 
//输入：root = [1]
//输出：[[1]]
// 
//
// 示例 3： 
//
// 
//输入：root = []
//输出：[]
// 
//
// 
//
// 提示： 
//
// 
// 树中节点数目在范围 [0, 2000] 内 
// -1000 <= Node.val <= 1000 
// 
//
// Related Topics 树 广度优先搜索 二叉树 👍 2196 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedList;
import java.util.List;

@Slf4j
public class BinaryTreeLevelOrderTraversal {
    public static void main(String[] args) {
        Solution solution = new BinaryTreeLevelOrderTraversal().new Solution();
        TreeNode treeNode = TreeNode.of(3, 9, 20, null, null, 15, 7);
        log.info("{}", solution.levelOrder(treeNode));

    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        public List<List<Integer>> levelOrder(TreeNode root) {
            ArrayList<List<Integer>> list = new ArrayList<>();
            if (root == null) {
                return list;
            }
            Deque<TreeNode> deque = new LinkedList<>();
            deque.offer(root);
            while (!deque.isEmpty()) {
                int size = deque.size();
                ArrayList<Integer> level = new ArrayList<>();
                for (int i = 0; i < size; i++) {
                    TreeNode node = deque.poll();
                    level.add(node.val);
                    if (node.left != null) {
                        deque.offer(node.left);
                    }
                    if (node.right != null) {
                        deque.offer(node.right);
                    }
                }
                list.add(level);
            }
            return list;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
