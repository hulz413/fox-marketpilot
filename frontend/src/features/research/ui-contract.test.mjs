import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

function readSource(path) {
  return readFileSync(resolve(projectRoot, path), "utf8");
}

test("task list keeps state-driven primary actions and secondary menu", () => {
  const source = readSource("src/features/research/research-task-list.tsx");

  assert.match(source, /查看结果/);
  assert.match(source, /查看进度/);
  assert.match(source, /开始研究/);
  assert.match(source, /重新运行/);
  assert.match(source, /更多操作/);
});

test("demo research samples are actionable real task entries", () => {
  const data = readSource("src/features/product-skeleton/data.ts");
  const samples = readSource("src/features/research/demo-research-samples.tsx");
  const emptyState = readSource("src/features/product-skeleton/components.tsx");

  assert.match(data, /sampleResearchRequests/);
  assert.match(data, /target_channels/);
  assert.match(data, /supply_preferences/);
  assert.match(samples, /createAndStartResearchTask/);
  assert.match(samples, /启动示例/);
  assert.match(samples, /正在启动/);
  assert.match(samples, /打开已创建任务/);
  assert.match(emptyState, /DemoResearchSamples/);
});

test("new research form supports sample fill and direct launch", () => {
  const source = readSource("src/features/research/new-research-form.tsx");

  assert.match(source, /sampleToFormValues/);
  assert.match(source, /fillWithSample/);
  assert.match(source, /DemoResearchSamples onFill/);
  assert.match(source, /createAndStartResearchTask/);
  assert.match(source, /直接启动一个完整演示任务/);
});

test("source transparency keeps cautious copy and non-blocking states", () => {
  const source = readSource("src/features/research/source-insights.tsx");

  assert.match(source, /公开线索/);
  assert.match(source, /初步参考/);
  assert.match(source, /待验证/);
  assert.match(source, /来源暂不可用/);
});

test("result pages include task context and source panels", () => {
  const report = readSource("src/features/reports/report-summary.tsx");
  const detail = readSource("src/features/opportunities/opportunity-detail.tsx");
  const shell = readSource("src/features/product-skeleton/components.tsx");

  assert.match(report, /TaskContextNavigation/);
  assert.match(report, /TaskSourceInsights/);
  assert.match(report, /TaskDemandInsightSummary/);
  assert.match(report, /TaskSupplyCandidateSummary/);
  assert.match(report, /TaskCompetitorReferenceSummary/);
  assert.match(report, /TaskValidationBudgetSummary/);
  assert.match(report, /TaskOpportunityRiskSummary/);
  assert.match(report, /TaskActionPlanSummary/);
  assert.match(detail, /OpportunitySourceInsights/);
  assert.match(detail, /OpportunityDemandInsightPanel/);
  assert.match(detail, /OpportunitySupplyCandidatePanel/);
  assert.match(detail, /OpportunityCompetitorReferencePanel/);
  assert.match(detail, /OpportunityValidationBudgetPanel/);
  assert.match(detail, /OpportunityRiskPanel/);
  assert.match(detail, /OpportunityActionPlanPanel/);
  assert.match(shell, /TaskContextNavigation/);
});

test("demand insights keep cautious copy and non-blocking states", () => {
  const source = readSource("src/features/research/demand-insights.tsx");

  assert.match(source, /需求洞察/);
  assert.match(source, /初步参考/);
  assert.match(source, /待验证/);
  assert.match(source, /暂不可用/);
});

test("supply candidates keep cautious copy and non-blocking states", () => {
  const source = readSource("src/features/research/supply-candidates.tsx");

  assert.match(source, /货源候选/);
  assert.match(source, /候选/);
  assert.match(source, /初步参考/);
  assert.match(source, /待确认/);
  assert.match(source, /待验证/);
  assert.match(source, /货源候选暂不可用/);
});

test("competitor references keep cautious copy and non-blocking states", () => {
  const source = readSource("src/features/research/competitor-references.tsx");

  assert.match(source, /竞品参考/);
  assert.match(source, /类似产品参考/);
  assert.match(source, /公开线索/);
  assert.match(source, /待确认/);
  assert.match(source, /待验证/);
  assert.match(source, /竞品参考暂不可用/);
});

test("validation budgets keep cautious copy and non-blocking states", () => {
  const source = readSource("src/features/research/validation-budgets.tsx");
  const progress = readSource("src/features/research/research-progress.tsx");

  assert.match(source, /验证预算/);
  assert.match(source, /粗略估算/);
  assert.match(source, /待验证假设/);
  assert.match(source, /验证预算暂不可用/);
  assert.match(progress, /estimate_validation_budgets/);
  assert.match(progress, /估算验证预算/);
});

test("research progress includes RAG evidence indexing stage", () => {
  const progress = readSource("src/features/research/research-progress.tsx");
  const api = readSource("src/features/research/api.ts");
  const taskList = readSource("src/features/research/research-task-list.tsx");
  const history = readSource("src/features/research/research-history-list.tsx");

  assert.match(api, /index_rag_evidence/);
  assert.match(progress, /index_rag_evidence/);
  assert.match(progress, /整理公开来源证据/);
  assert.match(progress, /待验证证据/);
  assert.match(taskList, /整理公开来源证据/);
  assert.match(history, /整理公开来源证据/);
});

test("opportunity risks keep cautious copy and non-blocking states", () => {
  const source = readSource("src/features/research/opportunity-risks.tsx");
  const progress = readSource("src/features/research/research-progress.tsx");

  assert.match(source, /风险复核/);
  assert.match(source, /待验证/);
  assert.match(source, /需要确认/);
  assert.match(source, /风险复核暂不可用/);
  assert.match(source, /合规、供应商履约、库存或平台规则已经完成核验/);
  assert.match(progress, /review_opportunity_risks/);
  assert.match(progress, /复核商机风险/);
});

test("action plans keep cautious copy and non-blocking states", () => {
  const source = readSource("src/features/research/action-plans.tsx");
  const progress = readSource("src/features/research/research-progress.tsx");

  assert.match(source, /行动计划/);
  assert.match(source, /人工执行/);
  assert.match(source, /待确认/);
  assert.match(source, /行动计划暂不可用/);
  assert.match(source, /不代表系统已经自动触达外部平台或完成真实验证/);
  assert.match(progress, /create_action_plans/);
  assert.match(progress, /生成行动计划/);
});

test("interactive controls use pointer cursor while disabled controls do not", () => {
  const button = readSource("src/components/ui/button.tsx");
  const dropdown = readSource("src/components/ui/dropdown-menu.tsx");

  assert.match(button, /cursor-pointer/);
  assert.match(button, /disabled:cursor-not-allowed/);
  assert.doesNotMatch(button, /cursor-default/);
  assert.match(dropdown, /cursor-pointer/);
  assert.match(dropdown, /data-\[disabled\]:cursor-not-allowed/);
});
