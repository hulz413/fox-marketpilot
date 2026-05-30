"use client";

import { useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, ExternalLink, RefreshCcw } from "lucide-react";

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
  fetchOpportunityDemandInsight,
  fetchTaskDemandInsights,
  type DemandInsightSourceStatus,
  type Opportunity,
  type OpportunityDemandInsight,
} from "@/features/research/api";

const sourceStatusLabels: Record<DemandInsightSourceStatus, string> = {
  linked: "已关联公开线索",
  no_sources: "暂无直接来源",
  fallback: "本地回退生成",
};

export function OpportunityDemandInsightPanel({
  opportunityUuid,
}: {
  opportunityUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["opportunity-demand-insight", opportunityUuid],
    queryFn: () => fetchOpportunityDemandInsight(opportunityUuid),
  });

  if (isLoading) {
    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>需求洞察</CardTitle>
          <CardDescription>正在读取需求判断拆解。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <InsightEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="需求洞察暂不可用，基础商机详情仍可作为待验证草案阅读。"
        title="需求洞察读取失败"
      />
    );
  }

  if (!data) {
    return (
      <InsightEmptyState
        description="当前商机还没有需求洞察，建议先结合公开线索和小批量反馈继续验证。"
        title="暂无需求洞察"
      />
    );
  }

  return <DemandInsightCard insight={data} />;
}

export function TaskDemandInsightSummary({
  opportunities,
  taskUuid,
}: {
  opportunities: Opportunity[];
  taskUuid: string;
}) {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ["task-demand-insights", taskUuid],
    queryFn: () => fetchTaskDemandInsights(taskUuid),
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
          <CardTitle>需求洞察摘要</CardTitle>
          <CardDescription>正在读取每个商机的需求判断。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-28 rounded-md border bg-muted/40" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <InsightEmptyState
        action={
          <Button type="button" variant="outline" onClick={() => void refetch()}>
            <RefreshCcw data-icon="inline-start" />
            重新加载
          </Button>
        }
        description="需求洞察暂不可用，报告主体仍保留基础推荐和公开线索。"
        title="需求洞察读取失败"
      />
    );
  }

  if (!data?.length) {
    return (
      <InsightEmptyState
        description="当前任务还没有需求洞察。基础报告仍是待验证推荐摘要，后续可结合公开资料继续补强。"
        title="暂无需求洞察摘要"
      />
    );
  }

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <Badge variant="secondary" className="w-fit">
          初步参考
        </Badge>
        <CardTitle>需求洞察摘要</CardTitle>
        <CardDescription>
          拆解每个商机可能对应的人群、场景和购买动机，仍需用公开资料和小批量反馈验证。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {data.map((insight) => {
          const opportunity = opportunityNameByUuid.get(insight.opportunity_uuid);

          return (
            <section key={insight.uuid} className="rounded-lg border bg-background p-4">
              <div className="flex flex-wrap items-center gap-2">
                {opportunity ? (
                  <Badge variant="outline">
                    {String(opportunity.rank).padStart(2, "0")}
                  </Badge>
                ) : null}
                <Badge variant="secondary">
                  {sourceStatusLabels[insight.source_status]}
                </Badge>
              </div>
              <h2 className="mt-3 font-semibold">
                {opportunity?.name ?? "商机需求洞察"}
              </h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {insight.summary}
              </p>
              <Button asChild variant="ghost" size="sm" className="mt-3 px-0">
                <Link href={`/opportunities/${insight.opportunity_uuid}`}>
                  查看完整洞察
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

function DemandInsightCard({ insight }: { insight: OpportunityDemandInsight }) {
  return (
    <Card id="demand-insights" className="rounded-lg">
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">需求洞察</Badge>
          <Badge variant="outline">{sourceStatusLabels[insight.source_status]}</Badge>
          <Badge variant="outline">待验证</Badge>
        </div>
        <CardTitle>为什么可能有需求</CardTitle>
        <CardDescription>
          以下判断是结合任务输入和公开线索形成的初步参考，仍需继续验证。
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        <section className="rounded-lg border bg-background p-4">
          <h2 className="font-semibold">需求摘要</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {insight.summary}
          </p>
        </section>
        <section className="rounded-lg border bg-background p-4">
          <h2 className="font-semibold">目标人群画像</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {insight.audience_profile}
          </p>
        </section>
        <div className="grid gap-4 md:grid-cols-2">
          <InsightList title="使用场景" items={insight.use_cases} />
          <InsightList title="购买动机" items={insight.purchase_motivations} />
          <InsightList title="内容种草点" items={insight.content_angles} />
          <InsightList title="趋势信号" items={insight.trend_signals} />
        </div>
        <section className="rounded-lg border bg-background p-4">
          <h2 className="font-semibold">季节性因素</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {insight.seasonality_notes}
          </p>
        </section>
        <DemandInsightSources insight={insight} />
      </CardContent>
    </Card>
  );
}

function InsightList({ items, title }: { items: string[]; title: string }) {
  return (
    <section className="rounded-lg border bg-background p-4">
      <h2 className="font-semibold">{title}</h2>
      <ul className="mt-3 grid gap-2 text-sm leading-6 text-muted-foreground">
        {items.map((item) => (
          <li key={item} className="rounded-md bg-muted/40 px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function DemandInsightSources({ insight }: { insight: OpportunityDemandInsight }) {
  if (!insight.sources.length) {
    return (
      <section className="rounded-lg border border-dashed bg-background p-4">
        <h2 className="font-semibold">关联来源</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          暂无直接关联来源。当前需求洞察仍是待验证判断，建议后续补充公开线索或小批量反馈。
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-background p-4">
      <h2 className="font-semibold">关联来源</h2>
      <div className="mt-3 grid gap-3">
        {insight.sources.map((source) => (
          <a
            key={source.uuid}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border p-3 text-sm transition-colors hover:border-primary/40 hover:bg-primary/5"
          >
            <span className="flex items-start justify-between gap-3 font-medium">
              <span className="break-words">{source.title}</span>
              <ExternalLink className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            </span>
            <span className="mt-2 block leading-6 text-muted-foreground">
              {source.relevance_note}
            </span>
          </a>
        ))}
      </div>
    </section>
  );
}

function InsightEmptyState({
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
