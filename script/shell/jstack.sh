#!/bin/bash
# 获取Java主进程PID
PID=$(jps -l | grep -v "Jps" | awk '{print $1}')
echo "Java主进程PID: $PID"

# 生成线程转储
jstack $PID > thread_dump.txt
echo "线程转储已保存到 thread_dump.txt"

# 获取高CPU线程信息
echo -e "\n高CPU线程分析："
echo "正在收集top 10高CPU线程..."
top -H -bn1 -p $PID | head -n 17 | tail -n 10 > high_cpu_threads.txt

# 添加十六进制转换
echo -e "\n线程PID(十进制)\t线程PID(十六进制)\tCPU%" >> high_cpu_threads.txt
top -H -bn1 -p $PID | head -n 17 | tail -n 10 | awk '{printf "%d\t0x%x\t%s\n", $1, $1, $9}' >> high_cpu_threads.txt

# 显示结果
echo -e "\nTop 10高CPU线程："
column -t -s $'\t' high_cpu_threads.txt

# 分析建议
echo -e "\n分析建议："
echo "1. 在线程转储中搜索对应线程："
echo "   grep -A 30 \"nid=0x<十六进制>\" thread_dump.txt"
echo "2. 检查线程状态和堆栈定位问题代码"
echo "3. 结果已保存到 high_cpu_threads.txt"
