# 2025Unicom 无界智联——跨平台多智能体协同助手
仓库地址：https://github.com/Henry-Sucks/2025Unicom
## 项目简介：无界智联——跨平台多智能体协同助手
“无界智联”是一套基于多智能体协作与大语言模型（LLM）的智能任务自动化系统，旨在解决现代超级应用（Super App）中功能入口分散、界面动态变化、交互复杂等问题。系统通过功能导向的探索与任务分解，实现跨平台（Android、Web）高效执行复杂多步任务。

项目采用三智能体架构：

* Agent 1 – 功能探索与UTG构建

借助LLM语义识别和深度优先探索，构建以“功能-界面”为核心节点的UI过渡图（UTG），避免传统按页面节点建图的冗余与歧义。

* Agent 2 – 任务分解

基于UTG和自然语言输入，将复杂任务拆解为功能级子任务，确保任务规划与App实际功能路径精准匹配。

* Agent 3 – 导航与执行

在已知功能路径指导下执行具体操作，结合AutoDroid执行机制，保证动作准确性与安全性，并生成可追溯的执行链路。

技术特色与创新点：
* 功能语义抽象：将界面与核心功能绑定为节点，减少页面歧义，提高任务匹配准确率。
* 多智能体分工：LLM主要用于探索与任务规划阶段，执行阶段依赖UTG，降低大模型调用成本与延迟。
* 最优路径规划：结合功能语义与图搜索算法，减少无效跳转，提高执行效率。
* 跨平台可迁移性：通过功能语义抽象层，UTG可在Android与Web环境复用，减少重复探索成本。
* 可追溯执行链路：记录任务-功能-操作链路，便于验证与调试。
* 相比现有的DroidBot与AutoDroid，本项目在任务准确性、执行效率和成本控制方面实现了突破，为跨平台、多任务的智能化执行提供了可扩展且高效的解决方案。

## 部署方法&示例执行
安装方法：
```
cd tool\droidbot_execute
pip install -e .
cd tool\droidbot_explore
pip install -e .
```

示例执行：
```
.run.bat
```

使用方式：
UI树生成：
```
python main.py ^
  --explore ^
  --target-apk "C:\Projects\2025Unicom\apks\unicom.apk"  #测试目标APK路径
```
用户任务执行：
```
python main.py ^
  --execute ^
  --task "Book a flight ticket from Beijing to Shanghai for tomorrow" ^   # 任务描述
  --ui-tree-file ".\data\ui_tree_graph\Unicom App.json" ^               # UI树路径
  --target-apk ".\apks\unicom.apk"                                   # 测试目标APK路径
```

## 项目结构
`docs`：项目文档与演示视频
`apks`: 测试所用apk
```
data
 ui_tree_graph: Agent 1 构建的UTG
 planned_tasks: Agent 2 任务规划结果
 task_execution_result: Agent3 任务执行结果
```

