# Ralph 循环

**Ralph 循环**是一种自引用开发循环。当你发送 `/ralph-loop` 命令并附带任务描述时，QwenPaw 的智能体会持续工作，每次迭代后检查任务是否完成。如果未完成，智能体会自动继续——直到任务 100% 完成、达到最大迭代次数限制、或你手动取消。

> Ralph 循环的灵感来自 [Ralph Loop](https://github.com/snarktank/ralph)。QwenPaw 的 [Mission Mode](./commands#mission-mode---autonomous-execution-for-complex-tasks) 也参考了同一设计思路，但 Ralph 循环更轻量——适用于不需要拆分为多故事的单次任务。

---

## 使用方法

### 启动 Ralph 循环

```
/ralph-loop <任务描述>
```

**示例：**

```
/ralph-loop 编写一个从 API 获取天气数据的 Python 脚本
/ralph-loop 创建一个支持拖拽上传的文件上传 React 组件
/ralph-loop 给项目添加代码格式化配置（ESLint + Prettier）
```

### 设置最大迭代次数

默认最大迭代次数为 20 次。你可以用 `--max-iterations` 参数自定义：

```
/ralph-loop --max-iterations=10 实现一个排序算法可视化工具
```

### 取消正在运行的循环

在循环运行期间，随时可以发送以下命令手动停止：

```
/cancel-loop
```

取消后智能体会停止工作，当前进度不会保存。

---

## 工作原理

Ralph 循环的执行流程如下：

1. **初始提示**：智能体接收任务描述和完成机制的说明，被告知用 `write_file` 工具写入 `completion.json` 文件来标记完成。
2. **工作迭代**：智能体使用可用工具（代码编辑、文件操作、终端命令等）处理任务。
3. **完成检查**：每次迭代后系统检查 `completion.json` 文件是否存在。如果存在，循环结束。
4. **继续或停止**：如果未完成且未达到最大迭代次数，系统会注入继续提示，智能体继续工作。否则循环终止。

### 完成检测机制

Ralph 循环采用 **文件式完成检测**，而非文本标签式：

- 智能体在完成任务后，通过 `write_file` 工具在当前工作目录创建 `completion.json` 文件
- 引擎每次迭代后检查该文件是否存在
- 这种方式比文本标签更健壮，避免了解析响应文本的歧义

---

## 完成条件

循环在以下任一条件满足时终止：

| 条件 | 说明 |
|------|------|
| **任务完成** | 智能体判断任务已完成并写入 `completion.json` 标记 |
| **达到最大迭代** | 达到迭代上限（默认 20 次）时自动停止 |
| **手动取消** | 使用 `/cancel-loop` 命令随时停止 |

---

## 在 Console 中查看进度

运行 Ralph 循环时，Console 聊天界面会显示简单的进度信息：

- 当前迭代次数 / 最大迭代次数（例如 "Iteration 3/20 - Working..."）
- 运行状态：运行中、已完成、已取消、达到上限

---

## 限制

- **仅 Console 可用**：Ralph 循环目前仅在 Console Web 界面中支持，不适用于 DingTalk、飞书、QQ 等渠道。
- **上下文保留**：智能体的对话上下文在迭代间保留，这意味着之前的思考和工作结果可以延续。
- **自动继续被禁用**：Ralph 循环运行期间，系统的自动继续（auto-continue）功能会被禁用，避免与循环自身的继续逻辑冲突。
- **无持久化**：循环状态仅保存在内存中，不会写入磁盘。如果重启服务，运行中的循环会丢失。
- **不支持嵌套**：Ralph 循环运行时不允许重复启动另一个循环。

---

## 相关页面

- [项目介绍](./intro) — 这个项目可以做什么
- [控制台](./console) — Web 界面与智能体切换
- [魔法命令](./commands) — `/mission`、`/plan`、`/clear` 等命令用法
- [Mission Mode](./commands#mission-mode---autonomous-execution-for-complex-tasks) — 适用于复杂长期任务的自主执行模式
