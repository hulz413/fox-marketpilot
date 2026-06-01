import Link from "next/link";
import { BarChart3, ClipboardList } from "lucide-react";

import { Button } from "@/components/ui/button";
import { LocalizedText } from "@/features/i18n/language-provider";
import { ProductShell } from "@/features/product-skeleton/components";
import { ReportSummary } from "@/features/reports/report-summary";

export default async function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <ProductShell
      active="tasks"
      title="基础报告"
      description="基于已生成商机结果汇总推荐排序、风险等级和下一步行动摘要。"
      action={
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/research/tasks">
              <ClipboardList data-icon="inline-start" />
              <LocalizedText source="我的研究" />
            </Link>
          </Button>
          <Button asChild>
            <Link href={id === "demo-report" ? "/opportunities" : `/opportunities?task=${id}`}>
              <LocalizedText source="商机推荐" />
              <BarChart3 data-icon="inline-end" />
            </Link>
          </Button>
        </div>
      }
    >
      <ReportSummary taskUuid={id} />
    </ProductShell>
  );
}
