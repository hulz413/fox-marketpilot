import { z } from "zod";

import { buildApiUrl } from "@/lib/api/client";

export type ResearchTaskStatus =
  | "created"
  | "queued"
  | "running"
  | "completed"
  | "failed";
export type ResearchTaskStage =
  | "intake"
  | "queued"
  | "normalize_intake"
  | "generate_opportunities"
  | "validate_results"
  | "persist_results"
  | "completed"
  | "failed";

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
  trace_url: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type OpportunityRiskLevel = "low" | "medium" | "high";

export type Opportunity = {
  uuid: string;
  research_task_uuid: string;
  rank: number;
  name: string;
  product_direction: string;
  target_audience: string;
  recommendation_reason: string;
  suitable_channels: string[];
  price_band: string;
  rough_margin: string;
  risk_level: OpportunityRiskLevel;
  priority_label: string;
  next_step_summary: string;
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
    cache: "no-store",
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
  const response = await fetch(buildApiUrl("/api/v1/research-tasks"), {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchResearchTask(taskUuid: string): Promise<ResearchTask> {
  const response = await fetch(buildApiUrl(`/api/v1/research-tasks/${taskUuid}`), {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function startResearchRun(taskUuid: string): Promise<ResearchTask> {
  const response = await fetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}/runs`),
    {
      method: "POST",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchTaskOpportunities(
  taskUuid: string,
): Promise<Opportunity[]> {
  const response = await fetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}/opportunities`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchOpportunity(
  opportunityUuid: string,
): Promise<Opportunity> {
  const response = await fetch(buildApiUrl(`/api/v1/opportunities/${opportunityUuid}`), {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}
