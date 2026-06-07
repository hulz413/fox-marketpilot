## 1. 数据模型和评测集

- [x] 1.1 创建 `backend/app/modules/generation_quality_evaluation/` 模块结构，包含 models、schemas、repository、service、runner、scorer 和 fixture 入口。
- [x] 1.2 新增 Alembic migration，创建 `generation_evaluation_cases`、`generation_evaluation_runs` 和 `generation_evaluation_results` 表，并包含内部自增 `id`、公开 `uuid`、`created_at`、`updated_at`、`deleted_at`。
- [x] 1.3 实现 SQLAlchemy models 和 Pydantic schemas，确保对外读取使用公开 UUID，不暴露内部自增 ID。
- [x] 1.4 增加默认中文生成质量评测集 fixture，覆盖预算、渠道、排除品类、目标人群、供给偏好、风险质量、行动质量和谨慎边界。
- [x] 1.5 实现评测 case 加载、启用状态筛选、类别筛选和运行时 case 快照保存逻辑。

## 2. 生成质量评测运行

- [x] 2.1 实现 evaluation run 创建、状态流转、最近结果读取、过期判断和安全响应转换。
- [x] 2.2 实现对已完成研究任务的评测 runner，读取 active 商机结果和增强分析记录。
- [x] 2.3 实现未完成任务拒绝逻辑，确保评测不修改研究任务状态、当前阶段或已有结果。
- [x] 2.4 实现单 case 失败降级，确保评分或数据读取失败不会终止整次评测。
- [x] 2.5 保存逐 case result，包含 case 快照、rubric 分数、状态、原因、受影响商机公开 UUID 和安全错误摘要。

## 3. Rubric 评分和指标汇总

- [x] 3.1 实现约束遵守检查，覆盖预算、渠道、排除品类、目标人群、期望利润和供给来源偏好。
- [x] 3.2 实现结果数量和字段完整性检查，覆盖 3-5 个 active 商机和 MVP 必需字段。
- [x] 3.3 实现增强分析一致性检查，覆盖需求洞察、货源候选、竞品参考、验证预算、风险复核和行动计划。
- [x] 3.4 实现风险具体性和行动可执行性检查，识别空泛风险、缺少验证动作、缺少询盘话术或缺少检查清单。
- [x] 3.5 实现谨慎边界检查，识别已核验市场、供应商确认、利润保证、自动联系供应商、自动发布内容等禁止表达。
- [x] 3.6 实现整体状态和 rubric 维度指标汇总，保存 case 总数、通过数、warning 数、失败数、跳过数和中文摘要。

## 4. Readiness、观测和内部入口

- [x] 4.1 将最近一次 generation evaluation run 摘要接入 `research_quality_readiness` runner 的生成内容展示质量检查项。
- [x] 4.2 在 readiness 缺少 generation evaluation run 时保留原有 smoke check，并输出未检查或需复查提示。
- [x] 4.3 为 evaluation run 和单 case 执行接入结构化日志和可选 LangSmith tracing metadata。
- [x] 4.4 确保 LangSmith 未配置时使用 no-op，不影响本地评测运行和结果保存。
- [x] 4.5 新增内部脚本、模块命令或内部 API，用于对指定已完成任务运行生成质量评测并读取安全摘要。

## 5. 测试与验证

- [x] 5.1 增加数据模型、repository、fixture 加载和软删除过滤测试。
- [x] 5.2 增加成功生成质量评测运行测试，验证 run、case result、rubric 指标和安全响应持久化。
- [x] 5.3 增加 rubric scorer 单元测试，覆盖约束违反、字段缺失、增强不一致、空泛风险、不可执行行动和禁止表达。
- [x] 5.4 增加失败降级测试，覆盖未完成任务、单 case 失败、缺少增强分析和 LangSmith 未配置。
- [x] 5.5 增加 readiness 集成测试，确认生成质量评测摘要进入检查项，缺失或过期评测不会修改研究任务状态。
- [x] 5.6 增加安全边界测试，确认响应、日志和 trace metadata 不暴露内部自增 ID、敏感凭证、完整 prompt、原始异常堆栈或完整网页正文。
- [x] 5.7 运行 `openspec validate add-generation-quality-evaluation --strict`，并运行相关后端测试。
- [x] 5.8 对一条本地已完成研究任务运行示例评测，确认生成 evaluation run、case result 和 readiness 摘要。
