//给定一个候选人编号的集合 candidates 和一个目标数 target ，找出 candidates 中所有可以使数字和为 target 的组合。 
//
// candidates 中的每个数字在每个组合中只能使用 一次 。 
//
// 注意：解集不能包含重复的组合。 
//
// 
//
// 示例 1: 
//
// 
//输入: candidates = [10,1,2,7,6,1,5], target = 8,
//输出:
//[
//[1,1,6],
//[1,2,5],
//[1,7],
//[2,6]
//] 
//
// 示例 2: 
//
// 
//输入: candidates = [2,5,2,1,2], target = 5,
//输出:
//[
//[1,2,2],
//[5]
//] 
//
// 
//
// 提示: 
//
// 
// 1 <= candidates.length <= 100 
// 1 <= candidates[i] <= 50 
// 1 <= target <= 30 
// 
//
// Related Topics 数组 回溯 👍 1742 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Slf4j
public class CombinationSumIi {
    public static void main(String[] args) {
        Solution solution = new CombinationSumIi().new Solution();
        log.info("{}", solution.combinationSum2(new int[]{10, 1, 2, 7, 6, 1, 5}, 8));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        private List<List<Integer>> res = new ArrayList<>();
        private List<Integer> path = new ArrayList<>();

        public List<List<Integer>> combinationSum2(int[] candidates, int target) {
            Arrays.sort(candidates);
            dfs(candidates, target, 0, 0);
            return res;
        }

        private void dfs(int[] candidates, int target, int sum, int start) {
            if (sum == target) {
                res.add(new ArrayList<>(path));
                return;
            }
            for (int i = start; i < candidates.length; i++) {
                if (sum + candidates[i] > target) {
                    break;
                }
                if (i > start && candidates[i] == candidates[i - 1]) {
                    continue;
                }
                path.add(candidates[i]);
                dfs(candidates, target, sum + candidates[i], i + 1);
                path.remove(path.size() - 1);
            }

        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
