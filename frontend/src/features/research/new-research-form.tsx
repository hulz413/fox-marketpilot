"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

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
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { samplePrompts } from "@/features/product-skeleton/data";

import { createResearchTask, startResearchRun } from "./api";

const formSchema = z.object({
  brief: z.string().trim().min(1, "请填写自然语言需求。").max(2000),
  budget: z.string().trim().max(120).optional(),
  targetChannels: z.string().trim().max(240).optional(),
  preferredCategories: z.string().trim().max(240).optional(),
  excludedCategories: z.string().trim().max(240).optional(),
  targetAudience: z.string().trim().max(240).optional(),
  expectedProfit: z.string().trim().max(120).optional(),
  supplyPreferences: z.string().trim().max(240).optional(),
  constraints: z.string().trim().max(1000).optional(),
});

type NewResearchFormValues = z.infer<typeof formSchema>;

const defaultValues: NewResearchFormValues = {
  brief: "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。",
  budget: "5000 元以内",
  targetChannels: "小红书种草",
  preferredCategories: "轻库存、内容种草",
  excludedCategories: "食品、电子产品",
  targetAudience: "通勤白领、租房办公人群",
  expectedProfit: "毛利 30%+",
  supplyPreferences: "1688、公开供给市场",
  constraints: "首批验证预算小，不囤货。",
};

function splitList(value?: string) {
  if (!value) {
    return [];
  }

  return value
    .split(/[,，、\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function optionalText(value?: string) {
  const trimmed = value?.trim();

  return trimmed ? trimmed : undefined;
}

export function NewResearchForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<NewResearchFormValues>({ defaultValues });

  const createTaskMutation = useMutation({
    mutationFn: async (input: Parameters<typeof createResearchTask>[0]) => {
      const task = await createResearchTask(input);

      return startResearchRun(task.uuid);
    },
    onSuccess: async (task) => {
      await queryClient.invalidateQueries({ queryKey: ["research-tasks"] });
      router.push(`/research/tasks/${task.uuid}`);
    },
  });

  const sampleButtons = useMemo(
    () =>
      samplePrompts.map((prompt) => (
        <Button
          key={prompt}
          type="button"
          variant="outline"
          className="h-auto justify-start whitespace-normal px-3 py-2 text-left"
          onClick={() => {
            setValue("brief", prompt, { shouldDirty: true, shouldValidate: true });
          }}
        >
          {prompt}
        </Button>
      )),
    [setValue],
  );

  async function onSubmit(values: NewResearchFormValues) {
    const parsed = formSchema.safeParse(values);

    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        const fieldName = issue.path[0] as keyof NewResearchFormValues | undefined;

        if (fieldName) {
          setError(fieldName, { message: issue.message });
        }
      }

      return;
    }

    try {
      await createTaskMutation.mutateAsync({
        brief: parsed.data.brief,
        budget: optionalText(parsed.data.budget),
        target_channels: splitList(parsed.data.targetChannels),
        preferred_categories: splitList(parsed.data.preferredCategories),
        excluded_categories: splitList(parsed.data.excludedCategories),
        target_audience: optionalText(parsed.data.targetAudience),
        expected_profit: optionalText(parsed.data.expectedProfit),
        supply_preferences: splitList(parsed.data.supplyPreferences),
        constraints: optionalText(parsed.data.constraints),
      });
    } catch (error) {
      setError("root.server", {
        message: error instanceof Error ? error.message : "创建任务失败，请稍后重试。",
      });
    }
  }

  return (
    <form className="grid gap-5" onSubmit={handleSubmit(onSubmit)}>
      <Card className="rounded-lg">
        <CardHeader>
          <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Sparkles className="size-5" aria-hidden="true" />
          </div>
          <CardTitle>研究需求</CardTitle>
          <CardDescription>
            提交后会创建真实研究任务，并启动基础商机推荐生成。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {errors.root?.server ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {errors.root.server.message}
            </div>
          ) : null}

          <FieldGroup className="gap-4">
            <Field data-invalid={Boolean(errors.brief)}>
              <FieldLabel htmlFor="research-brief">自然语言需求</FieldLabel>
              <FieldDescription>
                用一句话描述预算、渠道、偏好品类和排除条件。
              </FieldDescription>
              <Textarea
                id="research-brief"
                className="min-h-32 resize-none"
                aria-invalid={Boolean(errors.brief)}
                {...register("brief", { required: "请填写自然语言需求。" })}
              />
              <FieldError errors={[errors.brief]} />
            </Field>
          </FieldGroup>

          <FieldGroup className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="budget">验证预算</FieldLabel>
              <Input id="budget" {...register("budget")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="target-channels">目标渠道</FieldLabel>
              <Input id="target-channels" {...register("targetChannels")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="target-audience">目标人群</FieldLabel>
              <Input id="target-audience" {...register("targetAudience")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="expected-profit">期望利润</FieldLabel>
              <Input id="expected-profit" {...register("expectedProfit")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="preferred-categories">偏好品类</FieldLabel>
              <Input id="preferred-categories" {...register("preferredCategories")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="excluded-categories">排除品类</FieldLabel>
              <Input id="excluded-categories" {...register("excludedCategories")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="supply-preferences">供给来源偏好</FieldLabel>
              <Input id="supply-preferences" {...register("supplyPreferences")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="constraints">其他限制条件</FieldLabel>
              <Input id="constraints" {...register("constraints")} />
            </Field>
          </FieldGroup>

          <div className="flex flex-wrap gap-2">
            {["轻库存优先", "毛利 30%+", "中文内容平台", "待验证推荐"].map((item) => (
              <Badge key={item} variant="secondary">
                {item}
              </Badge>
            ))}
          </div>

          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={isSubmitting || createTaskMutation.isPending}>
              {isSubmitting || createTaskMutation.isPending
                ? "正在启动"
                : "创建并启动"}
              <ArrowRight data-icon="inline-end" />
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push("/research/tasks")}
            >
              查看任务
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>中文示例需求</CardTitle>
          <CardDescription>点击示例可以填入自然语言需求。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">{sampleButtons}</CardContent>
      </Card>
    </form>
  );
}
