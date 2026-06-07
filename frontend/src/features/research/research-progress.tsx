"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Circle,
  Clock3,
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
import { TaskContextNavigation } from "@/features/product-skeleton/components";
import { formatDateTime } from "@/lib/datetime";
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
    key: "index_rag_evidence",
    label: "整理公开来源证据",
    description: "将已收集公开线索整理为后续分析可检索的待验证证据。",
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
    key: "estimate_validation_budgets",
    label: "估算验证预算",
    description: "粗略估算首批验证预算、毛利空间和待验证假设。",
  },
  {
    key: "review_opportunity_risks",
    label: "复核商机风险",
    description: "提示质量、履约、售后、合规、库存、竞争和平台规则风险。",
  },
  {
    key: "create_action_plans",
    label: "生成行动计划",
    description: "整理首批验证计划、内容角度、询盘话术和上架前检查清单。",
  },
  {
    key: "completed",
    label: "完成",
    description: "基础商机推荐和可用增强信息已经可以查看。",
  },
];

function formatOptionalDateTime(value: string | null) {
  if (!value) {
    return null;
  }

  return formatDateTime(value);
}

function formatDuration(durationMs: number | null) {
  if (durationMs === null) {
    return null;
  }

  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }

  return `${(durationMs / 1000).toFixed(1)}s`;
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
      <div className="grid gap-5">
        <TaskContextNavigation
          active="progress"
          sourcesHref={`/reports/${taskUuid}#sources`}
          taskUuid={taskUuid}
        />
        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>研究进度</CardTitle>
            <CardDescription>正在读取任务运行状态。</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-36 rounded-md border bg-muted/40" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !progress) {
    return (
      <div className="grid gap-5">
        <TaskContextNavigation
          active="progress"
          sourcesHref={`/reports/${taskUuid}#sources`}
          taskUuid={taskUuid}
        />
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
                返回我的研究
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid gap-5">
      <TaskContextNavigation
        active="progress"
        resultsReady={progress.status === "completed"}
        sourcesHref={`/reports/${progress.task.uuid}#sources`}
        task={progress.task}
        taskUuid={progress.task.uuid}
      />
      <ProgressActions
        progress={progress}
        isStarting={startRunMutation.isPending}
        onStart={() => startRunMutation.mutate(progress.task.uuid)}
      />
      <StageTimeline progress={progress} />
    </div>
  );
}

function ProgressActions({
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
  const canStart = hasAction("start");
  const canRerun = hasAction("rerun");

  if (!progress.failure_reason && !canStart && !canRerun) {
    return null;
  }

  return (
    <Card className="rounded-lg">
      <CardContent className="grid gap-5">
        {progress.failure_reason ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {progress.failure_reason}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {canStart ? (
            <Button type="button" disabled={isStarting} onClick={onStart}>
              <Play data-icon="inline-start" />
              {isStarting ? "正在启动" : "启动研究"}
            </Button>
          ) : null}
          {canRerun ? (
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
        </div>
      </CardContent>
    </Card>
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
  const firstWorkerEvent = progress.events.find(
    (item) => item.stage !== "opportunity_research",
  );
  const orderedStages = stageTimeline
    .map((stage, index) => {
      const event = eventsByStage.get(stage.key);

      return {
        event,
        index,
        sortTime: getStageSortTime(progress, stage.key, event, firstWorkerEvent),
        stage,
      };
    })
    .sort((left, right) => {
      if (left.sortTime === 0 && right.sortTime !== 0) {
        return -1;
      }

      if (left.sortTime !== 0 && right.sortTime === 0) {
        return 1;
      }

      if (left.sortTime !== right.sortTime) {
        return right.sortTime - left.sortTime;
      }

      return right.index - left.index;
    });

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle>阶段时间线</CardTitle>
        <CardDescription>
          展示当前 run 的阶段事件；未开始的阶段在前，已有事件按最新时间倒序。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {hasMissingEvents ? (
          <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            正在等待阶段事件写入。任务状态会先更新，时间线随后出现。
          </div>
        ) : null}

        <div className="grid gap-3">
          {orderedStages.map(({ event, stage }) => (
            <StageRow
              key={stage.key}
              event={event}
              progress={progress}
              stage={stage}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function getStageSortTime(
  progress: ResearchProgress,
  stage: ResearchTaskStage,
  event: AgentRunEvent | undefined,
  firstWorkerEvent: AgentRunEvent | undefined,
) {
  if (event?.completed_at) {
    return Date.parse(event.completed_at);
  }

  if (event?.started_at) {
    return Date.parse(event.started_at);
  }

  if (stage === "completed" && progress.status === "completed") {
    return Date.parse(progress.task.updated_at);
  }

  if (stage === "failed" && progress.status === "failed") {
    return Date.parse(progress.task.updated_at);
  }

  if (stage === "queued" && progress.status !== "created") {
    return Date.parse(firstWorkerEvent?.started_at ?? progress.task.updated_at);
  }

  if (isLiveStatus(progress.status) && progress.current_stage === stage) {
    return Date.parse(progress.task.updated_at);
  }

  return 0;
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
  const startedAt = formatOptionalDateTime(event?.started_at ?? null);
  const completedAt = formatOptionalDateTime(event?.completed_at ?? null);
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
