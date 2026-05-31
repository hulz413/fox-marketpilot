"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, FileText, RefreshCcw } from "lucide-react";

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
import { OpportunitySourceInsights } from "@/features/research/source-insights";
import {
  fetchOpportunity,
  type Opportunity,
  type OpportunityRiskLevel,
} from "@/features/research/api";
import { OpportunityCompetitorReferencePanel } from "@/features/research/competitor-references";
import { OpportunityDemandInsightPanel } from "@/features/research/demand-insights";
import { OpportunitySupplyCandidatePanel } from "@/features/research/supply-candidates";
import { OpportunityValidationBudgetPanel } from "@/features/research/validation-budgets";

const riskLabels: Record<OpportunityRiskLevel, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

export function OpportunityDetail({ opportunityUuid }: { opportunityUuid: string }) {
  const {
    data: opportunity,
    error,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["opportunity", opportunityUuid],
    queryFn: () => fetchOpportunity(opportunityUuid),
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>商机详情</CardTitle>
          <CardDescription>正在读取基础推荐详情。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-40 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error || !opportunity) {
    return (
      <Card className="rounded-lg border-destructive/30">
        <CardHeader>
          <CardTitle>商机详情读取失败</CardTitle>
          <CardDescription>
            {error instanceof Error ? error.message : "无法读取商机详情。"}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
          <Button asChild variant="ghost">
            <Link href="/research/tasks">返回任务</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return <OpportunityDetailContent opportunity={opportunity} />;
}

function OpportunityDetailContent({ opportunity }: { opportunity: Opportunity }) {
  return (
    <div className="grid gap-5">
      <TaskContextNavigation
        active="opportunities"
        sourcesHref="#sources"
        taskUuid={opportunity.research_task_uuid}
      />
      <div className="flex flex-wrap gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link href={`/opportunities?task=${opportunity.research_task_uuid}`}>
            <ArrowLeft data-icon="inline-start" />
            返回基础推荐
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link href={`/reports/${opportunity.research_task_uuid}`}>
            <FileText data-icon="inline-start" />
            基础报告
          </Link>
        </Button>
      </div>

      <Card className="rounded-lg">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{String(opportunity.rank).padStart(2, "0")}</Badge>
            <Badge className="rounded-full bg-primary/10 text-primary">
              {opportunity.priority_label}
            </Badge>
            <Badge variant="outline">风险 {riskLabels[opportunity.risk_level]}</Badge>
            <Badge variant="secondary">待验证</Badge>
          </div>
          <CardTitle className="text-2xl">{opportunity.name}</CardTitle>
          <CardDescription className="leading-6">
            {opportunity.product_direction}。先围绕小批量内容和询单数据验证，不把当前推荐视为已证明结论。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5">
          <div className="grid gap-3 md:grid-cols-3">
            <InfoBlock label="目标人群" value={opportunity.target_audience} />
            <InfoBlock
              label="适合渠道"
              value={opportunity.suitable_channels.join("、")}
            />
            <InfoBlock label="价格带" value={opportunity.price_band} />
            <InfoBlock label="利润空间" value={opportunity.rough_margin} />
            <InfoBlock label="推荐优先级" value={opportunity.priority_label} />
            <InfoBlock label="风险等级" value={riskLabels[opportunity.risk_level]} />
          </div>
          <section className="rounded-lg border bg-background p-4">
            <h2 className="font-semibold">为什么推荐</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {opportunity.recommendation_reason}
            </p>
          </section>
          <section className="rounded-lg border bg-primary/5 p-4">
            <h2 className="font-semibold text-primary">下一步验证动作</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {opportunity.next_step_summary}
            </p>
          </section>
        </CardContent>
      </Card>
      <OpportunityDemandInsightPanel opportunityUuid={opportunity.uuid} />
      <OpportunitySupplyCandidatePanel opportunityUuid={opportunity.uuid} />
      <OpportunityCompetitorReferencePanel opportunityUuid={opportunity.uuid} />
      <OpportunityValidationBudgetPanel opportunityUuid={opportunity.uuid} />
      <OpportunitySourceInsights opportunityUuid={opportunity.uuid} />
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 text-sm font-semibold">{value}</p>
    </div>
  );
}
