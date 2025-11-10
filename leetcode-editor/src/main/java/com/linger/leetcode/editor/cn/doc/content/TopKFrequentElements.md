<p>给你一个整数数组 <code>nums</code> 和一个整数 <code>k</code> ，请你返回其中出现频率前 <code>k</code> 高的元素。你可以按 <strong>任意顺序</strong> 返回答案。</p>

<p>&nbsp;</p>

<p><strong class="example">示例 1：</strong></p>

<div class="example-block"> 
 <p><span class="example-io"><b>输入：</b>nums = [1,1,1,2,2,3], k = 2</span></p> 
</div>

<p><strong>输出：</strong><span class="example-io">[1,2]</span></p>

<p><strong class="example">示例 2：</strong></p>

<div class="example-block"> 
 <p><span class="example-io"><b>输入：</b>nums = [1], k = 1</span></p> 
</div>

<p><span class="example-io"><b>输出：</b>[1]</span></p>

<p><strong class="example">示例 3：</strong></p>

<div class="example-block"> 
 <p><span class="example-io"><b>输入：</b>nums = [1,2,1,2,1,2,3,1,3,2], k = 2</span></p> 
</div>

<p><strong>输出：</strong><span class="example-io">[1,2]</span></p>

<p>&nbsp;</p>

<p><strong>提示：</strong></p>

<ul> 
 <li><code>1 &lt;= nums.length &lt;= 10<sup>5</sup></code></li> 
 <li><code>k</code> 的取值范围是 <code>[1, 数组中不相同的元素的个数]</code></li> 
 <li>题目数据保证答案唯一，换句话说，数组中前 <code>k</code> 个高频元素的集合是唯一的</li> 
</ul>

<p>&nbsp;</p>

<p><strong>进阶：</strong>你所设计算法的时间复杂度 <strong>必须</strong> 优于 <code>O(n log n)</code> ，其中 <code>n</code><em>&nbsp;</em>是数组大小。</p>

<div><div>Related Topics</div><div><li>数组</li><li>哈希表</li><li>分治</li><li>桶排序</li><li>计数</li><li>快速选择</li><li>排序</li><li>堆（优先队列）</li></div></div><br><div><li>👍 2087</li><li>👎 0</li></div>