import Link from "next/link";
import { Suspense } from "react";
import { ClipboardList } from "lucide-react";

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
import { OpportunityList } from "@/features/opportunities/opportunity-list";

export default function OpportunitiesPage() {
  return (
    <ProductShell
      active="opportunities"
      title="基础商机推荐"
      description="展示某条研究任务生成的 3-5 个待验证商机草案。"
      action={
        <Button asChild>
          <Link href="/research/tasks">
            研究任务
            <ClipboardList data-icon="inline-end" />
          </Link>
        </Button>
      }
      aside={<ProductSummaryAside />}
    >
      <Suspense fallback={<OpportunityListFallback />}>
        <OpportunityList />
      </Suspense>
    </ProductShell>
  );
}

function OpportunityListFallback() {
  return (
    <Card className="rounded-lg">
      <CardHeader>
        <CardTitle>基础商机推荐</CardTitle>
        <CardDescription>正在准备任务结果视图。</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-28 rounded-md border bg-muted/40" />
      </CardContent>
    </Card>
  );
}
