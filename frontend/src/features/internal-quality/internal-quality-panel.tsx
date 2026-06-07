"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ClipboardCheck,
  Database,
  ListChecks,
  Play,
  RefreshCcw,
  ShieldAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";

import {
  createGenerationEvaluationRun,
  createResearchQualityReadinessRun,
  fetchLatestGenerationEvaluationRun,
  fetchLatestResearchQualityReadinessRun,
  fetchResearchTasks,
  type GenerationEvaluationRun,
  type GenerationEvaluationOverallStatus,
  type GenerationEvaluationRunStatus,
  type ReadinessCheckStatus,
  type ReadinessOverallStatus,
  type ReadinessRunStatus,
  type ResearchQualityReadinessCheck,
  type ResearchQualityReadinessRun,
  type ResearchTask,
  type ResearchTaskStage,
  type ResearchTaskStatus,
} from "@/features/research/api";

const taskStatusLabels: Record<ResearchTaskStatus, string> = {
  created: "待启动",
  queued: "运行中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

const taskStageLabels: Record<ResearchTaskStage, string> = {
  intake: "需求已提交",
  queued: "等待后台执行",
  normalize_intake: "整理研究需求",
  generate_opportunities: "生成基础推荐",
  validate_results: "校验推荐结果",
  persist_results: "保存研究结果",
  collect_research_sources: "收集公开来源线索",
  index_rag_evidence: "整理公开来源证据",
  generate_demand_insights: "生成需求洞察",
  generate_supply_candidates: "生成货源候选",
  generate_competitor_references: "生成竞品参考",
  estimate_validation_budgets: "估算验证预算",
  review_opportunity_risks: "复核商机风险",
  create_action_plans: "生成行动计划",
  completed: "研究已完成",
  failed: "生成失败",
};

const readinessOverallLabels: Record<ReadinessOverallStatus, string> = {
  ready: "可演示",
  warning: "需复查",
  failed: "检查失败",
};

const readinessRunLabels: Record<ReadinessRunStatus, string> = {
  running: "运行中",
  completed: "已完成",
  partial: "部分完成",
  failed: "失败",
};

const readinessCheckLabels: Record<ReadinessCheckStatus, string> = {
  pass: "通过",
  warning: "需复查",
  failed: "失败",
  skipped: "跳过",
};

const generationOverallLabels: Record<GenerationEvaluationOverallStatus, string> = {
  passed: "通过",
  warning: "需复查",
  failed: "失败",
};

const generationRunLabels: Record<GenerationEvaluationRunStatus, string> = {
  running: "运行中",
  completed: "已完成",
  partial: "部分完成",
  failed: "失败",
};

const metricLabels: Record<string, string> = {
  active_chunk_count: "Active chunks",
  case_completed_count: "完成 case",
  case_failed_count: "失败 case",
  case_skipped_count: "跳过 case",
  case_total: "Case 总数",
  completed_stage_count: "完成阶段",
  embedded_chunk_count: "已嵌入 chunks",
  embedding_dimensions: "Embedding 维度",
  embedding_models: "Embedding 模型",
  evaluation_run_uuid: "评测运行 UUID",
  "hit_rate@k": "hit_rate@k",
  "mrr@k": "mrr@k",
  "ndcg@k": "ndcg@k",
  "precision@k": "precision@k",
  "recall@k": "recall@k",
  rag_index_status: "RAG 索引状态",
  source_count: "来源数",
  status: "运行状态",
};

const ragMetricOrder = [
  "source_count",
  "active_chunk_count",
  "embedded_chunk_count",
  "embedding_models",
  "embedding_dimensions",
  "rag_index_status",
  "evaluation_run_uuid",
  "status",
  "case_total",
  "case_completed_count",
  "case_failed_count",
  "case_skipped_count",
  "hit_rate@k",
  "recall@k",
  "precision@k",
  "mrr@k",
  "ndcg@k",
];

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

function statusBadgeVariant(status: string): BadgeVariant {
  if (status === "failed") {
    return "destructive";
  }

  if (status === "warning" || status === "partial" || status === "skipped") {
    return "secondary";
  }

  if (status === "ready" || status === "passed" || status === "pass") {
    return "default";
  }

  return "outline";
}

function formatOptionalDateTime(value: string | null) {
  return value ? formatDateTime(value) : "未完成";
}

function formatError(error: unknown) {
  return error instanceof Error && error.message
    ? error.message
    : "请求失败，请稍后重试。";
}

function formatMetricValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "未记录";
  }

  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return "未记录";
    }

    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }

  if (typeof value === "string") {
    return value;
  }

  if (Array.isArray(value)) {
    return value.length ? value.map(formatMetricValue).join("、") : "无";
  }

  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    return entries.length
      ? entries
          .map(([key, item]) => `${key}: ${formatMetricValue(item)}`)
          .join("；")
      : "无";
  }

  return String(value);
}

function metricRows(
  metrics: Record<string, unknown>,
  keys?: string[],
): Array<{ key: string; label: string; value: string }> {
  const entries = keys
    ? keys
        .filter((key) => Object.prototype.hasOwnProperty.call(metrics, key))
        .map((key) => [key, metrics[key]] as const)
    : Object.entries(metrics);

  return entries.map(([key, value]) => ({
    key,
    label: metricLabels[key] ?? key,
    value: formatMetricValue(value),
  }));
}

function hasRows(metrics: Record<string, unknown>, keys?: string[]) {
  return metricRows(metrics, keys).length > 0;
}

export function InternalQualityPanel() {
  const queryClient = useQueryClient();
  const [selectedTaskUuid, setSelectedTaskUuid] = useState<string | null>(null);
  const tasksQuery = useQuery({
    queryKey: ["internal-quality", "research-tasks"],
    queryFn: fetchResearchTasks,
  });

  const activeTasks = useMemo(
    () => (tasksQuery.data ?? []).filter((task) => !task.deleted_at),
    [tasksQuery.data],
  );
  const completedTasks = useMemo(
    () => activeTasks.filter((task) => task.status === "completed"),
    [activeTasks],
  );

  const effectiveSelectedTaskUuid =
    selectedTaskUuid && activeTasks.some((task) => task.uuid === selectedTaskUuid)
      ? selectedTaskUuid
      : completedTasks[0]?.uuid ?? activeTasks[0]?.uuid ?? null;
  const selectedTask =
    activeTasks.find((task) => task.uuid === effectiveSelectedTaskUuid) ?? null;
  const canRunQuality = selectedTask?.status === "completed";
  const readinessQuery = useQuery({
    queryKey: ["internal-quality", "readiness", selectedTask?.uuid],
    queryFn: () => fetchLatestResearchQualityReadinessRun(selectedTask!.uuid),
    enabled: canRunQuality,
  });
  const generationQuery = useQuery({
    queryKey: ["internal-quality", "generation-evaluation", selectedTask?.uuid],
    queryFn: () => fetchLatestGenerationEvaluationRun(selectedTask!.uuid),
    enabled: canRunQuality,
  });

  const readinessMutation = useMutation({
    mutationFn: createResearchQualityReadinessRun,
    onSuccess: async (_run, taskUuid) => {
      await queryClient.invalidateQueries({
        queryKey: ["internal-quality", "readiness", taskUuid],
      });
    },
  });
  const generationMutation = useMutation({
    mutationFn: createGenerationEvaluationRun,
    onSuccess: async (_run, taskUuid) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["internal-quality", "generation-evaluation", taskUuid],
        }),
        queryClient.invalidateQueries({
          queryKey: ["internal-quality", "readiness", taskUuid],
        }),
      ]);
    },
  });

  const runReadiness = () => {
    if (selectedTask?.uuid) {
      readinessMutation.mutate(selectedTask.uuid);
    }
  };
  const runGenerationEvaluation = () => {
    if (selectedTask?.uuid) {
      generationMutation.mutate(selectedTask.uuid);
    }
  };

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <Button asChild variant="ghost" size="sm" className="mb-3 w-fit">
              <Link href="/research/tasks">
                <ArrowLeft data-icon="inline-start" />
                我的研究
              </Link>
            </Button>
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <ShieldAlert className="size-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="text-sm text-muted-foreground">MarketPilot internal</p>
                <h1 className="text-2xl font-semibold tracking-normal sm:text-3xl">
                  内部质量复查
                </h1>
              </div>
            </div>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
              内部复查信号不代表商机、需求、供给、利润或市场机会已经被证明。
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => void tasksQuery.refetch()}
            disabled={tasksQuery.isFetching}
          >
            <RefreshCcw data-icon="inline-start" />
            刷新任务
          </Button>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-5 lg:grid-cols-[360px_minmax(0,1fr)]">
        <TaskSelectorCard
          error={tasksQuery.error}
          isLoading={tasksQuery.isLoading}
          onRefresh={() => void tasksQuery.refetch()}
          onSelect={setSelectedTaskUuid}
          selectedTaskUuid={effectiveSelectedTaskUuid}
          tasks={activeTasks}
        />
        <div className="grid min-w-0 gap-5">
          <SelectedTaskCard
            generationError={generationMutation.error}
            isGenerating={generationMutation.isPending}
            isRunningReadiness={readinessMutation.isPending}
            onRunGenerationEvaluation={runGenerationEvaluation}
            onRunReadiness={runReadiness}
            readinessError={readinessMutation.error}
            task={selectedTask}
          />
          {canRunQuality ? (
            <>
              <ReadinessSummaryCard
                error={readinessQuery.error}
                isLoading={readinessQuery.isLoading}
                onRetry={() => void readinessQuery.refetch()}
                readiness={readinessQuery.data ?? null}
              />
              <GenerationEvaluationSummaryCard
                error={generationQuery.error}
                generationRun={generationQuery.data ?? null}
                isLoading={generationQuery.isLoading}
                onRetry={() => void generationQuery.refetch()}
              />
              <RagSummaryCard readiness={readinessQuery.data ?? null} />
            </>
          ) : (
            <UnavailableTaskCard task={selectedTask} />
          )}
        </div>
      </div>
    </main>
  );
}

function TaskSelectorCard({
  error,
  isLoading,
  onRefresh,
  onSelect,
  selectedTaskUuid,
  tasks,
}: {
  error: unknown;
  isLoading: boolean;
  onRefresh: () => void;
  onSelect: (taskUuid: string) => void;
  selectedTaskUuid: string | null;
  tasks: ResearchTask[];
}) {
  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>研究任务</CardTitle>
          <CardDescription>正在读取任务列表。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-44 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="rounded-lg border-destructive/30">
        <CardHeader>
          <CardTitle>任务读取失败</CardTitle>
          <CardDescription>{formatError(error)}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" variant="outline" onClick={onRefresh}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!tasks.length) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>研究任务</CardTitle>
          <CardDescription>暂无可复查任务。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm leading-6 text-muted-foreground">
          <p>先完成一次真实研究任务后，再运行内部质量复查。</p>
          <Button asChild variant="outline" className="w-fit">
            <Link href="/">新建研究</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle>研究任务</CardTitle>
        <CardDescription>选择一条任务查看内部质量状态。</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="grid gap-2 md:hidden">
          {tasks.map((task) => (
            <TaskSelectButton
              key={task.uuid}
              isSelected={task.uuid === selectedTaskUuid}
              onSelect={() => onSelect(task.uuid)}
              task={task}
            />
          ))}
        </div>
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>任务</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.uuid}>
                  <TableCell className="max-w-[180px]">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{task.title}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {task.uuid}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <StatusBadge
                      label={taskStatusLabels[task.status]}
                      status={task.status}
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      type="button"
                      variant={task.uuid === selectedTaskUuid ? "secondary" : "ghost"}
                      size="sm"
                      onClick={() => onSelect(task.uuid)}
                    >
                      查看
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function TaskSelectButton({
  isSelected,
  onSelect,
  task,
}: {
  isSelected: boolean;
  onSelect: () => void;
  task: ResearchTask;
}) {
  return (
    <button
      type="button"
      className={cn(
        "grid min-h-24 gap-3 rounded-lg border bg-card p-3 text-left transition-colors hover:bg-muted/50",
        isSelected ? "border-primary bg-primary/5" : "",
      )}
      onClick={onSelect}
    >
      <div className="flex min-w-0 items-start justify-between gap-2">
        <p className="min-w-0 truncate font-medium">{task.title}</p>
        <StatusBadge label={taskStatusLabels[task.status]} status={task.status} />
      </div>
      <p className="truncate text-xs text-muted-foreground">{task.uuid}</p>
      <p className="text-xs text-muted-foreground">
        {taskStageLabels[task.current_stage]} · {formatDateTime(task.updated_at)}
      </p>
    </button>
  );
}

function SelectedTaskCard({
  generationError,
  isGenerating,
  isRunningReadiness,
  onRunGenerationEvaluation,
  onRunReadiness,
  readinessError,
  task,
}: {
  generationError: unknown;
  isGenerating: boolean;
  isRunningReadiness: boolean;
  onRunGenerationEvaluation: () => void;
  onRunReadiness: () => void;
  readinessError: unknown;
  task: ResearchTask | null;
}) {
  if (!task) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>质量详情</CardTitle>
          <CardDescription>暂无选中的研究任务。</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const isCompleted = task.status === "completed";

  return (
    <Card className="rounded-lg">
      <CardHeader className="gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={taskStatusLabels[task.status]} status={task.status} />
          <Badge variant="outline">{taskStageLabels[task.current_stage]}</Badge>
          <Badge variant="outline">更新于 {formatDateTime(task.updated_at)}</Badge>
        </div>
        <div>
          <CardTitle>{task.title}</CardTitle>
          <CardDescription className="mt-2 leading-6">{task.brief}</CardDescription>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
          <p className="truncate">任务 UUID：{task.uuid}</p>
          <p className="truncate">研究 run：{task.run_id ?? "未记录"}</p>
          <p>创建时间：{formatDateTime(task.created_at)}</p>
          <p>更新时间：{formatDateTime(task.updated_at)}</p>
        </div>
        <Separator />
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            onClick={onRunReadiness}
            disabled={!isCompleted || isRunningReadiness}
          >
            {isRunningReadiness ? (
              <RefreshCcw data-icon="inline-start" />
            ) : (
              <Play data-icon="inline-start" />
            )}
            运行质量就绪检查
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={onRunGenerationEvaluation}
            disabled={!isCompleted || isGenerating}
          >
            {isGenerating ? (
              <RefreshCcw data-icon="inline-start" />
            ) : (
              <Play data-icon="inline-start" />
            )}
            运行生成质量评测
          </Button>
        </div>
        {readinessError ? <ErrorLine message={formatError(readinessError)} /> : null}
        {generationError ? <ErrorLine message={formatError(generationError)} /> : null}
      </CardContent>
    </Card>
  );
}

function UnavailableTaskCard({ task }: { task: ResearchTask | null }) {
  return (
    <Card className="rounded-lg">
      <CardHeader>
        <div className="flex items-center gap-3">
          <AlertTriangle className="size-5 text-muted-foreground" aria-hidden="true" />
          <CardTitle>当前任务不可运行质量复查</CardTitle>
        </div>
        <CardDescription>
          {task
            ? `当前状态为「${taskStatusLabels[task.status]}」，完成后再运行内部复查。`
            : "请选择一条研究任务。"}
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

function ReadinessSummaryCard({
  error,
  isLoading,
  onRetry,
  readiness,
}: {
  error: unknown;
  isLoading: boolean;
  onRetry: () => void;
  readiness: ResearchQualityReadinessRun | null;
}) {
  return (
    <Card className="rounded-lg">
      <CardHeader>
        <div className="flex items-center gap-3">
          <ClipboardCheck className="size-5 text-muted-foreground" aria-hidden="true" />
          <div>
            <CardTitle>质量就绪检查</CardTitle>
            <CardDescription>阶段完整性、增强分析、RAG 和分享快照摘要。</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        <AsyncState
          emptyTitle="尚未运行质量就绪检查"
          error={error}
          isEmpty={!readiness}
          isLoading={isLoading}
          loadingTitle="正在读取质量就绪检查。"
          onRetry={onRetry}
        >
          {readiness ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge
                  label={readinessOverallLabels[readiness.overall_status]}
                  status={readiness.overall_status}
                />
                <StatusBadge
                  label={readinessRunLabels[readiness.status]}
                  status={readiness.status}
                />
                {readiness.stale ? (
                  <Badge variant="secondary">已过期</Badge>
                ) : (
                  <Badge variant="outline">当前 run</Badge>
                )}
              </div>
              <p className="text-sm leading-6 text-muted-foreground">
                {readiness.summary}
              </p>
              <MetricGrid
                rows={[
                  { key: "uuid", label: "Readiness UUID", value: readiness.uuid },
                  {
                    key: "research_run_id",
                    label: "研究 run",
                    value: readiness.research_run_id ?? "未记录",
                  },
                  {
                    key: "completed_at",
                    label: "完成时间",
                    value: formatOptionalDateTime(readiness.completed_at),
                  },
                  {
                    key: "rag_evaluation_run_uuid",
                    label: "RAG 评测 UUID",
                    value: readiness.rag_evaluation_run_uuid ?? "未关联",
                  },
                  {
                    key: "generation_evaluation_run_uuid",
                    label: "生成评测 UUID",
                    value: readiness.generation_evaluation_run_uuid ?? "未关联",
                  },
                ]}
              />
              {readiness.error_summary ? (
                <ErrorLine message={readiness.error_summary} />
              ) : null}
              <CheckList checks={readiness.checks} />
            </>
          ) : null}
        </AsyncState>
      </CardContent>
    </Card>
  );
}

function GenerationEvaluationSummaryCard({
  error,
  generationRun,
  isLoading,
  onRetry,
}: {
  error: unknown;
  generationRun: GenerationEvaluationRun | null;
  isLoading: boolean;
  onRetry: () => void;
}) {
  return (
    <Card className="rounded-lg">
      <CardHeader>
        <div className="flex items-center gap-3">
          <ListChecks className="size-5 text-muted-foreground" aria-hidden="true" />
          <div>
            <CardTitle>生成质量评测</CardTitle>
            <CardDescription>约束、结构、一致性、风险、行动和谨慎边界。</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        <AsyncState
          emptyTitle="尚未运行生成质量评测"
          error={error}
          isEmpty={!generationRun}
          isLoading={isLoading}
          loadingTitle="正在读取生成质量评测。"
          onRetry={onRetry}
        >
          {generationRun ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge
                  label={generationOverallLabels[generationRun.overall_status]}
                  status={generationRun.overall_status}
                />
                <StatusBadge
                  label={generationRunLabels[generationRun.status]}
                  status={generationRun.status}
                />
                {generationRun.stale ? (
                  <Badge variant="secondary">已过期</Badge>
                ) : (
                  <Badge variant="outline">当前 run</Badge>
                )}
              </div>
              <p className="text-sm leading-6 text-muted-foreground">
                {generationRun.summary}
              </p>
              <MetricGrid
                rows={[
                  {
                    key: "uuid",
                    label: "Evaluation UUID",
                    value: generationRun.uuid,
                  },
                  {
                    key: "case_total",
                    label: "Case 总数",
                    value: String(generationRun.case_total),
                  },
                  {
                    key: "case_passed_count",
                    label: "通过",
                    value: String(generationRun.case_passed_count),
                  },
                  {
                    key: "case_warning_count",
                    label: "Warning",
                    value: String(generationRun.case_warning_count),
                  },
                  {
                    key: "case_failed_count",
                    label: "失败",
                    value: String(generationRun.case_failed_count),
                  },
                  {
                    key: "completed_at",
                    label: "完成时间",
                    value: formatOptionalDateTime(generationRun.completed_at),
                  },
                ]}
              />
              <RubricMetrics metrics={generationRun.summary_metrics} />
              {generationRun.error_summary ? (
                <ErrorLine message={generationRun.error_summary} />
              ) : null}
            </>
          ) : null}
        </AsyncState>
      </CardContent>
    </Card>
  );
}

function RagSummaryCard({
  readiness,
}: {
  readiness: ResearchQualityReadinessRun | null;
}) {
  const ragChecks = (readiness?.checks ?? []).filter((check) =>
    ["rag_index_health", "rag_retrieval_evaluation"].includes(check.key),
  );

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <div className="flex items-center gap-3">
          <Database className="size-5 text-muted-foreground" aria-hidden="true" />
          <div>
            <CardTitle>RAG 质量摘要</CardTitle>
            <CardDescription>从 readiness 检查项读取索引健康和检索评测指标。</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        {!readiness ? (
          <EmptyBlock title="暂无 RAG 摘要" />
        ) : ragChecks.length ? (
          <div className="grid gap-3">
            {ragChecks.map((check) => (
              <div key={check.key} className="grid gap-3 rounded-lg border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">{check.label}</p>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      {check.summary}
                    </p>
                  </div>
                  <StatusBadge
                    label={readinessCheckLabels[check.status]}
                    status={check.status}
                  />
                </div>
                {hasRows(check.metrics, ragMetricOrder) ? (
                  <MetricGrid rows={metricRows(check.metrics, ragMetricOrder)} />
                ) : null}
                <ReasonActionList check={check} />
              </div>
            ))}
          </div>
        ) : (
          <EmptyBlock title="本次 readiness 未包含 RAG 摘要" />
        )}
      </CardContent>
    </Card>
  );
}

function AsyncState({
  children,
  emptyTitle,
  error,
  isEmpty,
  isLoading,
  loadingTitle,
  onRetry,
}: {
  children: React.ReactNode;
  emptyTitle: string;
  error: unknown;
  isEmpty: boolean;
  isLoading: boolean;
  loadingTitle: string;
  onRetry: () => void;
}) {
  if (isLoading) {
    return <EmptyBlock title={loadingTitle} />;
  }

  if (error) {
    return (
      <div className="grid gap-3 rounded-lg border border-destructive/30 p-4">
        <ErrorLine message={formatError(error)} />
        <Button type="button" variant="outline" className="w-fit" onClick={onRetry}>
          <RefreshCcw data-icon="inline-start" />
          重新读取
        </Button>
      </div>
    );
  }

  if (isEmpty) {
    return <EmptyBlock title={emptyTitle} />;
  }

  return children;
}

function EmptyBlock({ title }: { title: string }) {
  return (
    <div className="rounded-lg border bg-muted/30 p-4 text-sm leading-6 text-muted-foreground">
      {title}
    </div>
  );
}

function StatusBadge({ label, status }: { label: string; status: string }) {
  return <Badge variant={statusBadgeVariant(status)}>{label}</Badge>;
}

function ErrorLine({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-background p-3 text-sm leading-6 text-destructive">
      <AlertTriangle className="mt-1 size-4 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

function MetricGrid({
  rows,
}: {
  rows: Array<{ key: string; label: string; value: string }>;
}) {
  return (
    <dl className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
      {rows.map((row) => (
        <div key={row.key} className="min-w-0 rounded-lg border bg-background p-3">
          <dt className="truncate text-xs text-muted-foreground">{row.label}</dt>
          <dd className="mt-1 break-words text-sm font-medium">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function CheckList({ checks }: { checks: ResearchQualityReadinessCheck[] }) {
  if (!checks.length) {
    return <EmptyBlock title="暂无检查项。" />;
  }

  return (
    <div className="grid gap-3">
      {checks.map((check) => (
        <div key={check.key} className="grid gap-3 rounded-lg border p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="font-medium">{check.label}</p>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {check.summary}
              </p>
            </div>
            <StatusBadge
              label={readinessCheckLabels[check.status]}
              status={check.status}
            />
          </div>
          {hasRows(check.metrics) ? <MetricGrid rows={metricRows(check.metrics)} /> : null}
          <ReasonActionList check={check} />
        </div>
      ))}
    </div>
  );
}

function ReasonActionList({ check }: { check: ResearchQualityReadinessCheck }) {
  if (!check.reasons.length && !check.actions.length) {
    return null;
  }

  return (
    <div className="grid gap-3 text-sm leading-6 md:grid-cols-2">
      {check.reasons.length ? (
        <div>
          <p className="font-medium">原因</p>
          <ul className="mt-1 grid gap-1 text-muted-foreground">
            {check.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {check.actions.length ? (
        <div>
          <p className="font-medium">建议动作</p>
          <ul className="mt-1 grid gap-1 text-muted-foreground">
            {check.actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function RubricMetrics({ metrics }: { metrics: Record<string, unknown> }) {
  const dimensions = metrics.rubric_dimensions;

  if (!dimensions || typeof dimensions !== "object" || Array.isArray(dimensions)) {
    return null;
  }

  const rows = Object.entries(dimensions as Record<string, unknown>).map(
    ([key, value]) => ({
      key,
      label: key,
      value: formatMetricValue(value),
    }),
  );

  if (!rows.length) {
    return null;
  }

  return (
    <div className="grid gap-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Activity className="size-4 text-muted-foreground" aria-hidden="true" />
        Rubric 维度摘要
      </div>
      <MetricGrid rows={rows} />
    </div>
  );
}
