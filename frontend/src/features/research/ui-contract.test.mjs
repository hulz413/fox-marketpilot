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

  assert.match(source, /查看研究结果/);
  assert.match(source, /查看进度/);
  assert.match(source, /开始研究/);
  assert.match(source, /重新运行/);
  assert.match(source, /更多操作/);
  assert.match(source, /taskStatusFilters/);
  assert.match(source, /TaskTableColumnGroup/);
  assert.match(source, /className="table-fixed"/);
  assert.match(source, /grid-cols-\[minmax\(0,1fr\)_auto\] grid-rows-\[auto\] items-center/);
  assert.match(source, /pt-4 pb-3 \[\.border-b\]:pb-3/);
  assert.match(source, /<div className="grid gap-2">/);
  assert.match(source, /defaultResearchTaskPageSize = 10/);
  assert.match(source, /researchTaskPageSizeOptions = \[10, 20, 50, 100\]/);
  assert.match(source, /ResearchTaskPagination/);
  assert.match(source, /getPaginationItems/);
  assert.match(source, /paginatedTasks/);
  assert.match(source, /第一页/);
  assert.match(source, /上一页/);
  assert.match(source, /下一页/);
  assert.match(source, /最后一页/);
  assert.match(source, /每页条数/);
  assert.match(source, /\{count\} 条\/页/);
  assert.match(source, /DropdownMenuRadioGroup/);
  assert.match(source, /justify-end gap-3 border-t/);
  assert.match(source, /bg-muted shadow-none hover:bg-muted/);
  assert.doesNotMatch(source, /bg-muted ring-2 ring-ring\/50/);
  assert.match(source, /focus-visible:border-ring focus-visible:ring-\[3px\] focus-visible:ring-ring\/50/);
  assert.match(source, /aria-current/);
  assert.doesNotMatch(source, /\{shown\} \/ \{total\} 条记录/);
  assert.match(source, /t\("操作"\)/);
  assert.doesNotMatch(source, /t\("下一步"\)/);
  assert.match(source, /TaskActionGroup/);
  assert.match(source, /rounded-r-none/);
  assert.match(source, /rounded-l-none/);
  assert.match(source, /w-28 rounded-r-none/);
  assert.match(source, /w-9 rounded-l-none/);
  assert.match(source, /flex justify-start/);
  assert.doesNotMatch(source, /ArrowRight/);
  assert.doesNotMatch(source, /TimerReset/);
  assert.doesNotMatch(source, /Play/);
  assert.doesNotMatch(source, /演示状态/);
  assert.doesNotMatch(source, /TaskReadinessBadge/);
});

test("task list shows short dates with full hover timestamps", () => {
  const source = readSource("src/features/research/research-task-list.tsx");

  assert.match(source, /function getLocalDateParts/);
  assert.match(source, /function formatDay/);
  assert.match(source, /function formatDateTime/);
  assert.match(source, /\[year, month, day\]\.join\("-"\)/);
  assert.match(source, /\$\{year\}-\$\{month\}-\$\{day\} \$\{hour\}:\$\{minute\}:\$\{second\}/);
  assert.match(source, /title=\{fullDate\}/);
  assert.match(source, /<TaskCreatedAt value=\{task\.created_at\}/);
});

test("global navigation is streamlined around my research", () => {
  const data = readSource("src/features/product-skeleton/data.ts");
  const home = readSource("src/app/page.tsx");
  const history = readSource("src/app/history/page.tsx");
  const opportunities = readSource("src/app/opportunities/page.tsx");
  const reports = readSource("src/app/reports/page.tsx");

  assert.match(data, /label: "我的研究"/);
  assert.doesNotMatch(data, /label: "研究历史"/);
  assert.doesNotMatch(data, /label: "商机推荐"/);
  assert.doesNotMatch(data, /label: "最终报告"/);
  assert.match(home, /title="我的研究"/);
  assert.match(history, /redirect\("\/research\/tasks\?status=completed"\)/);
  assert.match(opportunities, /active="tasks"/);
  assert.match(reports, /active="tasks"/);
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

test("language menu keeps bilingual UI toggle with Chinese default", () => {
  const shell = readSource("src/features/product-skeleton/components.tsx");
  const provider = readSource("src/features/i18n/language-provider.tsx");

  assert.match(shell, /DropdownMenuSub/);
  assert.match(shell, /setLanguage\("zh"\)/);
  assert.match(shell, /setLanguage\("en"\)/);
  assert.match(provider, /defaultLanguage: Language = "zh"/);
  assert.match(provider, /My research/);
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

test("task context tabs stay mounted during task surface loading states", () => {
  const opportunities = readSource("src/features/opportunities/opportunity-list.tsx");
  const report = readSource("src/features/reports/report-summary.tsx");
  const progress = readSource("src/features/research/research-progress.tsx");

  assert.match(opportunities, /const taskNavigation = \(/);
  assert.match(opportunities, /if \(isLoading\)[\s\S]*\{taskNavigation\}/);
  assert.match(report, /const taskNavigation = \(/);
  assert.match(report, /if \(isLoading\)[\s\S]*\{taskNavigation\}/);
  assert.match(progress, /if \(isLoading\)[\s\S]*active="progress"/);
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

  assert.match(api, /index_rag_evidence/);
  assert.match(progress, /index_rag_evidence/);
  assert.match(progress, /整理公开来源证据/);
  assert.match(progress, /待验证证据/);
  assert.match(taskList, /整理公开来源证据/);
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

test("report sharing keeps online share actions and read-only public report", () => {
  const report = readSource("src/features/reports/report-summary.tsx");
  const sharing = readSource("src/features/reports/report-sharing.tsx");
  const sharedReport = readSource("src/features/reports/shared-report.tsx");
  const sharedRoute = readSource("src/app/share/reports/[token]/page.tsx");
  const api = readSource("src/features/research/api.ts");

  assert.match(report, /ReportSharePanel/);
  assert.match(sharing, /生成分享链接/);
  assert.match(sharing, /复制链接/);
  assert.match(sharing, /打开分享页/);
  assert.match(sharing, /撤销分享/);
  assert.match(sharing, /分享功能暂不可用，不影响继续阅读报告/);
  assert.match(api, /createReportShare/);
  assert.match(api, /fetchPublicReportShare/);
  assert.match(sharedRoute, /fetchPublicReportShare/);
  assert.match(sharedRoute, /分享报告不可访问/);
  assert.match(sharedReport, /只读分享报告/);
  assert.match(sharedReport, /任务摘要/);
  assert.match(sharedReport, /推荐排序/);
  assert.match(sharedReport, /需求洞察/);
  assert.match(sharedReport, /货源候选/);
  assert.match(sharedReport, /竞品参考/);
  assert.match(sharedReport, /验证预算/);
  assert.match(sharedReport, /风险复核/);
  assert.match(sharedReport, /行动计划/);
  assert.match(sharedReport, /任务级来源线索/);
  assert.match(sharedReport, /谨慎边界/);
  assert.doesNotMatch(sharedReport, /重新运行/);
  assert.doesNotMatch(sharedReport, /LangSmith/);
  assert.doesNotMatch(sharedReport, /删除任务/);
});

test("research readiness stays internal and visible only in app surfaces", () => {
  const progress = readSource("src/features/research/research-progress.tsx");
  const taskList = readSource("src/features/research/research-task-list.tsx");
  const sharedReport = readSource("src/features/reports/shared-report.tsx");
  const sharedRoute = readSource("src/app/share/reports/[token]/page.tsx");
  const api = readSource("src/features/research/api.ts");

  assert.match(api, /ResearchQualityReadinessRun/);
  assert.match(api, /createResearchQualityReadinessRun/);
  assert.match(api, /fetchLatestResearchQualityReadinessRun/);
  assert.match(progress, /演示就绪检查/);
  assert.match(progress, /运行检查/);
  assert.match(progress, /RAG 检索评测已关联/);
  assert.match(progress, /不作为用户侧商机评分/);
  assert.doesNotMatch(taskList, /fetchLatestResearchQualityReadinessRun/);
  assert.doesNotMatch(taskList, /演示状态/);
  assert.doesNotMatch(taskList, /可演示/);
  assert.doesNotMatch(taskList, /需复查/);
  assert.doesNotMatch(sharedReport, /演示就绪检查/);
  assert.doesNotMatch(sharedReport, /RAG 检索评测已关联/);
  assert.doesNotMatch(sharedRoute, /fetchLatestResearchQualityReadinessRun/);
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
