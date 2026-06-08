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
      active="tasks"
      title="商机详情"
      description="集中查看单个待验证商机是什么、为什么推荐、适合谁、风险高低和下一步做什么。"
    >
      <OpportunityDetail opportunityUuid={id} />
    </ProductShell>
  );
}
