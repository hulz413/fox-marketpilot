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
  | "collect_research_sources"
  | "generate_demand_insights"
  | "generate_supply_candidates"
  | "generate_competitor_references"
  | "estimate_validation_budgets"
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

export type AgentRunEventStatus = "running" | "completed" | "failed";

export type AgentRunEvent = {
  uuid: string;
  run_id: string;
  trace_id: string | null;
  stage: string;
  status: AgentRunEventStatus;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  error_summary: string | null;
};

export type ResearchProgressAction =
  | "start"
  | "rerun"
  | "view_opportunities"
  | "view_report"
  | "open_trace"
  | "back_to_tasks";

export type ResearchProgress = {
  task: ResearchTask;
  run_id: string | null;
  trace_id: string | null;
  trace_url: string | null;
  status: ResearchTaskStatus;
  current_stage: ResearchTaskStage;
  failure_reason: string | null;
  events: AgentRunEvent[];
  available_actions: ResearchProgressAction[];
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

export type ResearchSourceType =
  | "demand"
  | "supply"
  | "competitor"
  | "risk"
  | "general";
export type SourceSupportLevel = "weak" | "medium" | "strong";

export type ResearchSource = {
  uuid: string;
  research_task_uuid: string;
  opportunity_uuid: string | null;
  source_type: ResearchSourceType;
  title: string;
  url: string;
  summary: string;
  snippet: string;
  publisher: string | null;
  score: number | null;
  query: string | null;
  linked_claim: string;
  support_level: SourceSupportLevel;
  collected_at: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type DemandInsightSourceStatus = "linked" | "no_sources" | "fallback";

export type DemandInsightSourceSummary = {
  uuid: string;
  source_type: ResearchSourceType;
  title: string;
  url: string;
  summary: string;
  support_level: SourceSupportLevel;
  relevance_note: string;
};

export type OpportunityDemandInsight = {
  uuid: string;
  research_task_uuid: string;
  opportunity_uuid: string;
  summary: string;
  audience_profile: string;
  use_cases: string[];
  purchase_motivations: string[];
  content_angles: string[];
  trend_signals: string[];
  seasonality_notes: string;
  source_status: DemandInsightSourceStatus;
  sources: DemandInsightSourceSummary[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type SupplyCandidateSourceStatus = "linked" | "no_sources" | "fallback";

export type SupplyCandidateSourceSummary = {
  uuid: string;
  source_type: ResearchSourceType;
  title: string;
  url: string;
  summary: string;
  support_level: SourceSupportLevel;
  relevance_note: string;
};

export type OpportunitySupplyCandidate = {
  uuid: string;
  research_task_uuid: string;
  opportunity_uuid: string;
  rank: number;
  candidate_name: string;
  supply_market: string;
  search_keywords: string[];
  price_range: string;
  minimum_order_quantity: string;
  specification_notes: string[];
  supplier_questions: string[];
  recommendation_note: string;
  source_status: SupplyCandidateSourceStatus;
  sources: SupplyCandidateSourceSummary[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type CompetitorReferenceSourceStatus =
  | "linked"
  | "no_sources"
  | "fallback";
export type HomogenizationLevel = "low" | "medium" | "high";

export type CompetitorReferenceSourceSummary = {
  uuid: string;
  source_type: ResearchSourceType;
  title: string;
  url: string;
  summary: string;
  support_level: SourceSupportLevel;
  relevance_note: string;
};

export type OpportunityCompetitorReference = {
  uuid: string;
  research_task_uuid: string;
  opportunity_uuid: string;
  rank: number;
  reference_name: string;
  reference_market: string;
  price_range: string;
  common_selling_points: string[];
  homogenization_level: HomogenizationLevel;
  differentiation_angles: string[];
  reference_note: string;
  source_status: CompetitorReferenceSourceStatus;
  sources: CompetitorReferenceSourceSummary[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type ValidationBudgetEstimateStatus =
  | "derived"
  | "fallback"
  | "insufficient_data";

export type OpportunityValidationBudget = {
  uuid: string;
  research_task_uuid: string;
  opportunity_uuid: string;
  estimated_unit_cost: string;
  estimated_selling_price: string;
  rough_gross_margin: string;
  first_batch_quantity: string;
  first_batch_budget: string;
  key_assumptions: string[];
  calculation_note: string;
  estimate_status: ValidationBudgetEstimateStatus;
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

export class ResearchRunStartError extends Error {
  task: ResearchTask;

  constructor(message: string, task: ResearchTask) {
    super(message);
    this.name = "ResearchRunStartError";
    this.task = task;
  }
}

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

async function safeFetch(input: RequestInfo | URL, init?: RequestInit) {
  try {
    return await fetch(input, init);
  } catch {
    throw new Error("无法连接后端服务，请确认 API 服务和本地依赖已启动。");
  }
}

export async function createResearchTask(
  input: CreateResearchTaskInput,
): Promise<ResearchTask> {
  const payload = createResearchTaskSchema.parse(input);
  const response = await safeFetch(buildApiUrl("/api/v1/research-tasks"), {
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

export async function createAndStartResearchTask(
  input: CreateResearchTaskInput,
): Promise<ResearchTask> {
  const task = await createResearchTask(input);

  try {
    return await startResearchRun(task.uuid);
  } catch (error) {
    const message =
      error instanceof Error
        ? `任务已创建，但启动研究失败：${error.message}`
        : "任务已创建，但启动研究失败，请稍后从任务列表继续启动。";

    throw new ResearchRunStartError(message, task);
  }
}

export async function fetchResearchTasks(): Promise<ResearchTask[]> {
  const response = await safeFetch(buildApiUrl("/api/v1/research-tasks"), {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchResearchTask(taskUuid: string): Promise<ResearchTask> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchResearchProgress(
  taskUuid: string,
): Promise<ResearchProgress> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}/progress`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function startResearchRun(taskUuid: string): Promise<ResearchTask> {
  const response = await safeFetch(
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
  const response = await safeFetch(
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
  const response = await safeFetch(
    buildApiUrl(`/api/v1/opportunities/${opportunityUuid}`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchTaskSources(
  taskUuid: string,
): Promise<ResearchSource[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}/sources`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchOpportunitySources(
  opportunityUuid: string,
): Promise<ResearchSource[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/opportunities/${opportunityUuid}/sources`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchTaskDemandInsights(
  taskUuid: string,
): Promise<OpportunityDemandInsight[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}/demand-insights`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchOpportunityDemandInsight(
  opportunityUuid: string,
): Promise<OpportunityDemandInsight | null> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/opportunities/${opportunityUuid}/demand-insight`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchTaskSupplyCandidates(
  taskUuid: string,
): Promise<OpportunitySupplyCandidate[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}/supply-candidates`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchOpportunitySupplyCandidates(
  opportunityUuid: string,
): Promise<OpportunitySupplyCandidate[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/opportunities/${opportunityUuid}/supply-candidates`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchTaskCompetitorReferences(
  taskUuid: string,
): Promise<OpportunityCompetitorReference[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}/competitor-references`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchOpportunityCompetitorReferences(
  opportunityUuid: string,
): Promise<OpportunityCompetitorReference[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/opportunities/${opportunityUuid}/competitor-references`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchTaskValidationBudgets(
  taskUuid: string,
): Promise<OpportunityValidationBudget[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/research-tasks/${taskUuid}/validation-budgets`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchOpportunityValidationBudgets(
  opportunityUuid: string,
): Promise<OpportunityValidationBudget[]> {
  const response = await safeFetch(
    buildApiUrl(`/api/v1/opportunities/${opportunityUuid}/validation-budgets`),
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}
