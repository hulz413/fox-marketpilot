import { z } from "zod";

import { buildApiUrl } from "@/lib/api/client";

export type ResearchTaskStatus = "created";
export type ResearchTaskStage = "intake";

export type ResearchTask = {
  uuid: string;
  title: string;
  brief: string;
  budget: string | null;
  target_channels: string[];
  preferred_categories: string[];
  excluded_categories: string[];
  target_audience: string | null;
  expected_profit: string | null;
  supply_preferences: string[];
  constraints: string | null;
  status: ResearchTaskStatus;
  current_stage: ResearchTaskStage;
  run_id: string | null;
  trace_id: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export const createResearchTaskSchema = z.object({
  title: z.string().trim().max(160).optional(),
  brief: z.string().trim().min(1, "请填写自然语言需求。").max(2000),
  budget: z.string().trim().max(120).optional(),
  target_channels: z.array(z.string().trim()).default([]),
  preferred_categories: z.array(z.string().trim()).default([]),
  excluded_categories: z.array(z.string().trim()).default([]),
  target_audience: z.string().trim().max(240).optional(),
  expected_profit: z.string().trim().max(120).optional(),
  supply_preferences: z.array(z.string().trim()).default([]),
  constraints: z.string().trim().max(1000).optional(),
});

export type CreateResearchTaskInput = z.infer<typeof createResearchTaskSchema>;

async function readErrorMessage(response: Response) {
  try {
    const body = await response.json();

    if (typeof body.detail === "string") {
      return body.detail;
    }

    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return body.detail[0].msg;
    }
  } catch {
    return "请求失败，请稍后重试。";
  }

  return "请求失败，请稍后重试。";
}

export async function createResearchTask(
  input: CreateResearchTaskInput,
): Promise<ResearchTask> {
  const payload = createResearchTaskSchema.parse(input);
  const response = await fetch(buildApiUrl("/api/v1/research-tasks"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchResearchTasks(): Promise<ResearchTask[]> {
  const response = await fetch(buildApiUrl("/api/v1/research-tasks"));

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchResearchTask(taskUuid: string): Promise<ResearchTask> {
  const response = await fetch(buildApiUrl(`/api/v1/research-tasks/${taskUuid}`));

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}
