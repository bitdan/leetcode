//给你一个二叉树的根节点 root ， 检查它是否轴对称。 
//
// 
//
// 示例 1： 
// 
// 
//输入：root = [1,2,2,3,4,4,3]
//输出：true
// 
//
// 示例 2： 
// 
// 
//输入：root = [1,2,2,null,3,null,3]
//输出：false
// 
//
// 
//
// 提示： 
//
// 
// 树中节点数目在范围 [1, 1000] 内 
// -100 <= Node.val <= 100 
// 
//
// 
//
// 进阶：你可以运用递归和迭代两种方法解决这个问题吗？ 
//
// Related Topics 树 深度优先搜索 广度优先搜索 二叉树 👍 3011 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class SymmetricTree {
    public static void main(String[] args) {
        Solution solution = new SymmetricTree().new Solution();
        log.info("{}", solution.isSymmetric(TreeNode.of(1, 2, 2, 3, 4, 4, 3)));
        log.info("{}", solution.isSymmetric(TreeNode.of(1, 2, 2, null, 3, null, 3)));
    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        public boolean isSymmetric(TreeNode root) {
            return isMirror(root, root);

        }

        private boolean isMirror(TreeNode t1, TreeNode t2) {
            if (t1 == null && t2 == null) return true;
            if (t1 == null || t2 == null) return false;
            return (t1.val == t2.val) && isMirror(t1.right, t2.left) && isMirror(t1.left, t2.right);
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
