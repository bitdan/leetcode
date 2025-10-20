//给定一个二叉搜索树的根节点 root ，和一个整数 k ，请你设计一个算法查找其中第 k 小的元素（从 1 开始计数）。 
//
// 
//
// 示例 1： 
// 
// 
//输入：root = [3,1,4,null,2], k = 1
//输出：1
// 
//
// 示例 2： 
// 
// 
//输入：root = [5,3,6,2,4,null,null,1], k = 3
//输出：3
// 
//
// 
//
// 
//
// 提示： 
//
// 
// 树中的节点数为 n 。 
// 1 <= k <= n <= 10⁴ 
// 0 <= Node.val <= 10⁴ 
// 
//
// 
//
// 进阶：如果二叉搜索树经常被修改（插入/删除操作）并且你需要频繁地查找第 k 小的值，你将如何优化算法？ 
//
// Related Topics 树 深度优先搜索 二叉搜索树 二叉树 👍 1038 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class KthSmallestElementInABst {
    public static void main(String[] args) {
        Solution solution = new KthSmallestElementInABst().new Solution();
        TreeNode treeNode = TreeNode.of(5, 3, 6, 2, 4, null, null, 1);
        log.info("{}", solution.kthSmallest(treeNode, 3));
    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        private int result = 0;
        private int count = 0;

        public int kthSmallest(TreeNode root, int k) {
            inorder(root, k);
            return result;
        }

        public void inorder(TreeNode root, int k) {
            if (root == null) return;
            inorder(root.left, k);
            count++;
            if (count == k) {
                result = root.val;
                return;
            }
            inorder(root.right, k);
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
