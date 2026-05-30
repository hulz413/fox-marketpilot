import Link from "next/link";
import { ClipboardList } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ProductShell } from "@/features/product-skeleton/components";
import { OpportunityDetail } from "@/features/opportunities/opportunity-detail";

export default async function OpportunityDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <ProductShell
      active="opportunities"
      title="商机详情"
      description="集中查看单个待验证商机是什么、为什么推荐、适合谁、风险高低和下一步做什么。"
      action={
        <Button asChild>
          <Link href="/research/tasks">
            研究任务
            <ClipboardList data-icon="inline-end" />
          </Link>
        </Button>
      }
    >
      <OpportunityDetail opportunityUuid={id} />
    </ProductShell>
  );
}
