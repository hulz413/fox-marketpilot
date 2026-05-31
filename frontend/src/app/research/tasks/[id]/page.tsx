import Link from "next/link";
import { ClipboardList } from "lucide-react";

import { Button } from "@/components/ui/button";
import { LocalizedText } from "@/features/i18n/language-provider";
import { ProductShell } from "@/features/product-skeleton/components";
import { ResearchProgressView } from "@/features/research/research-progress";

export default async function ResearchTaskProgressPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <ProductShell
      active="tasks"
      title="研究进度"
      description="查看当前任务运行到哪一步、哪些阶段已完成，以及失败或完成后的下一步操作。"
      action={
        <Button asChild>
          <Link href="/research/tasks">
            <ClipboardList data-icon="inline-start" />
            <LocalizedText source="研究任务" />
          </Link>
        </Button>
      }
    >
      <ResearchProgressView taskUuid={id} />
    </ProductShell>
  );
}
