import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ProductShell } from "@/features/product-skeleton/components";
import { NewResearchForm } from "@/features/research/new-research-form";

export default function NewResearchPage() {
  return (
    <ProductShell
      active="new"
      title="新建研究"
      description="描述你想尝试的小生意方向，后续任务闭环会在这里创建真实研究任务。"
      action={
        <Button asChild>
          <Link href="/research/tasks">
            查看任务
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      }
    >
      <NewResearchForm />
    </ProductShell>
  );
}
