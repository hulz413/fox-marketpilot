import Link from "next/link";
import { ArrowLeft, FileText } from "lucide-react";

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
  ProductShell,
  ProductSummaryAside,
} from "@/features/product-skeleton/components";
import { opportunities } from "@/features/product-skeleton/data";

export function generateStaticParams() {
  return opportunities.map((item) => ({ id: item.id }));
}

export default async function OpportunityDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const opportunity = opportunities.find((item) => item.id === id) ?? opportunities[0];

  return (
    <ProductShell
      active="opportunities"
      title="商机详情"
      description="集中查看单个商机是什么、为什么推荐、适合谁、风险高低和下一步做什么。"
      action={
        <Button asChild>
          <Link href="/reports/demo-report">
            查看报告
            <FileText data-icon="inline-end" />
          </Link>
        </Button>
      }
      aside={<ProductSummaryAside />}
    >
      <div className="grid gap-5">
        <div>
          <Button asChild variant="ghost" size="sm">
            <Link href="/opportunities">
              <ArrowLeft data-icon="inline-start" />
              返回商机推荐
            </Link>
          </Button>
        </div>

        <Card className="rounded-lg">
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{opportunity.rank}</Badge>
              <Badge className="rounded-full bg-primary/10 text-primary">
                {opportunity.priority}
              </Badge>
            </div>
            <CardTitle className="text-2xl">{opportunity.name}</CardTitle>
            <CardDescription>{opportunity.direction}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5">
            <div className="grid gap-3 md:grid-cols-3">
              <InfoBlock label="目标人群" value={opportunity.audience} />
              <InfoBlock label="适合渠道" value={opportunity.channel} />
              <InfoBlock label="价格带" value={opportunity.price} />
              <InfoBlock label="利润空间" value={opportunity.margin} />
              <InfoBlock label="验证预算" value={opportunity.budget} />
              <InfoBlock label="风险等级" value={opportunity.risk} />
            </div>
            <Card className="rounded-lg bg-background shadow-none">
              <CardHeader>
                <CardTitle>推荐理由</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-muted-foreground">
                  {opportunity.reason}
                </p>
              </CardContent>
            </Card>
            <Card className="rounded-lg bg-background shadow-none">
              <CardHeader>
                <CardTitle>下一步建议</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-muted-foreground">
                  {opportunity.next}
                </p>
              </CardContent>
            </Card>
          </CardContent>
        </Card>
      </div>
    </ProductShell>
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
