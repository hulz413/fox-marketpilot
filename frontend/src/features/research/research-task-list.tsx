"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  ArrowRight,
  ExternalLink,
  Eye,
  FileText,
  MoreHorizontal,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  EmptyResearchState,
  StatusBadge,
} from "@/features/product-skeleton/components";

import { fetchResearchTasks, startResearchRun, type ResearchTask } from "./api";

const statusLabels: Record<ResearchTask["status"], string> = {
  created: "已创建",
  queued: "运行中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
};

const stageLabels: Record<ResearchTask["current_stage"], string> = {
  intake: "需求已提交",
  queued: "等待后台执行",
  normalize_intake: "整理研究需求",
  generate_opportunities: "生成基础推荐",
  validate_results: "校验推荐结果",
  persist_results: "保存研究结果",
  collect_research_sources: "收集公开来源线索",
  generate_demand_insights: "生成需求洞察",
  completed: "基础推荐已生成",
  failed: "生成失败",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ResearchTaskList() {
  const queryClient = useQueryClient();
  const {
    data: tasks,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["research-tasks"],
    queryFn: fetchResearchTasks,
    refetchInterval: 5000,
  });
  const startRunMutation = useMutation({
    mutationFn: startResearchRun,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["research-tasks"] });
    },
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>研究任务列表</CardTitle>
          <CardDescription>正在加载真实研究任务。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-24 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="rounded-lg border-destructive/30">
        <CardHeader>
          <CardTitle>任务加载失败</CardTitle>
          <CardDescription>
            {error instanceof Error ? error.message : "无法读取研究任务。"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!tasks?.length) {
    return <EmptyResearchState />;
  }

  return (
    <Card className="overflow-hidden rounded-lg py-0 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between gap-4 border-b px-5 py-4">
        <div>
          <CardTitle>研究任务列表</CardTitle>
          <CardDescription>展示真实创建的任务和当前状态。</CardDescription>
        </div>
        <Badge variant="secondary">{tasks.length} 个任务</Badge>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid gap-3 p-4 md:hidden">
          {tasks.map((task) => (
            <TaskCard
              key={task.uuid}
              task={task}
              isStarting={startRunMutation.isPending}
              onStart={() => startRunMutation.mutate(task.uuid)}
            />
          ))}
        </div>
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="h-14 px-5">任务</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>阶段摘要</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="pr-5 text-right">下一步</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.uuid} className="h-16">
                  <TableCell className="px-5">
                    <TaskTitle task={task} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={statusLabels[task.status]} />
                  </TableCell>
                  <TableCell className="max-w-[220px] text-sm text-muted-foreground">
                    {stageLabels[task.current_stage]}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {formatDate(task.created_at)}
                  </TableCell>
                  <TableCell className="pr-5">
                    <TaskActions
                      task={task}
                      isStarting={startRunMutation.isPending}
                      onStart={() => startRunMutation.mutate(task.uuid)}
                    />
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

function TaskCard({
  task,
  isStarting,
  onStart,
}: {
  task: ResearchTask;
  isStarting: boolean;
  onStart: () => void;
}) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={statusLabels[task.status]} />
        <Badge variant="outline">{stageLabels[task.current_stage]}</Badge>
      </div>
      <div className="mt-3">
        <TaskTitle task={task} />
      </div>
      {task.failure_reason ? (
        <p className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {task.failure_reason}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <TaskActions task={task} isStarting={isStarting} onStart={onStart} />
      </div>
    </article>
  );
}

function TaskTitle({ task }: { task: ResearchTask }) {
  const title = task.title.trim();
  const brief = task.brief.trim();
  const showBrief = brief && brief !== title;
  const meta = [
    task.budget,
    task.target_channels.join("、"),
    task.target_audience,
  ].filter(Boolean);

  return (
    <div className="min-w-0">
      <p className="max-w-[520px] truncate font-medium">{title || brief}</p>
      {showBrief ? (
        <p className="mt-1 max-w-[560px] truncate text-xs text-muted-foreground">
          {brief}
        </p>
      ) : null}
      {meta.length ? (
        <p className="mt-1 max-w-[560px] truncate text-xs text-muted-foreground">
          {meta.join(" · ")}
        </p>
      ) : null}
    </div>
  );
}

function TaskActions({
  task,
  isStarting,
  onStart,
}: {
  task: ResearchTask;
  isStarting: boolean;
  onStart: () => void;
}) {
  if (task.status === "completed") {
    return (
      <div className="flex justify-end gap-2">
        <Button asChild size="sm">
          <Link href={`/opportunities?task=${task.uuid}`}>
            查看结果
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
        <TaskSecondaryActions task={task} />
      </div>
    );
  }

  if (task.status === "queued" || task.status === "running") {
    return (
      <div className="flex justify-end gap-2">
        <Button asChild size="sm">
          <Link href={`/research/tasks/${task.uuid}`}>
            <RefreshCcw data-icon="inline-start" />
            查看进度
          </Link>
        </Button>
        <TaskSecondaryActions task={task} />
      </div>
    );
  }

  return (
    <div className="flex justify-end gap-2">
      <Button
        type="button"
        variant={task.status === "failed" ? "outline" : "default"}
        size="sm"
        disabled={isStarting}
        onClick={onStart}
      >
        {task.status === "failed" ? (
          <RefreshCcw data-icon="inline-start" />
        ) : (
          <Play data-icon="inline-start" />
        )}
        {task.status === "failed" ? "重新运行" : "开始研究"}
      </Button>
      <TaskSecondaryActions task={task} />
    </div>
  );
}

function TaskSecondaryActions({ task }: { task: ResearchTask }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label="更多操作">
          <MoreHorizontal aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuLabel>次要入口</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem asChild>
            <Link href={`/research/tasks/${task.uuid}`}>
              <Eye aria-hidden="true" />
              进度
            </Link>
          </DropdownMenuItem>
          {task.status === "completed" ? (
            <DropdownMenuItem asChild>
              <Link href={`/reports/${task.uuid}`}>
                <FileText aria-hidden="true" />
                报告
              </Link>
            </DropdownMenuItem>
          ) : null}
          {task.trace_url ? (
            <DropdownMenuItem asChild>
              <a href={task.trace_url} target="_blank" rel="noreferrer">
                <ExternalLink aria-hidden="true" />
                LangSmith
              </a>
            </DropdownMenuItem>
          ) : null}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
