## ADDED Requirements

### Requirement: 研究运行建立任务内 RAG 证据索引

系统 SHALL 在来源收集阶段结束后，为当前研究任务建立任务内 RAG 证据索引，并在索引完成、跳过或失败后继续执行后续分析阶段。

#### Scenario: 来源收集后进入 RAG 索引阶段

- **WHEN** 后台研究运行完成 `collect_research_sources` 阶段
- **THEN** 系统进入 `index_rag_evidence` 阶段
- **AND** 系统基于当前任务的未软删除研究来源建立 RAG evidence chunks
- **AND** 系统在索引阶段结束后继续进入需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划阶段

#### Scenario: RAG 索引失败不覆盖基础结果

- **WHEN** 商机结果已经成功持久化但 RAG 索引、embedding 或 pgvector 写入失败
- **THEN** 系统保留已生成的商机结果和已收集来源
- **AND** 系统仍可以进入需求洞察生成阶段
- **AND** 系统仍可以进入竞品参考生成阶段并使用现有来源选择 fallback
- **AND** 系统可以将研究任务状态更新为 `completed`
- **AND** 系统记录 RAG 索引失败的阶段事件和应用日志

#### Scenario: 基础商机生成边界保持不变

- **WHEN** 系统执行基础商机生成、结果校验和商机持久化阶段
- **THEN** 系统仍不调用 Tavily、Playwright、网页正文提取、向量检索或 RAG 流程来生成基础商机推荐
- **AND** RAG evidence indexing 只发生在来源收集阶段结束之后
- **AND** 系统不要求基础商机结果包含 RAG 引用
