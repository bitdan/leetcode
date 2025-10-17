//给你一个整数数组 nums ，其中元素已经按 升序 排列，请你将其转换为一棵 平衡 二叉搜索树。 
//
// 
//
// 示例 1： 
// 
// 
//输入：nums = [-10,-3,0,5,9]
//输出：[0,-3,9,-10,null,5]
//解释：[0,-10,5,null,-3,null,9] 也将被视为正确答案：
//
// 
//
// 示例 2： 
// 
// 
//输入：nums = [1,3]
//输出：[3,1]
//解释：[1,null,3] 和 [3,1] 都是高度平衡二叉搜索树。
// 
//
// 
//
// 提示： 
//
// 
// 1 <= nums.length <= 10⁴ 
// -10⁴ <= nums[i] <= 10⁴ 
// nums 按 严格递增 顺序排列 
// 
//
// Related Topics 树 二叉搜索树 数组 分治 二叉树 👍 1709 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class ConvertSortedArrayToBinarySearchTree {
    public static void main(String[] args) {
        Solution solution = new ConvertSortedArrayToBinarySearchTree().new Solution();
        TreeNode treeNode = solution.sortedArrayToBST(new int[]{-10, -3, 0, 5, 9});
        log.info("{}", treeNode);
    }
    //leetcode submit region begin(Prohibit modification and deletion)

    class Solution {
        public TreeNode sortedArrayToBST(int[] nums) {
            return buildTree(nums, 0, nums.length - 1);
        }

        public TreeNode buildTree(int[] nums, int left, int right) {
            if (left > right) return null;
            int mid = (left + right) / 2;
            TreeNode root = new TreeNode(nums[mid]);
            root.left = buildTree(nums, left, mid - 1);
            root.right = buildTree(nums, mid + 1, right);
            return root;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
