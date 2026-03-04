# Agent 模块设计指南

## 背景与目标
NoteLLM 当前以 RAG + LLM 为核心，所有请求都会触发检索。为了让系统具备“自主决策”和“按需检索”的能力，引入 LangGraph Agent，先进行意图判断，再决定是否执行 RAG 检索。

目标：
- 仅在需要时触发 RAG，降低成本与延迟
- 为未来多步推理、工具调用、规划执行打基础
- 不破坏现有存储与流式输出逻辑

## 模块边界与职责
### ChatMessageService
- 负责会话权限校验、消息持久化、SSE 流式输出
- 通过 Agent Graph 获取最终响应

### IntentClassifier（意图分类器）
- 使用 LLM 进行分类
- 仅输出单行 JSON：{"need_retrieval":"yes"|"no"}
- 分类失败默认 yes（保守策略）

### LangGraph Agent
- 通过状态机编排：意图判断 -> 可选检索 -> 构建 prompt -> 生成回复
- 复用现有 RAG / Memory / LLM 逻辑，避免重复造轮子

## 核心流程
1. 用户请求进入 ChatMessageService
2. Agent 执行 `classify_intent`
3. need_retrieval == yes 时执行 RAG 检索
4. 构建 prompt，调用 LLM 生成回答
5. 结果回写长期记忆队列

## LangGraph 状态与节点
### State 字段
- user_id, session_id, user_message, file_id
- history（短期记忆）
- long_term_memory（长期记忆）
- need_retrieval（yes/no）
- rag_context（检索证据）
- prompt_messages

### Node 列表
- classify_intent
- load_history
- load_long_term_memory
- retrieve_rag（条件执行）
- build_prompt

### 条件边
- need_retrieval == yes -> retrieve_rag
- need_retrieval == no -> build_prompt

## 意图分类（RAG Gate）
### Prompt 设计
- 明确“只输出 JSON”
- few-shot 覆盖问候、常识、闲聊、文件相关问题

### 输出规范
- 单行 JSON
- 只允许 yes/no
- 解析失败默认 yes

## 错误处理与降级策略
- 意图分类失败：默认 yes
- RAG 检索失败：降级为空证据
- 长期记忆读取失败：降级为空

## 流式输出
- SSE 层保持不变
- Agent 仅负责产出 prompt 与最终响应

## 未来扩展方向
- 多步规划（Plan-and-Solve）
- 工具调用（搜索、数据库查询）
- 更细粒度的任务路由
