"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, FileText, Play, RefreshCcw, TimerReset } from "lucide-react";

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
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ResearchHistoryList() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: tasks, error, isLoading, refetch } = useQuery({
    queryKey: ["research-tasks"],
    queryFn: fetchResearchTasks,
    refetchInterval: 5000,
  });
  const startRunMutation = useMutation({
    mutationFn: startResearchRun,
    onSuccess: async (task) => {
      await queryClient.invalidateQueries({ queryKey: ["research-tasks"] });
      router.push(`/research/tasks/${task.uuid}`);
    },
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>历史研究列表</CardTitle>
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
          <CardTitle>历史加载失败</CardTitle>
          <CardDescription>
            {error instanceof Error ? error.message : "无法读取研究历史。"}
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
          <CardTitle>历史研究列表</CardTitle>
          <CardDescription>真实任务的继续入口，按创建时间倒序展示。</CardDescription>
        </div>
        <Badge variant="secondary">{tasks.length} 条记录</Badge>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid gap-3 p-4 md:hidden">
          {tasks.map((task) => (
            <HistoryCard
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
                <TableHead>创建时间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>当前阶段</TableHead>
                <TableHead className="pr-5 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.uuid} className="h-16">
                  <TableCell className="px-5">
                    <p className="max-w-[420px] truncate font-medium">
                      {task.title}
                    </p>
                    <p className="mt-1 max-w-[520px] truncate text-xs text-muted-foreground">
                      {task.brief === task.title ? task.budget : task.brief}
                    </p>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {formatDate(task.created_at)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={statusLabels[task.status]} />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {stageLabels[task.current_stage]}
                  </TableCell>
                  <TableCell className="pr-5">
                    <HistoryActions
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

function HistoryCard({
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
      <h2 className="mt-3 font-semibold">{task.title}</h2>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">
        {formatDate(task.created_at)}
      </p>
      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <HistoryActions task={task} isStarting={isStarting} onStart={onStart} />
      </div>
    </article>
  );
}

function HistoryActions({
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
      <div className="flex flex-wrap justify-end gap-2">
        <Button asChild size="sm">
          <Link href={`/reports/${task.uuid}`}>
            <FileText data-icon="inline-start" />
            报告
          </Link>
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={isStarting}
          onClick={onStart}
        >
          <RefreshCcw data-icon="inline-start" />
          重新运行
        </Button>
      </div>
    );
  }

  if (task.status === "queued" || task.status === "running") {
    return (
      <Button asChild size="sm">
        <Link href={`/research/tasks/${task.uuid}`}>
          <TimerReset data-icon="inline-start" />
          进度
        </Link>
      </Button>
    );
  }

  return (
    <div className="flex flex-wrap justify-end gap-2">
      <Button
        type="button"
        size="sm"
        variant={task.status === "failed" ? "outline" : "default"}
        disabled={isStarting}
        onClick={onStart}
      >
        {task.status === "failed" ? (
          <RefreshCcw data-icon="inline-start" />
        ) : (
          <Play data-icon="inline-start" />
        )}
        {task.status === "failed" ? "重新运行" : "启动研究"}
      </Button>
      <Button asChild variant="ghost" size="sm">
        <Link href={`/research/tasks/${task.uuid}`}>
          进度
          <ArrowRight data-icon="inline-end" />
        </Link>
      </Button>
    </div>
  );
}
