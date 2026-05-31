"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, BarChart3, RefreshCcw } from "lucide-react";

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
import { TaskCompetitorReferenceSummary } from "@/features/research/competitor-references";
import { TaskDemandInsightSummary } from "@/features/research/demand-insights";
import { TaskSourceInsights } from "@/features/research/source-insights";
import { TaskSupplyCandidateSummary } from "@/features/research/supply-candidates";
import { TaskValidationBudgetSummary } from "@/features/research/validation-budgets";

const riskLabels: Record<OpportunityRiskLevel, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

export function ReportSummary({ taskUuid }: { taskUuid: string }) {
  const isDemoRoute = taskUuid === "demo-report";
  const {
    data: opportunities,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["report-opportunities", taskUuid],
    queryFn: () => fetchTaskOpportunities(taskUuid),
    enabled: !isDemoRoute,
  });

  if (isDemoRoute) {
    return (
      <EmptyReportState
        title="请选择一条已完成任务"
        description="基础报告需要从真实研究任务进入，不展示静态演示报告作为真实结果。"
      />
    );
  }

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>基础报告</CardTitle>
          <CardDescription>正在读取待验证商机摘要。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="rounded-lg border-destructive/30">
        <CardHeader>
          <CardTitle>报告读取失败</CardTitle>
          <CardDescription>
            {error instanceof Error ? error.message : "无法读取基础报告。"}
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

  if (!opportunities?.length) {
    return (
      <EmptyReportState
        title="还没有基础报告"
        description="任务尚未生成商机结果，完成后这里会汇总推荐排序、风险等级和下一步行动摘要。"
      />
    );
  }

  return <ReportContent opportunities={opportunities} taskUuid={taskUuid} />;
}

function ReportContent({
  opportunities,
  taskUuid,
}: {
  opportunities: Opportunity[];
  taskUuid: string;
}) {
  const topOpportunity = opportunities[0];

  return (
    <div className="grid gap-5">
      <TaskContextNavigation
        active="report"
        sourcesHref="#sources"
        taskUuid={taskUuid}
      />
      <Card className="rounded-lg">
        <CardHeader>
          <Badge variant="secondary" className="w-fit">
            待验证基础报告
          </Badge>
          <CardTitle className="text-2xl">基础商机推荐摘要</CardTitle>
          <CardDescription>
            基于任务输入生成的验证草案；来源区域仅展示公开线索和初步参考，不代表完整市场核验。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <SummaryBlock title="推荐结论" body={`优先验证 ${topOpportunity.name}。`} />
          <SummaryBlock
            title="风险摘要"
            body={`当前最高优先级商机风险等级为 ${riskLabels[topOpportunity.risk_level]}。`}
          />
          <SummaryBlock title="下一步行动" body={topOpportunity.next_step_summary} />
        </CardContent>
      </Card>

      <TaskDemandInsightSummary opportunities={opportunities} taskUuid={taskUuid} />

      <TaskSupplyCandidateSummary opportunities={opportunities} taskUuid={taskUuid} />

      <TaskCompetitorReferenceSummary
        opportunities={opportunities}
        taskUuid={taskUuid}
      />

      <TaskValidationBudgetSummary opportunities={opportunities} taskUuid={taskUuid} />

      <TaskSourceInsights taskUuid={taskUuid} />

      <Card className="overflow-hidden rounded-lg py-0 shadow-none">
        <CardHeader className="flex flex-row items-center justify-between gap-4 border-b px-5 py-4">
          <div>
            <CardTitle>推荐排序</CardTitle>
            <CardDescription>报告中可回看本任务生成的全部待验证商机。</CardDescription>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href={`/opportunities?task=${taskUuid}`}>
              <BarChart3 data-icon="inline-start" />
              商机推荐
            </Link>
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50 hover:bg-muted/50">
                <TableHead className="px-5">排序</TableHead>
                <TableHead>商机</TableHead>
                <TableHead>价格带</TableHead>
                <TableHead>风险</TableHead>
                <TableHead className="pr-5 text-right">详情</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {opportunities.map((item) => (
                <TableRow key={item.uuid}>
                  <TableCell className="px-5">
                    <Badge variant="outline">{String(item.rank).padStart(2, "0")}</Badge>
                  </TableCell>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell>{item.price_band}</TableCell>
                  <TableCell>{riskLabels[item.risk_level]}</TableCell>
                  <TableCell className="pr-5 text-right">
                    <Button asChild variant="ghost" size="sm">
                      <Link href={`/opportunities/${item.uuid}`}>
                        打开
                        <ArrowRight data-icon="inline-end" />
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function SummaryBlock({ title, body }: { title: string; body: string }) {
  return (
    <section className="rounded-lg border bg-background p-4">
      <h2 className="font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
    </section>
  );
}

function EmptyReportState({
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
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/research/tasks">
              返回研究任务
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/research/new">新建研究</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
