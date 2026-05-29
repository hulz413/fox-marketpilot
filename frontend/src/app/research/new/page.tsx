import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

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
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  ProductShell,
  ProductSummaryAside,
} from "@/features/product-skeleton/components";
import { samplePrompts } from "@/features/product-skeleton/data";

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
      aside={<ProductSummaryAside />}
    >
      <div className="grid gap-5">
        <Card className="rounded-lg">
          <CardHeader>
            <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="size-5" aria-hidden="true" />
            </div>
            <CardTitle>研究需求</CardTitle>
            <CardDescription>
              用于演示任务创建入口，提交后进入研究任务列表。
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <FieldGroup className="gap-4">
              <Field>
                <FieldLabel htmlFor="research-brief">自然语言需求</FieldLabel>
                <FieldDescription>
                  用一句话描述预算、渠道、偏好品类和排除条件。
                </FieldDescription>
              <Textarea
                id="research-brief"
                className="min-h-32 resize-none"
                defaultValue="预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。"
              />
              </Field>
            </FieldGroup>
            <FieldGroup className="grid gap-4 md:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="budget">验证预算</FieldLabel>
                <Input id="budget" defaultValue="5000 元以内" />
              </Field>
              <Field>
                <FieldLabel htmlFor="channel">目标渠道</FieldLabel>
                <Input id="channel" defaultValue="小红书种草" />
              </Field>
              <Field>
                <FieldLabel htmlFor="audience">目标人群</FieldLabel>
                <Input id="audience" defaultValue="通勤白领、租房办公人群" />
              </Field>
              <Field>
                <FieldLabel htmlFor="constraints">限制条件</FieldLabel>
                <Input id="constraints" defaultValue="不做食品、不做电子产品" />
              </Field>
            </FieldGroup>
            <div className="flex flex-wrap gap-2">
              {["轻库存优先", "毛利 30%+", "中文内容平台", "公开来源"].map((item) => (
                <Badge key={item} variant="secondary">
                  {item}
                </Badge>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href="/research/tasks">创建演示任务</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/opportunities">查看商机推荐</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-lg">
          <CardHeader>
            <CardTitle>中文示例需求</CardTitle>
            <CardDescription>首次空状态中也会展示这些示例。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {samplePrompts.map((prompt) => (
              <div key={prompt} className="rounded-md border bg-background p-3 text-sm">
                {prompt}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </ProductShell>
  );
}
