## 1. 数据模型与检索评测集

- [x] 1.1 创建 `backend/app/modules/rag_quality_evaluation/` 模块结构，包含 models、schemas、repository、service、runner 和 fixture 入口。
- [x] 1.2 新增 Alembic migration，创建 `rag_evaluation_cases`、`rag_evaluation_runs` 和 `rag_evaluation_results` 表，并包含内部自增 `id`、公开 `uuid`、`created_at`、`updated_at`、`deleted_at`。
- [x] 1.3 实现 SQLAlchemy models 和 Pydantic schemas，确保对外读取使用公开 UUID，不暴露内部自增 ID。
- [x] 1.4 增加默认中文 MVP 检索评测集 fixture，覆盖需求、货源、竞品和风险类问题。
- [x] 1.5 为评测 case 支持 `question`、`category`、`expected_source_types`、`expected_keywords`、`expected_claims`、`top_k`、`grading_rubric` 和 `enabled` 字段。
- [x] 1.6 实现评测 case 加载、启用状态筛选、类别筛选和历史 case 快照保存逻辑。

## 2. 检索评测运行与 P0 指标

- [x] 2.1 实现评测运行创建、状态流转、完成/失败/部分失败统计和汇总指标保存。
- [x] 2.2 实现每个 case 的 retrieval query 构造，并复用现有 task-scoped RAG retriever 获取 top-k evidence。
- [x] 2.3 保存每个 case 的召回来源公开引用信息、retriever 相关性分数、评测相关性等级和判定说明。
- [x] 2.4 实现相关性评分器，为每条 evidence 输出 `0` 到 `3` 的相关性等级。
- [x] 2.5 实现 `hit_rate@k`、`recall@k`、`precision@k`、`mrr@k` 和 `ndcg@k` 的 case 级计算。
- [x] 2.6 实现整次评测运行的 P0 指标汇总，保存平均值、case 数量、失败数量和跳过数量。
- [x] 2.7 实现单 case 失败降级，确保检索或评分失败不会终止整次评测。
- [x] 2.8 实现无 RAG chunks、空召回和 embedding 不可用时的 empty/fallback 结果记录。

## 3. LangSmith 与内部运行入口

- [x] 3.1 为评测运行和单 case 执行接入 LangSmith tracing metadata，记录评测 run UUID、研究任务 UUID、case 数量、query、top-k、召回数量、相关性等级、P0 指标和状态。
- [x] 3.2 确保 LangSmith 未配置时使用 no-op，不影响本地评测结果。
- [x] 3.3 增加内部脚本或模块命令，用于选择已完成研究任务并运行一次 RAG 检索质量评测。
- [x] 3.4 输出或导出本次评测的 P0 指标汇总和 case 级检索结果，便于本地演示和排障。
- [x] 3.5 确保 trace metadata、错误摘要和导出结果不包含 API key、完整网页正文、原始异常堆栈或内部自增 ID。

## 4. 测试与验证

- [x] 4.1 增加数据模型、repository 和 fixture 加载测试，覆盖软删除记录默认不读取。
- [x] 4.2 增加成功检索评测运行测试，验证 case 结果、召回来源、相关性等级和 P0 指标持久化。
- [x] 4.3 增加指标计算单元测试，覆盖 `hit_rate@k`、`recall@k`、`precision@k`、`mrr@k` 和 `ndcg@k`。
- [x] 4.4 增加失败降级测试，覆盖单 case 失败、空召回、embedding 不可用和 LangSmith 未配置。
- [x] 4.5 增加安全边界测试，确认评测结果不暴露内部自增 ID、敏感凭证、原始堆栈或完整网页正文。
- [x] 4.6 增加或更新文档，说明如何在本地运行一次 RAG 检索质量评测和如何查看结果。
- [x] 4.7 运行 `pytest`，并确认现有研究任务、RAG 检索和竞品参考测试仍通过。
- [x] 4.8 运行一次本地评测示例，确认至少生成一条评测运行记录和 case 级 P0 检索指标。
