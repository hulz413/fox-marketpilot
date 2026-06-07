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
  const tasksPage = readSource("src/app/research/tasks/page.tsx");
  const shell = readSource("src/features/product-skeleton/components.tsx");

  assert.match(source, /查看研究结果/);
  assert.match(source, /查看进度/);
  assert.match(source, /开始研究/);
  assert.match(source, /重新运行/);
  assert.match(source, /更多操作/);
  assert.match(source, /taskStatusFilters/);
  assert.match(source, /TaskTableColumnGroup/);
  assert.match(source, /className="table-fixed"/);
  assert.match(source, /ClipboardList/);
  assert.match(source, /sm:grid-cols-\[minmax\(0,1fr\)_auto\] sm:grid-rows-\[auto\] sm:items-center/);
  assert.match(source, /grid-cols-\[auto_minmax\(0,1fr\)\] grid-rows-\[auto\] items-center/);
  assert.match(source, /gap-4 px-6 pt-6 pb-0/);
  assert.doesNotMatch(source, /border-b px-5 pt-4 pb-3/);
  assert.match(source, /<div className="grid min-w-0 gap-1">/);
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
  assert.doesNotMatch(tasksPage, /TaskStateCards/);
  assert.doesNotMatch(shell, /function TaskStateCards/);
  assert.match(shell, /StatusBadgeWithTooltip/);
  assert.match(shell, /TooltipContent/);
  assert.match(shell, /任务正在后台生成基础推荐，可进入进度页查看当前阶段。/);
  assert.match(shell, /生成过程失败，可查看失败原因并重新运行。/);
  assert.match(shell, /研究已完成，可打开研究结果查看商机推荐、基础报告和来源线索。/);
});

test("task list shows short dates with full hover timestamps", () => {
  const source = readSource("src/features/research/research-task-list.tsx");
  const datetime = readSource("src/lib/datetime.ts");

  assert.match(source, /formatDate, formatDateTime/);
  assert.match(datetime, /export function formatDate/);
  assert.match(datetime, /export function formatDateTime/);
  assert.match(datetime, /\$\{year\}-\$\{month\}-\$\{day\}/);
  assert.match(datetime, /\$\{year\}-\$\{month\}-\$\{day\} \$\{hour\}:\$\{minute\}:\$\{second\}/);
  assert.match(source, /title=\{fullDate\}/);
  assert.match(source, /<TaskCreatedAt value=\{task\.created_at\}/);
});

test("research timestamps use yyyy-mm-dd and compact durations", () => {
  const progress = readSource("src/features/research/research-progress.tsx");
  const sharing = readSource("src/features/reports/report-sharing.tsx");
  const sharedReport = readSource("src/features/reports/shared-report.tsx");

  assert.match(progress, /formatDateTime/);
  assert.match(progress, /\$\{durationMs\}ms/);
  assert.match(progress, /\$\{\(durationMs \/ 1000\)\.toFixed\(1\)\}s/);
  assert.doesNotMatch(progress, /\$\{durationMs\} ms/);
  assert.doesNotMatch(progress, /toFixed\(1\)\} s/);
  assert.match(sharing, /formatDateTime\(latestShare\.created_at\)/);
  assert.match(sharedReport, /formatDateTime\(snapshot\.shared_at\)/);
});

test("global navigation is streamlined around my research", () => {
  const data = readSource("src/features/product-skeleton/data.ts");
  const home = readSource("src/app/page.tsx");
  const tasks = readSource("src/app/research/tasks/page.tsx");
  const history = readSource("src/app/history/page.tsx");
  const opportunities = readSource("src/app/opportunities/page.tsx");
  const reports = readSource("src/app/reports/page.tsx");

  assert.match(data, /label: "我的研究"/);
  assert.doesNotMatch(data, /label: "研究历史"/);
  assert.doesNotMatch(data, /label: "商机推荐"/);
  assert.doesNotMatch(data, /label: "最终报告"/);
  assert.match(home, /ResearchIntakeWorkspace/);
  assert.match(tasks, /title="我的研究"/);
  assert.match(tasks, /Sparkles data-icon="inline-end"/);
  assert.doesNotMatch(tasks, /ArrowRight/);
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
  const legacyNewPage = readSource("src/app/research/new/page.tsx");
  const legacyChatPage = readSource("src/app/research/chat/page.tsx");
  const home = readSource("src/app/page.tsx");
  const workspace = readSource(
    "src/features/research/research-intake-workspace.tsx",
  );
  const tasks = readSource("src/app/research/tasks/page.tsx");
  const shell = readSource("src/features/product-skeleton/components.tsx");
  const navData = readSource("src/features/product-skeleton/data.ts");

  assert.match(source, /sampleToFormValues/);
  assert.match(source, /draftToFormValues/);
  assert.match(source, /initialDraftVersion/);
  assert.match(source, /type ResearchIntakeDraft/);
  assert.match(source, /fillWithSample/);
  assert.match(source, /DemoResearchSamples onFill/);
  assert.match(source, /createAndStartResearchTask/);
  assert.match(source, /直接启动一个完整演示任务/);
  assert.match(legacyNewPage, /redirect\("\/"\)/);
  assert.match(legacyChatPage, /redirect\("\/"\)/);
  assert.match(home, /ResearchIntakeWorkspace/);
  assert.match(workspace, /useState<ResearchIntakeMode>\("chat"\)/);
  assert.match(workspace, /formDraft/);
  assert.match(workspace, /editDraftInForm/);
  assert.match(workspace, /setMode\(isChatMode \? "form" : "chat"\)/);
  assert.match(workspace, /聊天模式/);
  assert.match(workspace, /表单模式/);
  assert.match(workspace, /breadcrumbAction=/);
  assert.match(workspace, /contentScroll=\{false\}/);
  assert.match(workspace, /className="h-full min-h-0"/);
  assert.match(workspace, /onEditDraft=\{editDraftInForm\}/);
  assert.match(workspace, /initialDraft=\{formDraft\?\.draft\}/);
  assert.match(workspace, /ClipboardList data-icon="inline-end"/);
  assert.match(workspace, /FilePenLine data-icon="inline-end"/);
  assert.match(workspace, /MessageCircle data-icon="inline-end"/);
  assert.match(tasks, /ResearchTaskList/);
  assert.doesNotMatch(tasks, /@\/app\/page/);
  assert.match(navData, /href: "\/"/);
  assert.match(shell, /aria-label=\{t\("返回主页"\)\}/);
  assert.match(shell, /href="\/"/);
  assert.match(shell, /breadcrumbAction\?: ReactNode/);
  assert.match(shell, /contentScroll\?: boolean/);
  assert.match(shell, /contentScroll \? "lg:overflow-y-auto" : "lg:overflow-hidden"/);
  assert.match(shell, /min-h-9 flex-col gap-3 sm:flex-row/);
});

test("research intake chat creates drafts before starting tasks", () => {
  const workspace = readSource(
    "src/features/research/research-intake-workspace.tsx",
  );
  const chat = readSource("src/features/research/research-intake-chat.tsx");
  const api = readSource("src/features/research/api.ts");
  const navData = readSource("src/features/product-skeleton/data.ts");

  assert.match(workspace, /ResearchIntakeChat/);
  assert.match(workspace, /NewResearchForm/);
  assert.match(workspace, /hidden=\{!isChatMode\}/);
  assert.match(workspace, /hidden=\{isChatMode\}/);
  assert.match(chat, /聊天对齐需求/);
  assert.match(chat, /grid-cols-\[auto_minmax\(0,1fr\)\] grid-rows-\[auto\]/);
  assert.match(chat, /size-10 shrink-0/);
  assert.match(chat, /研究草稿/);
  assert.match(chat, /ReadinessBadges conversation=\{conversation\}/);
  assert.doesNotMatch(chat, /点击「更新需求」后会显示草稿完整度/);
  assert.match(chat, /const hasSummary =/);
  assert.match(chat, /缺失条件/);
  assert.match(chat, /默认假设/);
  assert.match(chat, /确认并启动研究/);
  assert.match(chat, /createResearchIntakeConversation/);
  assert.match(chat, /sendResearchIntakeMessage/);
  assert.match(chat, /updateResearchIntakeRequirements/);
  assert.match(chat, /更新需求/);
  assert.match(chat, /更新中/);
  assert.match(chat, /商机顾问会追问补充信息/);
  assert.match(chat, /justify-start whitespace-normal px-4 py-1\.5 text-left leading-6/);
  assert.match(chat, /fetchResearchIntakeConversation/);
  assert.match(chat, /INTAKE_CONVERSATION_STORAGE_KEY/);
  assert.match(chat, /sessionStorage/);
  assert.match(chat, /forgetActiveConversation/);
  assert.match(chat, /正在恢复上次聊天/);
  assert.match(chat, /带入表单编辑/);
  assert.match(chat, /onEditDraft/);
  assert.match(chat, /ChatAvatar/);
  assert.match(chat, /ChatThinkingMessage/);
  assert.match(chat, /suggested_replies/);
  assert.doesNotMatch(chat, /suggestedRepliesForAssistant/);
  assert.match(chat, /latestAssistantMessageUuid/);
  assert.match(chat, /可选回复/);
  assert.match(chat, /onSuggestionSelect=\{submitMessage\}/);
  assert.match(chat, /size="xs"/);
  assert.match(chat, /rounded-full bg-secondary\/60 font-normal hover:bg-secondary/);
  assert.match(chat, /pendingMessage/);
  assert.match(chat, /思考中/);
  assert.match(chat, /messagesViewportRef/);
  assert.doesNotMatch(chat, /h-\[520px\]/);
  assert.match(chat, /lg:h-full/);
  assert.match(chat, /overflow-y-auto/);
  assert.match(chat, /\[scrollbar-width:none\]/);
  assert.match(chat, /flex min-h-0 flex-1 flex-col gap-4/);
  assert.match(chat, /min-h-0 min-w-0 self-stretch/);
  assert.match(chat, /h-full min-h-0 gap-4 rounded-lg/);
  assert.match(chat, /grid min-h-0 flex-1 gap-4 overflow-y-auto/);
  assert.match(chat, /UserRound/);
  assert.match(chat, /Compass/);
  assert.match(chat, /max-w-\[min\(560px,72%\)\]/);
  assert.match(chat, /sr-only/);
  assert.match(chat, /confirmResearchIntakeConversation/);
  assert.match(chat, /handleResetConversation/);
  assert.match(chat, /setConversation\(null\)/);
  assert.match(chat, /messageMutation\.reset\(\)/);
  assert.match(chat, /updateMutation\.reset\(\)/);
  assert.match(chat, /confirmMutation\.reset\(\)/);
  assert.match(chat, /重置/);
  assert.match(chat, /ml-auto bg-secondary\/60 hover:bg-secondary/);
  assert.match(chat, /handleMessageKeyDown/);
  assert.match(chat, /event\.nativeEvent\.isComposing/);
  assert.match(chat, /event\.shiftKey/);
  assert.match(chat, /LoaderCircle/);
  assert.match(chat, /animate-spin/);
  assert.doesNotMatch(chat, /发送中/);
  assert.doesNotMatch(chat, /正在整理需求草稿/);
  assert.match(chat, /router\.push\(`\/research\/tasks\/\$\{result\.research_task_uuid\}`\)/);
  assert.match(api, /ResearchIntakeConversation/);
  assert.match(api, /suggested_replies: string\[\]/);
  assert.match(api, /\/api\/v1\/research-intake-conversations/);
  assert.match(api, /\/analysis/);
  assert.match(api, /body: JSON\.stringify\(\{ content \}\)/);
  assert.doesNotMatch(navData, /research\/chat/);
  assert.doesNotMatch(chat, /href="\/research\/new"/);
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
  assert.match(shell, /fetchResearchTask/);
  assert.match(shell, /TaskContextSummaryCard/);
  assert.match(shell, /TaskContextSummaryCard[\s\S]*<nav/);
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

test("opportunity list title aligns with progress card header", () => {
  const opportunities = readSource("src/features/opportunities/opportunity-list.tsx");
  const progress = readSource("src/features/research/research-progress.tsx");

  assert.match(opportunities, /px-6 pt-6 pb-0/);
  assert.match(opportunities, /grid min-w-0 gap-2/);
  assert.doesNotMatch(opportunities, /border-b px-5 py-4/);
  assert.match(progress, /<CardTitle>阶段时间线<\/CardTitle>/);
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
  assert.match(progress, /未开始的阶段在前/);
  assert.match(progress, /sortTime/);
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

test("research readiness stays internal and hidden from progress/share surfaces", () => {
  const progress = readSource("src/features/research/research-progress.tsx");
  const taskList = readSource("src/features/research/research-task-list.tsx");
  const sharedReport = readSource("src/features/reports/shared-report.tsx");
  const sharedRoute = readSource("src/app/share/reports/[token]/page.tsx");
  const shell = readSource("src/features/product-skeleton/components.tsx");
  const navData = readSource("src/features/product-skeleton/data.ts");
  const internalRoute = readSource("src/app/internal/quality/page.tsx");
  const internalPanel = readSource(
    "src/features/internal-quality/internal-quality-panel.tsx",
  );
  const api = readSource("src/features/research/api.ts");

  assert.match(api, /ResearchQualityReadinessRun/);
  assert.match(api, /createResearchQualityReadinessRun/);
  assert.match(api, /fetchLatestResearchQualityReadinessRun/);
  assert.match(api, /GenerationEvaluationRun/);
  assert.match(api, /createGenerationEvaluationRun/);
  assert.match(api, /fetchLatestGenerationEvaluationRun/);
  assert.match(internalRoute, /InternalQualityPanel/);
  assert.match(internalPanel, /内部质量复查/);
  assert.match(internalPanel, /createResearchQualityReadinessRun/);
  assert.match(internalPanel, /fetchLatestResearchQualityReadinessRun/);
  assert.match(internalPanel, /createGenerationEvaluationRun/);
  assert.match(internalPanel, /fetchLatestGenerationEvaluationRun/);
  assert.match(internalPanel, /RAG 质量摘要/);
  assert.match(internalPanel, /不代表商机、需求、供给、利润或市场机会已经被证明/);
  assert.match(shell, /href="\/internal\/quality"/);
  assert.match(shell, /内部质量复查/);
  assert.doesNotMatch(navData, /internal\/quality/);
  assert.doesNotMatch(progress, /查看研究结果/);
  assert.doesNotMatch(progress, /fetchLatestResearchQualityReadinessRun/);
  assert.doesNotMatch(progress, /fetchLatestGenerationEvaluationRun/);
  assert.doesNotMatch(progress, /createGenerationEvaluationRun/);
  assert.doesNotMatch(progress, /演示就绪检查/);
  assert.doesNotMatch(progress, /运行检查/);
  assert.doesNotMatch(progress, /RAG 检索评测已关联/);
  assert.doesNotMatch(progress, /不作为用户侧商机评分/);
  assert.doesNotMatch(progress, /运行详情/);
  assert.doesNotMatch(progress, /运行 ID/);
  assert.doesNotMatch(progress, /Trace/);
  assert.doesNotMatch(progress, /当前阶段：/);
  assert.doesNotMatch(taskList, /fetchLatestResearchQualityReadinessRun/);
  assert.doesNotMatch(taskList, /fetchLatestGenerationEvaluationRun/);
  assert.doesNotMatch(taskList, /演示状态/);
  assert.doesNotMatch(taskList, /可演示/);
  assert.doesNotMatch(taskList, /需复查/);
  assert.doesNotMatch(sharedReport, /演示就绪检查/);
  assert.doesNotMatch(sharedReport, /生成质量评测/);
  assert.doesNotMatch(sharedReport, /RAG 检索评测已关联/);
  assert.doesNotMatch(sharedRoute, /fetchLatestResearchQualityReadinessRun/);
  assert.doesNotMatch(sharedRoute, /fetchLatestGenerationEvaluationRun/);
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
