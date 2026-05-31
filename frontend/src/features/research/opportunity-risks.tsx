"use client";

import { useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, RefreshCcw, ShieldAlert } from "lucide-react";

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
  fetchOpportunityRisks,
  fetchTaskOpportunityRisks,
  type Opportunity,
  type OpportunityRiskLevel,
  type OpportunityRiskReview,
  type OpportunityRiskReviewStatus,
} from "@/features/research/api";

const riskLevelLabels: Record<OpportunityRiskLevel, string> = {
  low: "低",
  medium: "中",
  high: "高",
};

const reviewStatusLabels: Record<OpportunityRiskReviewStatus, string> = {
  derived: "基于现有信息复核",
  fallback: "本地回退生成",
  insufficient_data: "线索不足提示",
};

export function OpportunityRiskPanel({
  opportunityUuid,
}: {
  opportunityUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["opportunity-risks", opportunityUuid],
    queryFn: () => fetchOpportunityRisks(opportunityUuid),
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>风险复核</CardTitle>
          <CardDescription>正在读取风险提示和缓解建议。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <OpportunityRiskEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="风险复核暂不可用，基础商机详情、竞品参考和验证预算仍可继续阅读。"
        title="风险复核读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <OpportunityRiskEmptyState
        description="当前商机还没有风险复核。可先人工排查产品质量、履约、售后、同质化竞争和平台规则，避免把基础推荐当成已核验结论。"
        title="暂无风险复核"
      />
    );
  }

  return (
    <Card id="opportunity-risks" className="rounded-lg">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">风险复核</Badge>
          <Badge variant="outline">待验证</Badge>
          <Badge variant="outline">需要确认</Badge>
        </div>
        <CardTitle>哪些风险要先排查</CardTitle>
        <CardDescription>
          以下内容是风险提示和缓解建议，不代表合规、供应商履约、库存或平台规则已经完成核验。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((risk) => (
          <OpportunityRiskCard key={risk.uuid} risk={risk} />
        ))}
      </CardContent>
    </Card>
  );
}

export function TaskOpportunityRiskSummary({
  opportunities,
  taskUuid,
}: {
  opportunities: Opportunity[];
  taskUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["task-opportunity-risks", taskUuid],
    queryFn: () => fetchTaskOpportunityRisks(taskUuid),
  });
  const opportunityNameByUuid = useMemo(
    () =>
      new Map(
        opportunities.map((opportunity) => [
          opportunity.uuid,
          {
            name: opportunity.name,
            rank: opportunity.rank,
          },
        ]),
      ),
    [opportunities],
  );

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>风险复核摘要</CardTitle>
          <CardDescription>正在读取每个商机的重点风险。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-28 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <OpportunityRiskEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="风险复核暂不可用，报告主体仍保留基础推荐、竞品参考和验证预算。"
        title="风险复核读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <OpportunityRiskEmptyState
        description="当前任务还没有风险复核摘要。基础报告仍可阅读，后续可补充质量、履约、售后、竞争和平台规则风险。"
        title="暂无风险复核摘要"
      />
    );
  }

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <Badge variant="secondary" className="w-fit">
          风险复核
        </Badge>
        <CardTitle>风险复核摘要</CardTitle>
        <CardDescription>
          为每个商机整理优先排查的风险触发原因和缓解建议。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((risk) => {
          const opportunity = opportunityNameByUuid.get(risk.opportunity_uuid);

          return (
            <section
              key={risk.uuid}
              className="rounded-lg border bg-background p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                {opportunity ? (
                  <Badge variant="outline">
                    {String(opportunity.rank).padStart(2, "0")}
                  </Badge>
                ) : null}
                <Badge variant="secondary">
                  风险 {riskLevelLabels[risk.overall_risk_level]}
                </Badge>
                <Badge variant="outline">
                  {reviewStatusLabels[risk.review_status]}
                </Badge>
              </div>
              <h2 className="mt-3 font-semibold">
                {opportunity?.name ?? "商机风险复核"}
              </h2>
              <div className="mt-3 grid gap-2">
                <p className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground">
                  {risk.risk_summary}
                </p>
                <p className="rounded-md bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground">
                  优先排查：{risk.risk_triggers[0]}
                </p>
              </div>
              <Button asChild variant="ghost" size="sm" className="mt-3 px-0">
                <Link href={`/opportunities/${risk.opportunity_uuid}`}>
                  查看完整风险
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            </section>
          );
        })}
      </CardContent>
    </Card>
  );
}

function OpportunityRiskCard({ risk }: { risk: OpportunityRiskReview }) {
  return (
    <article className="rounded-lg border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              风险 {riskLevelLabels[risk.overall_risk_level]}
            </Badge>
            <Badge variant="outline">{reviewStatusLabels[risk.review_status]}</Badge>
            <Badge variant="outline">待验证</Badge>
          </div>
          <h2 className="mt-3 font-semibold">风险提示</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {risk.risk_summary}
          </p>
        </div>
        <ShieldAlert className="size-5 shrink-0 text-primary" aria-hidden="true" />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <InfoBlock label="产品质量" value={risk.quality_risk} />
        <InfoBlock label="发货履约" value={risk.fulfillment_risk} />
        <InfoBlock label="售后风险" value={risk.after_sales_risk} />
        <InfoBlock label="合规风险" value={risk.compliance_risk} />
        <InfoBlock label="库存积压" value={risk.inventory_risk} />
        <InfoBlock label="同质化竞争" value={risk.competition_risk} />
        <InfoBlock label="平台规则" value={risk.platform_risk} />
        <InfoBlock
          label="复核状态"
          value={reviewStatusLabels[risk.review_status]}
        />
      </div>

      <section className="mt-4 rounded-lg border bg-muted/20 p-3">
        <h3 className="text-sm font-semibold">风险触发原因</h3>
        <ul className="mt-3 grid gap-2 text-sm leading-6 text-muted-foreground">
          {risk.risk_triggers.map((trigger) => (
            <li key={trigger} className="rounded-md bg-background px-3 py-2">
              {trigger}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-4 rounded-lg border bg-muted/20 p-3">
        <h3 className="text-sm font-semibold">缓解建议</h3>
        <ul className="mt-3 grid gap-2 text-sm leading-6 text-muted-foreground">
          {risk.mitigation_suggestions.map((suggestion) => (
            <li key={suggestion} className="rounded-md bg-background px-3 py-2">
              {suggestion}
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <section className="rounded-lg border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold leading-6">{value}</p>
    </section>
  );
}

function OpportunityRiskEmptyState({
  action,
  description,
  title,
}: {
  action?: ReactNode;
  description: string;
  title: string;
}) {
  return (
    <Card className="rounded-lg border-dashed">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {action ? <CardContent>{action}</CardContent> : null}
    </Card>
  );
}
