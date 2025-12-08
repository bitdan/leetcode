//在给定的 m x n 网格
// grid 中，每个单元格可以有以下三个值之一： 
//
// 
// 值 0 代表空单元格； 
// 值 1 代表新鲜橘子； 
// 值 2 代表腐烂的橘子。 
// 
//
// 每分钟，腐烂的橘子 周围 4 个方向上相邻 的新鲜橘子都会腐烂。 
//
// 返回 直到单元格中没有新鲜橘子为止所必须经过的最小分钟数。如果不可能，返回 -1 。 
//
// 
//
// 示例 1： 
//
// 
//
// 
//输入：grid = [[2,1,1],[1,1,0],[0,1,1]]
//输出：4
// 
//
// 示例 2： 
//
// 
//输入：grid = [[2,1,1],[0,1,1],[1,0,1]]
//输出：-1
//解释：左下角的橘子（第 2 行， 第 0 列）永远不会腐烂，因为腐烂只会发生在 4 个方向上。
// 
//
// 示例 3： 
//
// 
//输入：grid = [[0,2]]
//输出：0
//解释：因为 0 分钟时已经没有新鲜橘子了，所以答案就是 0 。
// 
//
// 
//
// 提示： 
//
// 
// m == grid.length 
// n == grid[i].length 
// 1 <= m, n <= 10 
// grid[i][j] 仅为 0、1 或 2 
// 
//
// Related Topics 广度优先搜索 数组 矩阵 👍 1102 👎 0


package com.linger.leetcode.editor.cn;

import lombok.extern.slf4j.Slf4j;

import java.util.LinkedList;
import java.util.Queue;

@Slf4j
public class RottingOranges {
    public static void main(String[] args) {
        Solution solution = new RottingOranges().new Solution();
        log.info("{}", solution.orangesRotting(new int[][]{{2, 1, 1}, {1, 1, 0}, {0, 1, 1}}));
    }

    //leetcode submit region begin(Prohibit modification and deletion)
    class Solution {
        public int orangesRotting(int[][] grid) {
            int m = grid.length;
            int n = grid[0].length;
            int freshCount = 0;
            int[][] dirs = {{0, 1}, {0, -1}, {1, 0}, {-1, 0}};
            Queue<int[]> queue = new LinkedList<>();
            for (int i = 0; i < m; i++) {
                for (int j = 0; j < n; j++) {
                    if (grid[i][j] == 1) {
                        freshCount++;
                    }
                    if (grid[i][j] == 2) {
                        queue.offer(new int[]{i, j});
                    }
                }
            }
            if (freshCount == 0) return 0;
            int time = 0;
            while (!queue.isEmpty()) {
                Boolean flag = false;
                int size = queue.size();
                while (size-- > 0) {
                    int[] poll = queue.poll();
                    for (int[] dir : dirs) {
                        int x = poll[0] + dir[0];
                        int y = poll[1] + dir[1];
                        if (x < 0 || x >= m || y < 0 || y >= n || grid[x][y] != 1) {
                            continue;
                        }

                        grid[x][y] = 2;
                        queue.offer(new int[]{x, y});
                        freshCount--;
                        flag = true;

                    }
                }
                if (flag) {
                    time++;
                }

            }
            return freshCount == 0 ? time : -1;
        }
    }
//leetcode submit region end(Prohibit modification and deletion)

}
