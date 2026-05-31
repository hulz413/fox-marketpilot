## Purpose

定义 MarketPilot 内部 RAG 检索质量评测集、评测运行、P0 检索指标、LangSmith 观测和安全边界契约，用于复跑任务内 retriever 的召回与排序质量评估。

## Requirements

### Requirement: 系统维护中文 RAG 检索评测集

系统 SHALL 提供面向中文商机研究场景的 RAG 检索评测集，用于复跑任务内 retriever 的召回和排序质量评估。

#### Scenario: 评测集覆盖典型检索问题

- **WHEN** 团队加载默认 RAG 检索评测集
- **THEN** 系统提供多个中文评测 case
- **AND** case 覆盖需求、货源、竞品和风险类问题
- **AND** 每个 case 包含问题、类别、期望来源类型、期望关键词或判断点、默认 `top_k` 和评分说明
- **AND** 每个 case 使用公开 UUID 作为稳定标识

#### Scenario: 评测 case 支持分级相关性

- **WHEN** 系统评估某个 case 的召回 evidence
- **THEN** 系统可以为每条 evidence 记录 `0` 到 `3` 的相关性等级
- **AND** `0` 表示不相关
- **AND** `1` 表示弱相关
- **AND** `2` 表示相关
- **AND** `3` 表示强相关或关键证据
- **AND** 相关性等级可用于计算 `ndcg@k`

#### Scenario: 只使用启用的评测 case

- **WHEN** 系统准备一次 RAG 检索评测运行
- **THEN** 系统默认只选择启用且未软删除的评测 case
- **AND** 系统不读取 `deleted_at` 非空的评测 case
- **AND** 系统允许按类别筛选评测 case

#### Scenario: 评测集内容可版本化和复查

- **WHEN** 评测 case 来自仓库内默认 fixture 或数据库记录
- **THEN** 系统保留 case 的问题、期望来源类型、期望关键词或判断点和评分说明
- **AND** 系统在评测结果中保存本次运行使用的 case 快照或等价内容
- **AND** 后续 fixture 修改不会让历史评测结果失去可解释性

### Requirement: 系统运行 RAG 检索质量评测

系统 SHALL 支持对一条已完成研究任务或可复现测试任务运行 RAG 检索质量评测，并记录每个 case 的检索输入、召回证据和相关性判定。

#### Scenario: 成功运行一次基础检索评测

- **WHEN** 团队触发 RAG 检索质量评测运行且存在可用评测 case
- **THEN** 系统创建一条评测运行记录
- **AND** 系统为每个评测 case 构造 retrieval query
- **AND** 系统调用当前任务内 RAG retriever 获取 top-k evidence
- **AND** 系统记录召回 evidence 的公开来源 UUID、标题、URL、来源类型、支撑强度和 retriever 相关性分数
- **AND** 系统记录每条 evidence 的评测相关性等级和判定说明

#### Scenario: 评测运行关联研究任务和 trace

- **WHEN** 评测运行基于一条研究任务执行
- **THEN** 系统将评测运行关联到研究任务公开 UUID
- **AND** 系统保存可空 run ID、trace ID 和 trace URL
- **AND** 系统不对外暴露研究任务、来源、chunk、评测 case 或评测运行的内部自增 ID

#### Scenario: 单个 case 失败不终止整次评测

- **WHEN** 某个评测 case 的检索或评分失败
- **THEN** 系统将该 case 结果标记为 failed
- **AND** 系统保存中文安全错误摘要
- **AND** 系统继续执行后续评测 case
- **AND** 整次评测运行可以以 completed、partial 或 failed 状态结束

#### Scenario: 缺少 RAG 证据时记录空召回

- **WHEN** 当前任务没有可用 RAG chunks 或某个 case 没有召回证据
- **THEN** 系统为该 case 保存空召回结果
- **AND** 系统记录 empty 或 fallback 状态
- **AND** 系统将该 case 的检索指标按无命中结果处理或记录跳过原因

### Requirement: 系统计算 P0 检索质量指标

系统 SHALL 为每个评测 case 和整次评测运行计算 P0 检索质量指标：`hit_rate@k`、`recall@k`、`precision@k`、`mrr@k` 和 `ndcg@k`。

#### Scenario: 计算 hit_rate@k

- **WHEN** 系统完成一个评测 case 的 top-k 检索和相关性判定
- **THEN** 系统计算 `hit_rate@k`
- **AND** top-k 中至少存在一条相关性等级大于 `0` 的 evidence 时该 case 命中
- **AND** top-k 中不存在相关 evidence 时该 case 未命中

#### Scenario: 计算 recall@k

- **WHEN** 系统完成一个评测 case 的 top-k 检索和相关性判定
- **THEN** 系统计算 `recall@k`
- **AND** 系统基于该 case 的期望关键词、判断点或标注相关证据数量计算召回覆盖比例
- **AND** 召回率用于判断期望证据或关键判断点有多少被找回

#### Scenario: 计算 precision@k

- **WHEN** 系统完成一个评测 case 的 top-k 检索和相关性判定
- **THEN** 系统计算 `precision@k`
- **AND** 系统将 top-k 中相关性等级大于 `0` 的 evidence 视为相关结果
- **AND** 精确率用于判断 top-k 召回结果中的噪音比例

#### Scenario: 计算 mrr@k

- **WHEN** 系统完成一个评测 case 的 top-k 检索和相关性判定
- **THEN** 系统计算 `mrr@k`
- **AND** 系统基于第一个相关性等级大于 `0` 的 evidence 排名计算倒数排名
- **AND** top-k 中没有相关 evidence 时该 case 的 reciprocal rank 为 `0`

#### Scenario: 计算 ndcg@k

- **WHEN** 系统完成一个评测 case 的 top-k 检索和相关性判定
- **THEN** 系统计算 `ndcg@k`
- **AND** 系统使用 `0` 到 `3` 的相关性等级计算 DCG
- **AND** 系统使用该 case 的理想排序计算 IDCG
- **AND** `ndcg@k` 用于判断强相关或关键证据是否排在更靠前的位置

#### Scenario: 汇总整次评测指标

- **WHEN** 一次评测运行结束
- **THEN** 系统计算已完成 case 数、失败 case 数和跳过 case 数
- **AND** 系统计算 `hit_rate@k`、`recall@k`、`precision@k`、`mrr@k` 和 `ndcg@k` 的平均值或等价汇总
- **AND** 系统将汇总指标保存到评测运行记录
- **AND** 系统可以通过内部读取或导出结构查看本次检索评测结果

### Requirement: RAG 检索评测接入 LangSmith 观测

系统 SHALL 在 LangSmith 配置可用时，将 RAG 检索评测运行、case 输入输出、召回信息和 P0 指标写入可关联的 tracing metadata。

#### Scenario: LangSmith tracing 启用时记录评测 trace

- **WHEN** LangSmith tracing 已启用且团队运行 RAG 检索质量评测
- **THEN** 系统为评测运行创建或进入可追踪 trace
- **AND** trace metadata 包含评测运行 UUID、研究任务 UUID、可空研究 run ID、case 数量和评测类别
- **AND** 每个 case 的 trace metadata 包含 retrieval query、top-k、召回数量、相关性等级、P0 指标和状态
- **AND** trace metadata 不包含 API key、完整网页正文、原始异常堆栈或内部自增 ID

#### Scenario: LangSmith 未配置时评测仍可运行

- **WHEN** LangSmith tracing 未配置
- **THEN** 系统仍可加载评测集并运行基础检索评测
- **AND** 系统仍保存本地评测运行和结果
- **AND** 系统不因为缺少 LangSmith API key 而让评测运行失败

### Requirement: RAG 检索评测保持内部安全边界

系统 SHALL 将 RAG 检索评测作为内部质量观察能力，避免影响用户研究主流程或泄露敏感信息。

#### Scenario: 评测不阻断用户研究主流程

- **WHEN** RAG 检索评测运行失败、部分失败或未配置
- **THEN** 用户创建研究任务、运行研究、查看商机列表、详情和报告的流程不受影响
- **AND** 系统不因为评测失败而修改研究任务状态
- **AND** 系统不因为评测失败而删除已有商机、来源、RAG chunks 或分析结果

#### Scenario: 评测结果不作为用户可见商机结论

- **WHEN** 用户查看商机详情、报告或来源透明度信息
- **THEN** 系统不把内部 RAG 检索评测分数展示为商机可信度、市场成立度或推荐排序依据
- **AND** 系统不把检索评测结果描述为需求、供给、竞品或风险已经被证明
- **AND** 用户可见内容继续使用待验证和初步参考表达

#### Scenario: 评测错误摘要保持安全

- **WHEN** 评测运行、case 检索、外部 trace 写入或评分发生错误
- **THEN** 系统保存中文可理解的安全错误摘要
- **AND** 错误摘要不包含 API key、完整请求头、原始异常堆栈、完整网页正文或内部自增 ID
- **AND** 应用日志可以保留任务 UUID、评测运行 UUID、case UUID、错误类型和阶段名用于开发者排障
