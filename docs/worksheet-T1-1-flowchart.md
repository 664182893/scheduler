# T1-1 流程图填空练习（自己填细节）

> 用途：不看书，先把图里的 `填「...」` 补上，再对照答案。图只是骨架，细节由你填。
> 规则：每个空都按「输入 / 输出 / 失败谁处理」三样写；填不出就写「断了」，不要猜。
> 对照答案：`docs/SCHEDULER_STUDY_GUIDE.md`、`docs/review-2026-11-18.md`、`docs/SCHEDULER_CALLCHAIN.md`。

## 图 1：主干 6 阶段（粗颗粒）

```mermaid
graph TD
  A["0 入队：填「谁把 Pod 放进 activeQ」"] --> B["1 出队：填「哪个函数取 Pod」"]
  B --> C["2 选节点：填「三个子步骤」"]
  C --> D["3 占坑/预留：填「三个函数」"]
  D --> E["4 绑定：填「异步边界行号 + 谁写 apiserver」"]
  E --> F["5 收尾：填「finishBinding 做什么」"]
  C -->|"0 个可行节点"| P["填「走 PostFilter 还是直接失败」"]
  D -->|"Reserve 或 Permit 失败"| R["填「退哪两笔账」"]
```

## 图 2：`ScheduleOne` 的同步 / 异步分叉

```mermaid
sequenceDiagram
  participant M as 主 goroutine
  participant S as schedulingCycle
  participant B as binding goroutine
  M->>S: 填「调用所在行号」
  S-->>M: 填「返回哪三个值」
  alt 失败
    M->>M: 填「调用哪个 Handler，退账吗」
  else 成功
    M->>B: 填「哪一行起 goroutine」
    B->>B: 填「bindingCycle 的 4 个步骤」
  end
```

## 图 3：`schedulePod` 的四个短路口（重点）

```mermaid
graph TD
  A["schedulePod 开始"] --> B{"UpdateSnapshot 成功？"}
  B -->|"否"| B1["填「返回什么，谁处理，退账吗」"]
  B -->|"是"| C{"快照节点数 == 0？"}
  C -->|"是"| C1["填「哪个 error，会不会抢占」"]
  C -->|"否"| D["findNodesThatFitPod"]
  D --> E{"可行节点数"}
  E -->|"0"| E1["填「返回什么，PostFilter 做什么，最终 Status」"]
  E -->|"1"| E2["填「跳过哪两个阶段，为什么安全」"]
  E -->|">=2"| E3["填「prioritizeNodes 和 selectHost 各返回什么」"]
```

## 图 4：PreFilter / Filter / PostFilter

```mermaid
graph TD
  P["PreFilter：填「跑几次，范围」"] --> P1["填「PreFilterResult 怎么缩小节点集」"]
  P1 --> F["Filter：填「跑几次，是否并行」"]
  F --> F1["填「第一个失败怎么办，原因写哪」"]
  F1 --> G{"可行节点数 > 0？"}
  G -->|"是"| S["填「下一步做什么」"]
  G -->|"否"| PF["PostFilter：填「什么时候跑」"]
  PF --> PF1["填「DefaultPreemption 做什么，返回什么 Status」"]
```

## 图 5：第 4 步 `findNodesThatFitPod`（当前）

### 5-1 主流程与 PreFilter 的三种 Status

```mermaid
graph TD
  A["findNodesThatFitPod 开始"] --> B["allNodes = snapshot 节点列表"]
  B --> C["RunPreFilterPlugins"]
  C --> D{"PreFilter Status"}
  D -->|"Success"| E{"preRes.AllNodes()?"}
  D -->|"Rejected"| R["填：Diagnosis 怎么记？返回什么？为什么不是 error？"]
  D -->|"Error"| X["填：返回什么？谁处理？"]
  E -->|"true"| F["nodes = allNodes"]
  E -->|"false"| G["填：怎么用 NodeNames 构造 nodes？缺失/排除节点怎么标？"]
  F --> H["findNodesThatPassFilters（并行）"]
  G --> H
  H --> I["填：nextStartNodeIndex 怎么更新？出错也更新吗？"]
  I --> J["findNodesThatPassExtenders"]
  J --> K["填：返回哪三个值？Extender 过滤后补什么？"]
```

### 5-2 `NominatedNodeName` 提前返回

```mermaid
graph TD
  A{"NominatedNodeName 非空？"} -->|"是"| B["evaluateNominatedNode"]
  B --> C["填：里面跑哪两步？"]
  C --> D{"feasibleNodes 非空？"}
  D -->|"是"| E["填：返回什么？跳过哪一步？"]
  D -->|"否"| F["继续全量扫描"]
  A -->|"否"| F
```

### 5-3 `Diagnosis` 的四个字段

| 字段 | 谁写 | 什么时候写 |
|---|---|---|
| `NodeToStatus` | 填 | 填 |
| `UnschedulablePlugins` | 填 | 填 |
| `PreFilterMsg` | 填 | 填 |
| `PostFilterMsg` | 填 | 填 |

本步要填的 4 个空：

1. PreFilter `Rejected` 分支：Diagnosis 怎么记、返回什么、为什么不是 error？
2. PreFilter `Error` 分支：返回什么、谁处理？
3. `preRes.NodeNames` 怎么构造 `nodes`？缺失节点和排除节点怎么标？
4. `nextStartNodeIndex` 怎么更新？为什么出错也更新？

## 填空表

按「位置 / 一句话职责 / 返回值给谁 / 失败谁处理」四列填。

| 函数 | 文件:行号 | 一句话职责 | 返回值给谁 | 失败谁处理 |
|---|---|---|---|---|
| `ScheduleOne` | | | | |
| `schedulingCycle` | | | | |
| `schedulePod` | | | | |
| `findNodesThatFitPod` | | | | |
| `RunPreFilterPlugins` | | | | |
| `findNodesThatPassFilters` | | | | |
| `RunFilterPlugins` | | | | |
| `prioritizeNodes` | | | | |
| `selectHost` | | | | |
| `assume` | | | | |
| `RunReservePluginsReserve` | | | | |
| `RunPermitPlugins` | | | | |
| `bindingCycle` | | | | |
| `bind` | | | | |
| `RunBindPlugins` | | | | |
| `DefaultBinder.Bind` | | | | |
| `finishBinding` | | | | |
| `RunPostBindPlugins` | | | | |

## 自查清单

填完后逐条自问，答不出就回到图里补：

- [ ] 4 个短路口分别在什么条件触发？各自返回什么？
- [ ] `ErrNoNodesAvailable` 和 `FitError` 对抢占的影响有什么不同？
- [ ] 为什么 0 可行节点时 `EvaluatedNodes` 是 0？
- [ ] 默认日志级别能看到什么？`-v=4` 多看到什么？
- [ ] PreFilter 如何缩小节点集？Filter 的失败原因写到哪里？
- [ ] PostFilter 什么时候跑？跑完返回什么 Status？
- [ ] `go func` 在哪一行？之前必须完成哪三件事？
- [ ] `Reserve` / `Permit` 失败时，退账的两个动作是什么？

## 用法

1. 先只看图，不看文档，用 10–15 分钟填。
2. 填不出的空写「断了」，这就是下一轮的盲区。
3. 对照 `docs/review-2026-11-18.md` 和 `docs/SCHEDULER_STUDY_GUIDE.md` 批改。
4. 把错的写进 `progress.md` 的盲区台账，下一次验收先考这些。

## 怎么改图（Zed / GitHub）

- Markdown 预览是**只读**的；改的是 `.md` 文件里的 `mermaid` 代码块。
- 把 `填「...」` 替换成你的答案，保留外面的 `["..."]` 或 `{"..."}` 结构。
- 示例：
  ```text
  A["0 入队：填「谁把 Pod 放进 activeQ」"]
  ↓ 改成
  A["0 入队：informer → addPodToSchedulingQueue → activeQ"]
  ```
- Zed：命令面板 → `Markdown: Open Preview`；改源码后预览自动刷新。
- GitHub：点铅笔编辑代码块，切到 Preview 看渲染；PR review 里只能评论/建议，不能直接拖动节点。
- 不想碰 Mermaid 语法：直接填下面的「填空表」，效果一样。
