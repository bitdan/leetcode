//给定一个二叉树的根节点 root ，和一个整数 targetSum ，求该二叉树里节点值之和等于 targetSum 的 路径 的数目。 
//
// 路径 不需要从根节点开始，也不需要在叶子节点结束，但是路径方向必须是向下的（只能从父节点到子节点）。 
//
// 
//
// 示例 1： 
//
// 
//
// 
//输入：root = [10,5,-3,3,2,null,11,3,-2,null,1], targetSum = 8
//输出：3
//解释：和等于 8 的路径有 3 条，如图所示。
// 
//
// 示例 2： 
//
// 
//输入：root = [5,4,8,11,null,13,4,7,2,null,null,5,1], targetSum = 22
//输出：3
// 
//
// 
//
// 提示: 
//
// 
// 二叉树的节点个数的范围是 [0,1000] 
// 
// -10⁹ <= Node.val <= 10⁹ 
// -1000 <= targetSum <= 1000 
// 
//
// Related Topics 树 深度优先搜索 二叉树 👍 2157 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.HashMap;

@Slf4j
public class PathSumIii {
    public static void main(String[] args) {
        Solution solution = new PathSumIii().new Solution();
        TreeNode root = TreeNode.of(10, 5, -3, 3, 2, null, 11, 3, -2, null, 1);
        log.info("{}", solution.pathSum(root, 8));
    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        public int pathSum(TreeNode root, int targetSum) {
            HashMap<Long, Integer> prefixMap = new HashMap<>();
            prefixMap.put(0L, 1);
            return dfs(root, 0L, targetSum, prefixMap);
        }

        private int dfs(TreeNode root, long prefixSum, int targetSum, HashMap<Long, Integer> prefixMap) {
            if (root == null) return 0;
            prefixSum += root.val;
            int res = prefixMap.getOrDefault(prefixSum - targetSum, 0);
            prefixMap.put(prefixSum, prefixMap.getOrDefault(prefixSum, 0) + 1);
            res += dfs(root.left, prefixSum, targetSum, prefixMap);
            res += dfs(root.right, prefixSum, targetSum, prefixMap);
            prefixMap.put(prefixSum, prefixMap.get(prefixSum) - 1);
            return res;
        }

    }
//leetcode submit region end(Prohibit modification and deletion)

}
