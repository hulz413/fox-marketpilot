"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, RefreshCcw } from "lucide-react";

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

import { fetchResearchTasks, type ResearchTask } from "./api";

const statusLabels: Record<ResearchTask["status"], string> = {
  created: "已创建",
};

const stageLabels: Record<ResearchTask["current_stage"], string> = {
  intake: "需求已提交",
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
  const {
    data: tasks,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["research-tasks"],
    queryFn: fetchResearchTasks,
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
        <Table className="min-w-[760px]">
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              <TableHead className="h-14 px-5">任务标题</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>当前阶段</TableHead>
              <TableHead>创建时间</TableHead>
              <TableHead className="pr-5 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((task) => (
              <TableRow key={task.uuid} className="h-16">
                <TableCell className="px-5">
                  <p className="max-w-[420px] truncate font-medium">{task.title}</p>
                  <p className="mt-1 max-w-[520px] truncate text-xs text-muted-foreground">
                    {task.brief}
                  </p>
                </TableCell>
                <TableCell>
                  <StatusBadge status={statusLabels[task.status]} />
                </TableCell>
                <TableCell>{stageLabels[task.current_stage]}</TableCell>
                <TableCell>{formatDate(task.created_at)}</TableCell>
                <TableCell className="pr-5">
                  <div className="flex justify-end gap-2">
                    <Button asChild variant="outline" size="sm">
                      <Link href={`/research/tasks?task=${task.uuid}`}>
                        查看任务
                        <ArrowRight data-icon="inline-end" />
                      </Link>
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
