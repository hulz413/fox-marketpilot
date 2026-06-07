import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type {
  OpportunityActionPlan,
  OpportunityCompetitorReference,
  OpportunityDemandInsight,
  OpportunityRiskLevel,
  OpportunityRiskReview,
  OpportunitySupplyCandidate,
  OpportunityValidationBudget,
  PublicReportShare,
  ResearchSource,
  SourceSupportLevel,
} from "@/features/research/api";
import { formatDateTime } from "@/lib/datetime";

const riskLabels: Record<OpportunityRiskLevel, string> = {
  low: "低风险",
  medium: "中风险",
  high: "高风险",
};

const supportLabels: Record<SourceSupportLevel, string> = {
  weak: "弱支撑",
  medium: "中等支撑",
  strong: "强支撑",
};

export function SharedReportView({ share }: { share: PublicReportShare }) {
  const snapshot = share.snapshot;
  const opportunities = [...snapshot.opportunities].sort((a, b) => a.rank - b.rank);
  const demandByOpportunity = groupOneByOpportunity(snapshot.demand_insights);
  const supplyByOpportunity = groupManyByOpportunity(snapshot.supply_candidates);
  const competitorByOpportunity = groupManyByOpportunity(
    snapshot.competitor_references,
  );
  const budgetByOpportunity = groupManyByOpportunity(snapshot.validation_budgets);
  const riskByOpportunity = groupManyByOpportunity(snapshot.opportunity_risks);
  const actionByOpportunity = groupManyByOpportunity(snapshot.action_plans);
  const sourcesByOpportunity = groupManyByOpportunity(
    snapshot.sources.filter((source) => source.opportunity_uuid),
  );
  const taskSources = snapshot.sources.filter((source) => !source.opportunity_uuid);

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto grid max-w-6xl gap-5 px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">只读分享报告</Badge>
            <Badge variant="outline">{formatDateTime(snapshot.shared_at)}</Badge>
          </div>
          <div className="grid gap-3">
            <h1 className="max-w-4xl break-words text-3xl font-semibold tracking-normal text-foreground md:text-4xl">
              {share.title}
            </h1>
            <p className="max-w-4xl break-words text-sm leading-6 text-muted-foreground md:text-base">
              {snapshot.task.brief}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="推荐商机" value={`${snapshot.summary.opportunity_count} 个`} />
            <Metric label="公开来源" value={`${snapshot.summary.source_count} 条`} />
            <Metric
              label="优先验证"
              value={snapshot.summary.top_opportunity_name ?? "待确认"}
            />
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-5 px-4 py-6 sm:px-6 lg:px-8">
        <TaskSnapshotCard share={share} />

        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>推荐排序</CardTitle>
            <CardDescription>所有结论均为待验证判断，适合先做小成本验证。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {opportunities.map((opportunity) => (
              <div
                key={opportunity.uuid}
                className="grid gap-3 rounded-md border p-4 md:grid-cols-[72px_1fr_160px]"
              >
                <Badge variant="outline" className="h-fit">
                  {String(opportunity.rank).padStart(2, "0")}
                </Badge>
                <div className="min-w-0">
                  <h2 className="break-words font-semibold">{opportunity.name}</h2>
                  <p className="mt-1 break-words text-sm leading-6 text-muted-foreground">
                    {opportunity.product_direction}
                  </p>
                </div>
                <div className="min-w-0 text-sm text-muted-foreground">
                  <p>{opportunity.price_band}</p>
                  <p>{riskLabels[opportunity.risk_level]}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <section className="grid gap-5">
          {opportunities.map((opportunity) => (
            <Card key={opportunity.uuid} className="rounded-lg">
              <CardHeader>
                <Badge variant="secondary" className="w-fit">
                  推荐 {String(opportunity.rank).padStart(2, "0")}
                </Badge>
                <CardTitle className="break-words text-2xl">
                  {opportunity.name}
                </CardTitle>
                <CardDescription className="break-words">
                  {opportunity.recommendation_reason}
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-5">
                <div className="grid gap-3 md:grid-cols-3">
                  <DetailBlock title="目标人群" body={opportunity.target_audience} />
                  <DetailBlock title="价格与毛利" body={`${opportunity.price_band}；${opportunity.rough_margin}`} />
                  <DetailBlock title="下一步" body={opportunity.next_step_summary} />
                </div>

                <ListBlock title="适合渠道" items={opportunity.suitable_channels} />

                <DemandInsightBlock insight={demandByOpportunity[opportunity.uuid]} />
                <SupplyCandidateBlock
                  candidates={supplyByOpportunity[opportunity.uuid] ?? []}
                />
                <CompetitorReferenceBlock
                  references={competitorByOpportunity[opportunity.uuid] ?? []}
                />
                <ValidationBudgetBlock
                  budgets={budgetByOpportunity[opportunity.uuid] ?? []}
                />
                <RiskReviewBlock risks={riskByOpportunity[opportunity.uuid] ?? []} />
                <ActionPlanBlock plans={actionByOpportunity[opportunity.uuid] ?? []} />
                <SourceList
                  title="关联来源线索"
                  sources={sourcesByOpportunity[opportunity.uuid] ?? []}
                />
              </CardContent>
            </Card>
          ))}
        </section>

        <SourceList title="任务级来源线索" sources={taskSources} framed />

        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>谨慎边界</CardTitle>
            <CardDescription>这份报告用于帮助筛选方向，不替代真实经营验证。</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-2 text-sm leading-6 text-muted-foreground">
              {snapshot.boundary_notes.map((note) => (
                <li key={note} className="break-words">
                  {note}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

function TaskSnapshotCard({ share }: { share: PublicReportShare }) {
  const task = share.snapshot.task;

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle>任务摘要</CardTitle>
        <CardDescription>分享时固定的研究输入和阅读时间。</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2">
        <DetailBlock title="预算" body={task.budget ?? "未填写"} />
        <DetailBlock title="目标人群" body={task.target_audience ?? "未填写"} />
        <DetailBlock title="目标渠道" body={formatTextList(task.target_channels)} />
        <DetailBlock title="供给偏好" body={formatTextList(task.supply_preferences)} />
        <DetailBlock title="偏好品类" body={formatTextList(task.preferred_categories)} />
        <DetailBlock title="排除品类" body={formatTextList(task.excluded_categories)} />
        <DetailBlock title="期望利润" body={task.expected_profit ?? "未填写"} />
        <DetailBlock title="其他限制" body={task.constraints ?? "未填写"} />
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-lg border bg-background p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-lg font-semibold">{value}</p>
    </div>
  );
}

function DetailBlock({ title, body }: { title: string; body: string }) {
  return (
    <section className="min-w-0 rounded-md border bg-background p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 break-words text-sm leading-6 text-muted-foreground">
        {body}
      </p>
    </section>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  if (!items.length) {
    return null;
  }

  return (
    <section className="grid gap-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <Badge key={item} variant="outline" className="max-w-full whitespace-normal">
            {item}
          </Badge>
        ))}
      </div>
    </section>
  );
}

function DemandInsightBlock({
  insight,
}: {
  insight: OpportunityDemandInsight | undefined;
}) {
  if (!insight) {
    return <EmptyBlock title="需求洞察" />;
  }

  return (
    <section className="grid gap-3">
      <SectionTitle title="需求洞察" status={insight.source_status} />
      <DetailBlock title="需求摘要" body={insight.summary} />
      <div className="grid gap-3 md:grid-cols-2">
        <DetailBlock title="人群画像" body={insight.audience_profile} />
        <DetailBlock title="季节性备注" body={insight.seasonality_notes} />
      </div>
      <ListBlock title="使用场景" items={insight.use_cases} />
      <ListBlock title="购买动机" items={insight.purchase_motivations} />
      <ListBlock title="内容角度" items={insight.content_angles} />
      <ListBlock title="趋势信号" items={insight.trend_signals} />
    </section>
  );
}

function SupplyCandidateBlock({
  candidates,
}: {
  candidates: OpportunitySupplyCandidate[];
}) {
  if (!candidates.length) {
    return <EmptyBlock title="货源候选" />;
  }

  return (
    <section className="grid gap-3">
      <SectionTitle title="货源候选" />
      {candidates.map((candidate) => (
        <div key={candidate.uuid} className="grid gap-3 rounded-md border p-4">
          <h3 className="break-words font-semibold">{candidate.candidate_name}</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <DetailBlock title="供给市场" body={candidate.supply_market} />
            <DetailBlock title="价格区间" body={candidate.price_range} />
            <DetailBlock title="起订量" body={candidate.minimum_order_quantity} />
          </div>
          <DetailBlock title="推荐说明" body={candidate.recommendation_note} />
          <ListBlock title="搜索关键词" items={candidate.search_keywords} />
          <ListBlock title="规格备注" items={candidate.specification_notes} />
          <ListBlock title="供应商问题" items={candidate.supplier_questions} />
        </div>
      ))}
    </section>
  );
}

function CompetitorReferenceBlock({
  references,
}: {
  references: OpportunityCompetitorReference[];
}) {
  if (!references.length) {
    return <EmptyBlock title="竞品参考" />;
  }

  return (
    <section className="grid gap-3">
      <SectionTitle title="竞品参考" />
      {references.map((reference) => (
        <div key={reference.uuid} className="grid gap-3 rounded-md border p-4">
          <h3 className="break-words font-semibold">{reference.reference_name}</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <DetailBlock title="参考市场" body={reference.reference_market} />
            <DetailBlock title="售价区间" body={reference.price_range} />
            <DetailBlock title="同质化程度" body={reference.homogenization_level} />
          </div>
          <DetailBlock title="参考备注" body={reference.reference_note} />
          <ListBlock title="常见卖点" items={reference.common_selling_points} />
          <ListBlock title="差异化角度" items={reference.differentiation_angles} />
        </div>
      ))}
    </section>
  );
}

function ValidationBudgetBlock({
  budgets,
}: {
  budgets: OpportunityValidationBudget[];
}) {
  if (!budgets.length) {
    return <EmptyBlock title="验证预算" />;
  }

  return (
    <section className="grid gap-3">
      <SectionTitle title="验证预算" />
      {budgets.map((budget) => (
        <div key={budget.uuid} className="grid gap-3 rounded-md border p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <DetailBlock title="预估拿货成本" body={budget.estimated_unit_cost} />
            <DetailBlock title="预估售价" body={budget.estimated_selling_price} />
            <DetailBlock title="粗略毛利" body={budget.rough_gross_margin} />
            <DetailBlock title="首批数量" body={budget.first_batch_quantity} />
            <DetailBlock title="首批预算" body={budget.first_batch_budget} />
            <DetailBlock title="估算状态" body={budget.estimate_status} />
          </div>
          <DetailBlock title="估算说明" body={budget.calculation_note} />
          <ListBlock title="关键假设" items={budget.key_assumptions} />
        </div>
      ))}
    </section>
  );
}

function RiskReviewBlock({ risks }: { risks: OpportunityRiskReview[] }) {
  if (!risks.length) {
    return <EmptyBlock title="风险复核" />;
  }

  return (
    <section className="grid gap-3">
      <SectionTitle title="风险复核" />
      {risks.map((risk) => (
        <div key={risk.uuid} className="grid gap-3 rounded-md border p-4">
          <Badge variant="outline" className="w-fit">
            {riskLabels[risk.overall_risk_level]}
          </Badge>
          <DetailBlock title="风险摘要" body={risk.risk_summary} />
          <div className="grid gap-3 md:grid-cols-2">
            <DetailBlock title="质量风险" body={risk.quality_risk} />
            <DetailBlock title="履约风险" body={risk.fulfillment_risk} />
            <DetailBlock title="售后风险" body={risk.after_sales_risk} />
            <DetailBlock title="合规风险" body={risk.compliance_risk} />
            <DetailBlock title="库存风险" body={risk.inventory_risk} />
            <DetailBlock title="竞争风险" body={risk.competition_risk} />
            <DetailBlock title="平台风险" body={risk.platform_risk} />
          </div>
          <ListBlock title="风险触发点" items={risk.risk_triggers} />
          <ListBlock title="缓解建议" items={risk.mitigation_suggestions} />
        </div>
      ))}
    </section>
  );
}

function ActionPlanBlock({ plans }: { plans: OpportunityActionPlan[] }) {
  if (!plans.length) {
    return <EmptyBlock title="行动计划" />;
  }

  return (
    <section className="grid gap-3">
      <SectionTitle title="行动计划" />
      {plans.map((plan) => (
        <div key={plan.uuid} className="grid gap-3 rounded-md border p-4">
          <DetailBlock title="验证目标" body={plan.validation_goal} />
          <div className="grid gap-3 md:grid-cols-2">
            <DetailBlock title="首批计划" body={plan.first_batch_plan} />
            <DetailBlock title="验证方式" body={plan.product_validation_method} />
          </div>
          <ListBlock title="内容角度" items={plan.content_angles} />
          <ListBlock title="标题建议" items={plan.title_suggestions} />
          <ListBlock title="卖点建议" items={plan.selling_point_suggestions} />
          <DetailBlock title="询盘话术" body={plan.supplier_inquiry_script} />
          <ListBlock title="上架前检查" items={plan.prelaunch_checklist} />
        </div>
      ))}
    </section>
  );
}

function SourceList({
  title,
  sources,
  framed = false,
}: {
  title: string;
  sources: ResearchSource[];
  framed?: boolean;
}) {
  if (!sources.length) {
    if (!framed) {
      return <EmptyBlock title={title} />;
    }

    return (
      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>暂无可展示的公开来源线索。</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const sourceLinks = (
    <div className="grid gap-3">
      {sources.map((source) => (
        <a
          key={source.uuid}
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="grid gap-2 rounded-md border p-4 text-sm transition-colors hover:bg-accent"
        >
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Badge variant="outline">{source.source_type}</Badge>
            <Badge variant="secondary">{supportLabels[source.support_level]}</Badge>
            <ExternalLink className="size-4 text-muted-foreground" />
          </div>
          <h3 className="break-words font-semibold">{source.title}</h3>
          <p className="break-words leading-6 text-muted-foreground">
            {source.summary}
          </p>
        </a>
      ))}
    </div>
  );

  if (!framed) {
    return (
      <section className="grid gap-3">
        <div>
          <h3 className="text-base font-semibold">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            来源仅作为初步参考，仍需人工核验。
          </p>
        </div>
        {sourceLinks}
      </section>
    );
  }

  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>来源仅作为初步参考，仍需人工核验。</CardDescription>
      </CardHeader>
      <CardContent>{sourceLinks}</CardContent>
    </Card>
  );
}

function SectionTitle({ title, status }: { title: string; status?: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <h3 className="text-base font-semibold">{title}</h3>
      {status ? <Badge variant="outline">{status}</Badge> : null}
    </div>
  );
}

function EmptyBlock({ title }: { title: string }) {
  return (
    <section className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
      {title} 暂无可展示内容，不影响报告主体阅读。
    </section>
  );
}

function groupOneByOpportunity<T extends { opportunity_uuid: string }>(items: T[]) {
  return items.reduce<Record<string, T>>((grouped, item) => {
    grouped[item.opportunity_uuid] = item;
    return grouped;
  }, {});
}

function groupManyByOpportunity<T extends { opportunity_uuid: string | null }>(
  items: T[],
) {
  return items.reduce<Record<string, T[]>>((grouped, item) => {
    if (!item.opportunity_uuid) {
      return grouped;
    }

    grouped[item.opportunity_uuid] = grouped[item.opportunity_uuid] ?? [];
    grouped[item.opportunity_uuid].push(item);
    return grouped;
  }, {});
}

function formatTextList(items: string[]) {
  return items.length ? items.join("、") : "未填写";
}
