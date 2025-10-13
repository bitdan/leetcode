//给你一棵二叉树的根节点 root ，翻转这棵二叉树，并返回其根节点。 
//
// 
//
// 示例 1： 
//
// 
//
// 
//输入：root = [4,2,7,1,3,6,9]
//输出：[4,7,2,9,6,3,1]
// 
//
// 示例 2： 
//
// 
//
// 
//输入：root = [2,1,3]
//输出：[2,3,1]
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
// 树中节点数目范围在 [0, 100] 内 
// -100 <= Node.val <= 100 
// 
//
// Related Topics 树 深度优先搜索 广度优先搜索 二叉树 👍 2010 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class InvertBinaryTree {
    public static void main(String[] args) {
        Solution solution = new InvertBinaryTree().new Solution();
        log.info("{}", solution.invertTree(TreeNode.of(4, 2, 7, 1, 3, 6, 9)));
    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        public TreeNode invertTree(TreeNode root) {
            if (root == null) return null;
            TreeNode left = invertTree(root.left);
            TreeNode right = invertTree(root.right);
            return new TreeNode(root.val, right, left);
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
