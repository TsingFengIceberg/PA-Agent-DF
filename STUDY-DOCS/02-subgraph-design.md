# 02 — SubGraph 构建与编译隔离

> **日期**: 2026-05-14 | **Sprint**: 1 | **作者**: Wu Gang + Claude

---

## 涉及源文件

| 文件 | 角色 |
|------|------|
| [`backend/packages/harness/deerflow/collaboration/subgraphs/research_subgraph.py`](../backend/packages/harness/deerflow/collaboration/subgraphs/research_subgraph.py) | Research SubGraph 骨架（Sprint 2 填装逻辑） |
| [`backend/packages/harness/deerflow/collaboration/subgraphs/analysis_subgraph.py`](../backend/packages/harness/deerflow/collaboration/subgraphs/analysis_subgraph.py) | Analysis SubGraph 骨架（Sprint 3 填装逻辑） |
| [`backend/packages/harness/deerflow/collaboration/state.py`](../backend/packages/harness/deerflow/collaboration/state.py) | SubGraph State Schema 定义 |

---

## Q1: `raise NotImplementedError` 是什么？ `📄 research_subgraph.py`

**A:** Sprint 1 的节点只是骨架占位，不执行任何逻辑。

```python
def pi_agent_node(state: ResearchSubGraphState) -> dict:
    """PI Agent — 规划研究任务 + Send API Fan-out 分发到 Scouts。"""
    raise NotImplementedError("pi_agent_node — Sprint 2 实现")
```

**为什么用 `raise` 而不是 `pass`？** 如果图不小心被 `invoke()` 走到了这些占位节点，`pass` 会静默返回 `None`（LangGraph 可能把它当成合法的状态更新），导致状态错乱且极难排查。`raise` 立即崩溃报错——**尽早暴露未完成部分**。

到 Sprint 2/3 实现节点真实逻辑时，`raise` 会被替换成 SubagentExecutor 调用、LLM 推理等。

---

## Q2: 为什么提前声明节点（骨架）？ `📄 research_subgraph.py`

**A:** 自顶向下的设计方法——先把结构和接口定好，编译验证通过，再填内部实现。

```
Sprint 1（现在）:          Sprint 2/3（将来）:
┌──────────────────┐       ┌──────────────────────┐
│ 节点签名 + 路由    │  →   │ 节点内部 SubagentExecutor │
│ 图结构 + 编译通过  │       │ 真实 LLM 推理 + 工具调用  │
│ State 定义正确     │       │ 对抗式批判协议实现       │
└──────────────────┘       └──────────────────────┘
   接口验证在前               逻辑实现在后
```

类似于先写 interface 再写实现类。好处是：
1. **Sprint 1 就有可编译的图**——能看到节点连接是否正确，路由是否可达
2. **接口即文档**——`pi_agent_node(state) -> dict` 这条签名比任何文字都精确地描述了"PI 做什么"
3. **并行开发**——Sprint 2 可以实现 PI 和 Data Scout 同时进行，因为接口已定

---

## Q3: `StateGraph` 是什么？ `📄 research_subgraph.py`

**A:** `StateGraph` 是 LangGraph 的核心工厂函数，来自 `langgraph.graph`。

```python
from langgraph.graph import StateGraph
from deerflow.collaboration.state import ResearchSubGraphState

builder = StateGraph(ResearchSubGraphState)   # ① 创建 Builder，绑定 State Schema
builder.add_node("pi_agent", pi_agent_node)   # ② 注册节点
builder.add_edge("pi_agent", "critic_agent")  # ③ 连接边
builder.set_entry_point("pi_agent")            # ④ 设置入口
graph = builder.compile()                      # ⑤ 编译成可执行图
```

**每一步做了什么：**

| 步骤 | API | 作用 |
|------|-----|------|
| ① | `StateGraph(Schema)` | 创建 Builder，LangGraph 为 Schema 的每个字段创建 channel（状态通道） |
| ② | `add_node(name, fn)` | 注册节点：名字是图的顶点，fn 是到达该顶点时执行的函数 |
| ③ | `add_edge(a, b)` | 固定边：a 执行完后无条件跳到 b |
| ④ | `set_entry_point(name)` | 图的起点：`invoke()` 时从哪个节点开始 |
| ⑤ | `compile()` | 编译：验证所有节点签名、边连接完整性、生成执行计划 |

**`StateGraph(Schema)` 的参数就是 State 类型**——它告诉 LangGraph："这个图的所有节点都读写这个类型的状态"。编译时 LangGraph 会：
- 为 Schema 的每个字段创建 channel
- 验证所有节点的返回 dict 的 key 都在 Schema 内
- 处理 `Annotated[list, add]` reducer（多分支并发时的合并策略）

**`builder.compile()` 的产物**是 `CompiledStateGraph`——这个对象可以直接传给 `add_node(name, compiled_graph, state_in=fn, state_out=fn)` 挂载到父图。

---

## Q4: Research 子图的输入/输出在哪体现？ `📄 research_subgraph.py` `📄 state_mapping.py`

**A:** 分两个层面。

**图内层面** — 节点函数签名决定每个节点读写什么：

```python
def pi_agent_node(state: ResearchSubGraphState) -> dict:
    #      ↑ 输入: LangGraph 自动传入当前图状态       ↑ 输出: 要更新的字段 dict
```

- `state` — LangGraph 在调用节点时自动从 channel 组装出当前 `ResearchSubGraphState` 并传入
- `-> dict` — 返回的 dict 包含要更新的字段，LangGraph 自动 merge 回状态的对应 channel

**挂载层面** — `state_in` / `state_out` 控制子图与外部的数据交换（在 `graph.py` 中配置）：

```python
# graph.py
builder.add_node(
    "research_subgraph",
    build_research_subgraph(),          # ← 编译好的子图
    state_in=map_parent_to_research,    # ← 入口投影: Parent → Research
    state_out=map_research_to_parent,   # ← 出口投影: Research → Parent
)
```

```
调用子图时:
  Parent.validated_brief ──[state_in]──→ ResearchSubGraphState  ← 节点看到的 state
  Parent.workflow_type   ──[state_in]──→ ResearchSubGraphState

子图结束时:
  ResearchSubGraphState ──[state_out]──→ Parent.validated_brief
  ResearchSubGraphState ──[state_out]──→ Parent.collaboration_error
```

**关键**：子图内部完全不知道 Parent 的存在。它只认自己的 `ResearchSubGraphState`。数据进出由 `state_in`/`state_out` 两个纯函数代理。这就是 Q3 中"父子隔离"的具体实现。

---

## Q5: `add_conditional_edges` 和 `add_edge` 的区别？ `📄 research_subgraph.py`

**A:** 两种边的语义：

| | `add_edge` | `add_conditional_edges` |
|---|---|---|
| 路由方式 | 固定：A 完成 → 无条件跳到 B | 动态：A 完成 → 执行 router 函数 → 跳到对应节点 |
| 典型场景 | `pi_agent → critic_agent`（顺序） | `critic → scout 或 judge`（根据质疑结果决定） |
| 返回值 | 无 | router 函数返回字符串，匹配 path_map |

```python
# 固定边: Scout 补采完一定回到 Critic 重新审查
builder.add_edge("data_scout", "critic_agent")

# 条件边: Critic 审查后根据结果决定下一步
builder.add_conditional_edges("critic_agent", route_after_critic, {
    "data_scout": "data_scout",    # 还有质疑 → 补采
    "meta_judge": "meta_judge",    # 质疑解决 → 裁决
})

def route_after_critic(state) -> Literal["data_scout", "meta_judge"]:
    if state.get("challenges") and state.get("debate_round", 0) < 2:
        return "data_scout"   # 有质疑且未满2轮 → 继续补采
    return "meta_judge"        # 否则 → 进入裁决
```

`path_map` 的 key 是 router 函数的返回值，value 是目标节点名。`"__end__"` 映射到 `END` 表示图结束。

---

> **下一主题**: [03 — Parent Graph 组装与条件路由](03-graph-orchestration.md) *(待编码)*
