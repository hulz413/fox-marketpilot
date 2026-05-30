"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, FilePenLine, Play } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  sampleResearchRequests,
  type SampleResearchRequest,
} from "@/features/product-skeleton/data";

import {
  createAndStartResearchTask,
  ResearchRunStartError,
  type CreateResearchTaskInput,
} from "./api";

type DemoResearchSamplesProps = {
  onFill?: (sample: SampleResearchRequest) => void;
};

type LaunchError = {
  message: string;
  taskUuid?: string;
};

function sampleToCreateInput(sample: SampleResearchRequest): CreateResearchTaskInput {
  return sample.payload;
}

export function DemoResearchSamples({ onFill }: DemoResearchSamplesProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [launchError, setLaunchError] = useState<LaunchError | null>(null);

  const launchMutation = useMutation({
    mutationFn: async (sample: SampleResearchRequest) =>
      createAndStartResearchTask(sampleToCreateInput(sample)),
    onMutate: () => {
      setLaunchError(null);
    },
    onSuccess: async (task) => {
      await queryClient.invalidateQueries({ queryKey: ["research-tasks"] });
      router.push(`/research/tasks/${task.uuid}`);
    },
    onError: async (error) => {
      if (error instanceof ResearchRunStartError) {
        await queryClient.invalidateQueries({ queryKey: ["research-tasks"] });
        setLaunchError({
          message: `${error.message} 可以从任务列表或进度页继续启动。`,
          taskUuid: error.task.uuid,
        });
        return;
      }

      setLaunchError({
        message: error instanceof Error ? error.message : "启动示例研究失败，请稍后重试。",
      });
    },
  });

  const pendingSampleId = launchMutation.isPending
    ? launchMutation.variables?.id
    : undefined;

  return (
    <div className="grid gap-4">
      {launchError ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm leading-6 text-destructive">
          <p>{launchError.message}</p>
          {launchError.taskUuid ? (
            <Button asChild variant="link" size="sm" className="mt-1 h-auto px-0">
              <Link href={`/research/tasks/${launchError.taskUuid}`}>
                打开已创建任务
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          ) : null}
        </div>
      ) : null}

      <div className="grid gap-3">
        {sampleResearchRequests.map((sample) => {
          const isPending = pendingSampleId === sample.id;

          return (
            <article
              key={sample.id}
              className="rounded-lg border bg-background p-4"
            >
              <div className="flex flex-wrap gap-2">
                {sample.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
              <h2 className="mt-3 font-semibold">{sample.title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {sample.summary}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {onFill ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={launchMutation.isPending}
                    onClick={() => onFill(sample)}
                  >
                    <FilePenLine data-icon="inline-start" />
                    填入表单
                  </Button>
                ) : null}
                <Button
                  type="button"
                  size="sm"
                  disabled={launchMutation.isPending}
                  onClick={() => launchMutation.mutate(sample)}
                >
                  <Play data-icon="inline-start" />
                  {isPending ? "正在启动" : "启动示例"}
                </Button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
