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
import { LocalizedText } from "@/features/i18n/language-provider";
import { ProductShell } from "@/features/product-skeleton/components";
import { OpportunityList } from "@/features/opportunities/opportunity-list";

export default function OpportunitiesPage() {
  return (
    <ProductShell
      active="tasks"
      title="基础商机推荐"
      description="展示某条研究任务生成的 3-5 个待验证商机草案。"
      action={
        <Button asChild>
          <Link href="/research/tasks">
            <LocalizedText source="我的研究" />
            <ClipboardList data-icon="inline-end" />
          </Link>
        </Button>
      }
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
        <CardTitle>
          <LocalizedText source="基础商机推荐" />
        </CardTitle>
        <CardDescription>
          <LocalizedText source="正在准备任务结果视图。" />
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-28 rounded-md border bg-muted/40" />
      </CardContent>
    </Card>
  );
}
