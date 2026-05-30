"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowRight, ClipboardList, FileText, RefreshCcw } from "lucide-react";

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
  fetchTaskOpportunities,
  type Opportunity,
  type OpportunityRiskLevel,
} from "@/features/research/api";
import { TaskContextNavigation } from "@/features/product-skeleton/components";

const riskLabels: Record<OpportunityRiskLevel, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

export function OpportunityList() {
  const searchParams = useSearchParams();
  const taskUuid = searchParams.get("task");
  const {
    data: opportunities,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["task-opportunities", taskUuid],
    queryFn: () => fetchTaskOpportunities(taskUuid ?? ""),
    enabled: Boolean(taskUuid),
  });

  if (!taskUuid) {
    return (
      <EmptyOpportunityState
        title="请选择一条研究任务"
        description="商机推荐需要从已完成的真实研究任务进入。"
      />
    );
  }

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>基础商机推荐</CardTitle>
          <CardDescription>正在读取任务生成的待验证商机。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-28 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="rounded-lg border-destructive/30">
        <CardHeader>
          <CardTitle>商机读取失败</CardTitle>
          <CardDescription>
            {error instanceof Error ? error.message : "无法读取商机结果。"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
          <Button asChild variant="ghost">
            <Link href="/research/tasks">
              <ClipboardList data-icon="inline-start" />
              返回任务
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!opportunities?.length) {
    return (
      <EmptyOpportunityState
        title="还没有生成商机"
        description="任务可能仍在运行，或本次运行尚未产出可展示的基础推荐。"
      />
    );
  }

  return (
    <div className="grid gap-5">
      <TaskContextNavigation active="opportunities" taskUuid={taskUuid} />
      <Card className="overflow-hidden rounded-lg py-0 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between gap-4 border-b px-5 py-4">
        <div>
          <CardTitle>基础商机推荐</CardTitle>
          <CardDescription>
            基于任务输入生成的待验证草案，不包含来源或竞品核验。
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{opportunities.length} 个推荐</Badge>
          <Button asChild variant="outline" size="sm">
            <Link href={`/reports/${taskUuid}`}>
              <FileText data-icon="inline-start" />
              基础报告
            </Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid gap-3 p-4 md:hidden">
          {opportunities.map((item) => (
            <OpportunityCard key={item.uuid} opportunity={item} />
          ))}
        </div>
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="h-14 px-5">排序</TableHead>
                <TableHead>商机名称</TableHead>
                <TableHead>验证动作</TableHead>
                <TableHead>价格 / 风险</TableHead>
                <TableHead>推荐优先级</TableHead>
                <TableHead className="pr-5 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {opportunities.map((item) => (
                <OpportunityRow key={item.uuid} opportunity={item} />
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
      </Card>
    </div>
  );
}

function OpportunityRow({ opportunity }: { opportunity: Opportunity }) {
  return (
    <TableRow className="h-16">
      <TableCell className="px-5">
        <Badge variant="outline">{String(opportunity.rank).padStart(2, "0")}</Badge>
      </TableCell>
      <TableCell>
        <p className="font-medium">{opportunity.name}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {opportunity.product_direction}
        </p>
      </TableCell>
      <TableCell className="max-w-[280px] text-sm leading-6 text-muted-foreground">
        {opportunity.next_step_summary}
      </TableCell>
      <TableCell>
        <p>{opportunity.price_band}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          风险 {riskLabels[opportunity.risk_level]}
        </p>
      </TableCell>
      <TableCell>
        <Badge className="rounded-full bg-primary/10 text-primary">
          {opportunity.priority_label}
        </Badge>
      </TableCell>
      <TableCell className="pr-5 text-right">
        <Button asChild variant="outline" size="sm">
          <Link href={`/opportunities/${opportunity.uuid}`}>
            详情
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      </TableCell>
    </TableRow>
  );
}

function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{String(opportunity.rank).padStart(2, "0")}</Badge>
            <Badge className="rounded-full bg-primary/10 text-primary">
              {opportunity.priority_label}
            </Badge>
            <Badge variant="secondary">风险 {riskLabels[opportunity.risk_level]}</Badge>
          </div>
          <h2 className="mt-3 font-semibold">{opportunity.name}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {opportunity.product_direction}
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href={`/opportunities/${opportunity.uuid}`}>
            详情
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      </div>
      <div className="mt-4 grid gap-3 text-sm">
        <InfoLine label="目标人群" value={opportunity.target_audience} />
        <InfoLine label="价格带" value={opportunity.price_band} />
        <InfoLine label="验证动作" value={opportunity.next_step_summary} />
      </div>
    </article>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 leading-6">{value}</p>
    </div>
  );
}

function EmptyOpportunityState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card className="rounded-lg border-dashed">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild>
          <Link href="/research/tasks">
            返回研究任务
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
