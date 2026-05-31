## ADDED Requirements

### Requirement: 竞品参考使用任务内 RAG 检索证据

系统 SHALL 在生成竞品参考时优先使用当前研究任务内的 RAG 检索结果，并在检索不可用时回退到现有来源选择和确定性 fallback。

#### Scenario: 基于 RAG 检索生成竞品参考

- **WHEN** 当前任务已经建立 RAG evidence chunks 且系统开始生成竞品参考
- **THEN** 系统为每个未软删除商机构造竞品参考检索 query
- **AND** 系统只在当前研究任务内检索相关 evidence chunks
- **AND** 系统优先检索同商机的 `competitor` 或 `general` 来源 chunks
- **AND** 竞品参考生成输入包含召回 chunk 文本、来源标题、URL、支撑强度和相关性分数

#### Scenario: 竞品参考关联 RAG 召回来源

- **WHEN** 竞品参考使用了 RAG 检索返回的 evidence chunks
- **THEN** 系统将竞品参考关联到这些 chunks 对应的未软删除研究来源
- **AND** 关联说明表达该来源是公开线索或初步参考
- **AND** 对外读取竞品参考时仍只暴露来源 UUID、标题、URL、摘要、来源类型、支撑强度和关联说明
- **AND** 系统不对外暴露 RAG chunk、来源、任务或商机的内部自增 ID

#### Scenario: RAG 检索不可用时回退

- **WHEN** 当前任务没有 RAG chunks、检索无结果、embedding 配置缺失或检索执行失败
- **THEN** 系统继续使用现有 `competitor`、`general` 来源选择逻辑生成竞品参考
- **AND** 若仍缺少可用来源，系统使用谨慎的待验证竞品参考 fallback
- **AND** 研究任务不因 RAG 检索不可用而失败

#### Scenario: RAG 竞品参考保持谨慎表达

- **WHEN** 系统基于 RAG 召回证据生成参考名称、售价区间、常见卖点、同质化程度或差异化切入点
- **THEN** 文案使用“类似产品参考”“公开线索”“可能”“需要验证”“待确认”或等价谨慎表达
- **AND** 文案不使用“竞品已全面核验”“售价已确认”“销量已确认”“市场已证明”或等价表达
