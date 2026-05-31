## ADDED Requirements

### Requirement: Agent 运行记录 RAG 索引和检索观测信息

系统 SHALL 在基础商机研究运行中记录 RAG evidence indexing 和 retrieval 的阶段历史、trace metadata 和安全错误摘要。

#### Scenario: RAG 索引阶段可观测

- **WHEN** 后台研究运行执行 `index_rag_evidence` 阶段
- **THEN** 系统保存该阶段事件记录
- **AND** 阶段事件包含任务 UUID、运行 ID、可空 trace ID、阶段状态、开始时间、完成时间、耗时、索引 chunk 数和可空错误摘要
- **AND** LangSmith tracing 启用时，该阶段可在同一条研究运行 trace 下关联查看

#### Scenario: RAG 检索调用可观测

- **WHEN** 竞品参考生成阶段执行 RAG evidence retrieval
- **THEN** 系统记录 retrieval query 数量、过滤范围、top-k、返回 chunk 数、来源链接数量和 fallback 状态
- **AND** LangSmith tracing 启用时，检索调用 metadata 包含任务 UUID、运行 ID、商机 UUID、来源类型过滤和召回数量
- **AND** 系统不把 API key、完整网页正文、原始异常堆栈或内部自增 ID 写入 trace metadata 或用户可见失败信息

#### Scenario: RAG 可观测异常不覆盖业务结果

- **WHEN** RAG 索引或检索的 trace 创建、metadata 写入或观测记录保存失败
- **THEN** 系统记录应用日志用于开发者排障
- **AND** 系统继续执行研究主流程或现有 fallback
- **AND** 研究任务不会仅因为 RAG 可观测系统异常而失败
