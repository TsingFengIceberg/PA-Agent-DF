# STUDY-DOCS 目录索引

> PA-Agent-DF 编码过程中的学习记录，按架构主题分类，非逐文件对应。

## 目录结构

| 编号 | 主题 | 文件 | 最后更新 |
|------|------|------|----------|
| 01 | 三层 State 体系 + State Mapping | [`01-state-system.md`](01-state-system.md) | 2026-05-14 (8 Q&A) |
| 02 | SubGraph 构建与编译隔离 | [`02-subgraph-design.md`](02-subgraph-design.md) | 2026-05-14 (10 Q&A) |
| 03 | Parent Graph 组装与条件路由 | [`03-graph-orchestration.md`](03-graph-orchestration.md) | 2026-05-14 (4 Q&A) |
| 04 | 测试模式与断言 | [`04-testing-patterns.md`](04-testing-patterns.md) | 2026-05-14 (3 Q&A) |
| 05 | 角色体系与权限门控 | *(待编码)* | — |
| 06 | 对抗式批判协议 | [`05-debate-protocol.md`](05-debate-protocol.md) | 2026-05-14 (3 Q&A) |
| 07 | 执行实例走读：Research SubGraph 全链路 | [`06-execution-walkthrough.md`](06-execution-walkthrough.md) | 2026-05-14 |
| 07 | HITL 人类审批门 | *(待编码)* | — |
| 08 | 配置与集成 | *(待编码)* | — |

## 关联源文件索引

| 源文件 | 相关学习文档 |
|--------|-------------|
| `backend/packages/harness/deerflow/collaboration/state.py` | 01 |
| `backend/packages/harness/deerflow/collaboration/subgraphs/state_mapping.py` | 01 |
| `backend/packages/harness/deerflow/collaboration/subgraphs/research_subgraph.py` | 02 |
| `backend/packages/harness/deerflow/collaboration/subgraphs/analysis_subgraph.py` | 02 |
| `backend/packages/harness/deerflow/collaboration/graph.py` | 03 |
| `backend/packages/harness/deerflow/agents/thread_state.py` | 01 |
| `backend/tests/test_collaboration_subgraphs.py` | 04 |
| `backend/tests/test_collaboration_graph.py` | 04 |
| `backend/tests/test_collaboration_debate.py` | 05 |
| `backend/tests/test_collaboration_nodes.py` | 02 |
| `backend/packages/harness/deerflow/collaboration/protocols/messages.py` | 05, 06 |
| `backend/packages/harness/deerflow/collaboration/protocols/debate.py` | 05, 06 |
| `backend/packages/harness/deerflow/collaboration/prompts/research_prompts.py` | 05, 06 |
| `backend/packages/harness/deerflow/collaboration/nodes/research_nodes.py` | 02, 06 |
