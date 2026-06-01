"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
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
import { useLanguage } from "@/features/i18n/language-provider";
import {
  sampleResearchRequests,
  type SampleResearchRequest,
} from "@/features/product-skeleton/data";

import {
  createAndStartResearchTask,
  ResearchRunStartError,
} from "./api";
import { DemoResearchSamples } from "./demo-research-samples";

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

function joinList(values: string[]) {
  return values.join("、");
}

function sampleToFormValues(sample: SampleResearchRequest): NewResearchFormValues {
  return {
    brief: sample.payload.brief,
    budget: sample.payload.budget,
    targetChannels: joinList(sample.payload.target_channels),
    preferredCategories: joinList(sample.payload.preferred_categories),
    excludedCategories: joinList(sample.payload.excluded_categories),
    targetAudience: sample.payload.target_audience,
    expectedProfit: sample.payload.expected_profit,
    supplyPreferences: joinList(sample.payload.supply_preferences),
    constraints: sample.payload.constraints,
  };
}

const defaultValues = sampleToFormValues(sampleResearchRequests[0]);

export function NewResearchForm() {
  const { t } = useLanguage();
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
    mutationFn: createAndStartResearchTask,
    onSuccess: async (task) => {
      await queryClient.invalidateQueries({ queryKey: ["research-tasks"] });
      router.push(`/research/tasks/${task.uuid}`);
    },
  });

  function fillWithSample(sample: SampleResearchRequest) {
    const values = sampleToFormValues(sample);

    setValue("brief", values.brief, { shouldDirty: true, shouldValidate: true });
    setValue("budget", values.budget, { shouldDirty: true });
    setValue("targetChannels", values.targetChannels, { shouldDirty: true });
    setValue("preferredCategories", values.preferredCategories, {
      shouldDirty: true,
    });
    setValue("excludedCategories", values.excludedCategories, {
      shouldDirty: true,
    });
    setValue("targetAudience", values.targetAudience, { shouldDirty: true });
    setValue("expectedProfit", values.expectedProfit, { shouldDirty: true });
    setValue("supplyPreferences", values.supplyPreferences, { shouldDirty: true });
    setValue("constraints", values.constraints, { shouldDirty: true });
  }

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
      if (error instanceof ResearchRunStartError) {
        await queryClient.invalidateQueries({ queryKey: ["research-tasks"] });
      }

      setError("root.server", {
        message: error instanceof Error ? error.message : t("创建任务失败，请稍后重试。"),
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
          <CardTitle>{t("研究需求")}</CardTitle>
          <CardDescription>
            {t("提交后会创建真实研究任务，并启动基础商机推荐生成。")}
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
              <FieldLabel htmlFor="research-brief">{t("自然语言需求")}</FieldLabel>
              <FieldDescription>
                {t("用一句话描述预算、渠道、偏好品类和排除条件。")}
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
              <FieldLabel htmlFor="budget">{t("验证预算")}</FieldLabel>
              <Input id="budget" {...register("budget")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="target-channels">{t("目标渠道")}</FieldLabel>
              <Input id="target-channels" {...register("targetChannels")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="target-audience">{t("目标人群")}</FieldLabel>
              <Input id="target-audience" {...register("targetAudience")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="expected-profit">{t("期望利润")}</FieldLabel>
              <Input id="expected-profit" {...register("expectedProfit")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="preferred-categories">{t("偏好品类")}</FieldLabel>
              <Input id="preferred-categories" {...register("preferredCategories")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="excluded-categories">{t("排除品类")}</FieldLabel>
              <Input id="excluded-categories" {...register("excludedCategories")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="supply-preferences">{t("供给来源偏好")}</FieldLabel>
              <Input id="supply-preferences" {...register("supplyPreferences")} />
            </Field>
            <Field>
              <FieldLabel htmlFor="constraints">{t("其他限制条件")}</FieldLabel>
              <Input id="constraints" {...register("constraints")} />
            </Field>
          </FieldGroup>

          <div className="flex flex-wrap gap-2">
            {["轻库存优先", "毛利 30%+", "中文内容平台", "待验证推荐"].map((item) => (
              <Badge key={item} variant="secondary">
                {t(item)}
              </Badge>
            ))}
          </div>

          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={isSubmitting || createTaskMutation.isPending}>
              {isSubmitting || createTaskMutation.isPending
                ? t("正在启动")
                : t("创建并启动")}
              <ArrowRight data-icon="inline-end" />
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push("/research/tasks")}
            >
              {t("我的研究")}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-lg">
        <CardHeader>
          <CardTitle>{t("中文示例需求")}</CardTitle>
          <CardDescription>
            {t("可以先填入表单微调，也可以直接启动一个完整演示任务。")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DemoResearchSamples onFill={fillWithSample} />
        </CardContent>
      </Card>
    </form>
  );
}
