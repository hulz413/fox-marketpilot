"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Circle,
  Clock3,
  ExternalLink,
  FileText,
  Play,
  RefreshCcw,
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
import { TaskContextNavigation } from "@/features/product-skeleton/components";
import { cn } from "@/lib/utils";

import {
  fetchResearchProgress,
  startResearchRun,
  type AgentRunEvent,
  type ResearchProgress,
  type ResearchProgressAction,
  type ResearchTaskStage,
  type ResearchTaskStatus,
} from "./api";

const statusLabels: Record<ResearchTaskStatus, string> = {
  created: "待启动",
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

const stageLabels: Record<ResearchTaskStage, string> = {
  intake: "需求已提交",
  queued: "等待后台执行",
  normalize_intake: "整理研究需求",
  generate_opportunities: "生成基础推荐",
  validate_results: "校验推荐结果",
  persist_results: "保存研究结果",
  collect_research_sources: "收集公开来源线索",
  generate_demand_insights: "生成需求洞察",
  generate_supply_candidates: "生成货源候选",
  generate_competitor_references: "生成竞品参考",
  completed: "基础推荐已生成",
  failed: "生成失败",
};

const stageTimeline: Array<{
  key: ResearchTaskStage;
  label: string;
  description: string;
}> = [
  {
    key: "queued",
    label: "等待后台执行",
    description: "任务已进入后台队列，等待 worker 接手。",
  },
  {
    key: "normalize_intake",
    label: "整理研究需求",
    description: "归一化预算、渠道、品类和限制条件。",
  },
  {
    key: "generate_opportunities",
    label: "生成基础推荐",
    description: "基于任务输入生成 3-5 个待验证商机。",
  },
  {
    key: "validate_results",
    label: "校验推荐结果",
    description: "检查字段完整性、排序、数量和风险等级。",
  },
  {
    key: "persist_results",
    label: "保存研究结果",
    description: "写入商机推荐并更新任务状态。",
  },
  {
    key: "collect_research_sources",
    label: "收集公开来源线索",
    description: "补充公开来源线索，作为后续判断的初步参考。",
  },
  {
    key: "generate_demand_insights",
    label: "生成需求洞察",
    description: "拆解人群、场景、购买动机和内容种草角度。",
  },
  {
    key: "generate_supply_candidates",
    label: "生成货源候选",
    description: "整理候选找货方向、初步参考信息和供应商待确认问题。",
  },
  {
    key: "generate_competitor_references",
    label: "生成竞品参考",
    description: "整理类似产品参考、常见售价和差异化切入点。",
  },
  {
    key: "completed",
    label: "完成",
    description: "基础商机推荐和可用增强信息已经可以查看。",
  },
];

function formatDateTime(value: string | null) {
  if (!value) {
    return null;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function formatDuration(durationMs: number | null) {
  if (durationMs === null) {
    return null;
  }

  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }

  return `${(durationMs / 1000).toFixed(1)} s`;
}

function formatError(error: unknown) {
  const message = error instanceof Error ? error.message : "";

  if (message.toLowerCase().includes("not found")) {
    return "研究任务不存在或不可访问。";
  }

  return message || "无法读取研究进度，请稍后重试。";
}

function isLiveStatus(status?: ResearchTaskStatus) {
  return status === "queued" || status === "running";
}

export function ResearchProgressView({ taskUuid }: { taskUuid: string }) {
  const queryClient = useQueryClient();
  const {
    data: progress,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["research-progress", taskUuid],
    queryFn: () => fetchResearchProgress(taskUuid),
    refetchInterval: (query) =>
      isLiveStatus(query.state.data?.status) ? 3000 : false,
  });
  const startRunMutation = useMutation({
    mutationFn: startResearchRun,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["research-progress", taskUuid],
        }),
        queryClient.invalidateQueries({ queryKey: ["research-tasks"] }),
      ]);
    },
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>研究进度</CardTitle>
          <CardDescription>正在读取任务运行状态。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-36 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error || !progress) {
    return (
      <Card className="rounded-lg border-destructive/30">
        <CardHeader>
          <CardTitle>研究进度读取失败</CardTitle>
          <CardDescription>{formatError(error)}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
          <Button asChild variant="ghost">
            <Link href="/research/tasks">
              <ArrowLeft data-icon="inline-start" />
              返回任务
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-5">
      <TaskContextNavigation
        active="progress"
        resultsReady={progress.status === "completed"}
        sourcesHref={`/reports/${progress.task.uuid}#sources`}
        taskUuid={progress.task.uuid}
      />
      <ProgressSummary
        progress={progress}
        isStarting={startRunMutation.isPending}
        onStart={() => startRunMutation.mutate(progress.task.uuid)}
      />
      <StageTimeline progress={progress} />
    </div>
  );
}

function ProgressSummary({
  progress,
  isStarting,
  onStart,
}: {
  progress: ResearchProgress;
  isStarting: boolean;
  onStart: () => void;
}) {
  const hasAction = (action: ResearchProgressAction) =>
    progress.available_actions.includes(action);
  const eventsByStage = new Map(
    progress.events.map((event) => [event.stage, event] as const),
  );
  const completedStageCount = stageTimeline.filter(
    (stage) => getStageState(progress, stage.key, eventsByStage.get(stage.key)) === "completed",
  ).length;
  const progressMessage = getProgressMessage(progress, completedStageCount);

  return (
    <Card className="rounded-lg">
      <CardHeader className="gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={progress.status} />
          <Badge variant="outline">{stageLabels[progress.current_stage]}</Badge>
          {progress.run_id ? <Badge variant="secondary">run 已创建</Badge> : null}
        </div>
        <div>
          <CardTitle className="text-2xl">{progress.task.title}</CardTitle>
          <CardDescription className="mt-2 leading-6">
            {progress.task.brief}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="grid gap-5">
        {progress.failure_reason ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {progress.failure_reason}
          </div>
        ) : null}

        <section className="rounded-lg border bg-primary/5 p-4">
          <p className="text-sm font-semibold text-primary">
            当前阶段：{stageLabels[progress.current_stage]}
          </p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {progressMessage}
          </p>
        </section>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <InfoBlock label="当前阶段" value={stageLabels[progress.current_stage]} />
          <InfoBlock
            label="已完成阶段"
            value={`${completedStageCount}/${stageTimeline.length}`}
          />
          <InfoBlock label="预算" value={progress.task.budget ?? "未填写"} />
          <InfoBlock
            label="目标渠道"
            value={progress.task.target_channels.join("、") || "未填写"}
          />
        </div>

        <Separator />

        <div className="flex flex-wrap gap-2">
          {hasAction("start") ? (
            <Button type="button" disabled={isStarting} onClick={onStart}>
              <Play data-icon="inline-start" />
              {isStarting ? "正在启动" : "启动研究"}
            </Button>
          ) : null}
          {hasAction("rerun") ? (
            <Button
              type="button"
              variant="outline"
              disabled={isStarting}
              onClick={onStart}
            >
              <RefreshCcw data-icon="inline-start" />
              {isStarting ? "正在启动" : "重新运行"}
            </Button>
          ) : null}
          {hasAction("view_opportunities") ? (
            <Button asChild>
              <Link href={`/opportunities?task=${progress.task.uuid}`}>
                商机推荐
                <BarChart3 data-icon="inline-end" />
              </Link>
            </Button>
          ) : null}
          {hasAction("view_report") ? (
            <Button asChild variant="outline">
              <Link href={`/reports/${progress.task.uuid}`}>
                <FileText data-icon="inline-start" />
                基础报告
              </Link>
            </Button>
          ) : null}
          <Button asChild variant="ghost">
            <Link href="/research/tasks">
              <ArrowLeft data-icon="inline-start" />
              返回任务
            </Link>
          </Button>
        </div>

        <RunDetails progress={progress} />
      </CardContent>
    </Card>
  );
}

function getProgressMessage(
  progress: ResearchProgress,
  completedStageCount: number,
) {
  if (progress.status === "completed") {
    return "基础商机推荐已经生成，可以继续查看商机列表、详情、货源候选、竞品参考和基础报告。";
  }

  if (progress.status === "failed") {
    return "本次运行没有完成，可以查看失败原因后重新运行。";
  }

  if (progress.status === "created") {
    return "需求已经保存，启动研究后会进入后台队列并生成基础商机推荐。";
  }

  return `系统正在推进研究流程，已完成 ${completedStageCount} 个阶段。你可以停留在这里等待状态刷新。`;
}

function RunDetails({ progress }: { progress: ResearchProgress }) {
  const latestEvent = progress.events[progress.events.length - 1];
  const latestStageLabel = latestEvent
    ? stageLabels[latestEvent.stage as ResearchTaskStage] ?? latestEvent.stage
    : "暂无事件";

  return (
    <section className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">运行详情</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            调试信息用于排障，不影响用户继续查看商机结果。
          </p>
        </div>
        {progress.trace_url ? (
          <Button asChild variant="outline" size="sm">
            <a href={progress.trace_url} target="_blank" rel="noreferrer">
              <ExternalLink data-icon="inline-start" />
              LangSmith
            </a>
          </Button>
        ) : null}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <InfoBlock label="运行 ID" value={progress.run_id ?? "尚未启动"} />
        <InfoBlock label="Trace" value={progress.trace_id ?? "未启用或未生成"} />
        <InfoBlock label="最近事件" value={latestStageLabel} />
      </div>
    </section>
  );
}

function StageTimeline({ progress }: { progress: ResearchProgress }) {
  const eventsByStage = new Map(
    progress.events.map((event) => [event.stage, event] as const),
  );
  const hasMissingEvents =
    Boolean(progress.run_id) &&
    progress.events.length === 0 &&
    progress.status !== "created";

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle>阶段时间线</CardTitle>
        <CardDescription>
          展示当前 run 的阶段事件；重新运行后默认只看最新 run。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {hasMissingEvents ? (
          <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            正在等待阶段事件写入。任务状态会先更新，时间线随后出现。
          </div>
        ) : null}

        <div className="grid gap-3">
          {stageTimeline.map((stage) => (
            <StageRow
              key={stage.key}
              event={eventsByStage.get(stage.key)}
              progress={progress}
              stage={stage}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function StageRow({
  event,
  progress,
  stage,
}: {
  event?: AgentRunEvent;
  progress: ResearchProgress;
  stage: (typeof stageTimeline)[number];
}) {
  const state = getStageState(progress, stage.key, event);
  const startedAt = formatDateTime(event?.started_at ?? null);
  const completedAt = formatDateTime(event?.completed_at ?? null);
  const firstWorkerEvent = progress.events.find(
    (item) => item.stage !== "opportunity_research",
  );
  const fallbackCompletedAt =
    stage.key === "completed" && progress.status === "completed"
      ? formatDateTime(progress.task.updated_at)
      : stage.key === "queued" && state === "completed"
        ? formatDateTime(firstWorkerEvent?.started_at ?? progress.task.updated_at)
      : null;
  const duration = formatDuration(event?.duration_ms ?? null);

  return (
    <section
      className={cn(
        "grid gap-3 rounded-lg border p-4 md:grid-cols-[auto_minmax(0,1fr)_auto]",
        state === "active" ? "border-primary/40 bg-primary/5" : "",
        state === "failed" ? "border-destructive/30 bg-destructive/10" : "",
      )}
    >
      <StageIcon state={state} />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold">{stage.label}</h2>
          <Badge variant={state === "pending" ? "outline" : "secondary"}>
            {stageStateLabels[state]}
          </Badge>
        </div>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          {stage.description}
        </p>
        {event?.error_summary ? (
          <p className="mt-2 text-sm text-destructive">{event.error_summary}</p>
        ) : null}
      </div>
      <div className="text-sm text-muted-foreground md:text-right">
        <p>{completedAt ?? startedAt ?? fallbackCompletedAt ?? "等待中"}</p>
        {duration ? <p className="mt-1">耗时 {duration}</p> : null}
      </div>
    </section>
  );
}

type StageState = "pending" | "active" | "completed" | "failed";

const stageStateLabels: Record<StageState, string> = {
  pending: "等待中",
  active: "进行中",
  completed: "已完成",
  failed: "失败",
};

function getStageState(
  progress: ResearchProgress,
  stage: ResearchTaskStage,
  event?: AgentRunEvent,
): StageState {
  if (event?.status === "failed") {
    return "failed";
  }

  if (event?.status === "completed") {
    return "completed";
  }

  if (event?.status === "running") {
    return "active";
  }

  if (stage === "queued") {
    if (progress.status === "created") {
      return "pending";
    }

    if (progress.current_stage === "queued") {
      return "active";
    }

    return "completed";
  }

  if (progress.status === "failed" && progress.current_stage === stage) {
    return "failed";
  }

  if (isLiveStatus(progress.status) && progress.current_stage === stage) {
    return "active";
  }

  if (progress.status === "completed" && stage === "completed") {
    return "completed";
  }

  return "pending";
}

function StageIcon({ state }: { state: StageState }) {
  if (state === "completed") {
    return <CheckCircle2 className="mt-1 size-5 text-primary" aria-hidden="true" />;
  }

  if (state === "failed") {
    return (
      <AlertTriangle className="mt-1 size-5 text-destructive" aria-hidden="true" />
    );
  }

  if (state === "active") {
    return <Clock3 className="mt-1 size-5 text-primary" aria-hidden="true" />;
  }

  return <Circle className="mt-1 size-5 text-muted-foreground" aria-hidden="true" />;
}

function StatusBadge({ status }: { status: ResearchTaskStatus }) {
  const tone =
    status === "failed"
      ? "border-destructive/30 bg-destructive/10 text-destructive"
      : status === "queued" || status === "running"
        ? "border-primary/20 bg-primary/10 text-primary"
        : "border-transparent bg-secondary text-secondary-foreground";

  return (
    <Badge variant="outline" className={cn("rounded-full px-3 py-1", tone)}>
      {statusLabels[status]}
    </Badge>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <section className="rounded-lg border bg-background p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold">{value}</p>
    </section>
  );
}
