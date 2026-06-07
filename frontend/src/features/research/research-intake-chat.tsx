"use client";

import { useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Compass,
  LoaderCircle,
  MessageCircle,
  RefreshCcw,
  RotateCcw,
  Rocket,
  Send,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useLanguage } from "@/features/i18n/language-provider";
import { sampleResearchRequests } from "@/features/product-skeleton/data";
import { cn } from "@/lib/utils";

import {
  confirmResearchIntakeConversation,
  createResearchIntakeConversation,
  fetchResearchIntakeConversation,
  sendResearchIntakeMessage,
  updateResearchIntakeRequirements,
  type ResearchIntakeConversation,
  type ResearchIntakeDraft,
  type ResearchIntakeMessage,
} from "./api";

const draftFields: Array<{
  key: keyof ResearchIntakeDraft;
  label: string;
}> = [
  { key: "brief", label: "自然语言需求" },
  { key: "budget", label: "验证预算" },
  { key: "target_channels", label: "目标渠道" },
  { key: "target_audience", label: "目标人群" },
  { key: "preferred_categories", label: "偏好品类" },
  { key: "excluded_categories", label: "排除品类" },
  { key: "supply_preferences", label: "供给来源偏好" },
  { key: "expected_profit", label: "期望利润" },
  { key: "constraints", label: "其他限制条件" },
];

const missingFieldLabels: Record<string, string> = {
  brief: "自然语言需求",
  budget: "验证预算",
  target_channels: "目标渠道",
  excluded_categories: "排除品类",
  constraints: "限制条件",
};

function draftValue(value: ResearchIntakeDraft[keyof ResearchIntakeDraft]) {
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join("、") : "未指定";
  }

  return value || "未指定";
}

const INTAKE_CONVERSATION_STORAGE_KEY =
  "marketpilot.researchIntakeConversationUuid";

function hasDraftValue(value: ResearchIntakeDraft[keyof ResearchIntakeDraft]) {
  return Array.isArray(value) ? value.length > 0 : Boolean(value);
}

function hasDraftContent(draft: ResearchIntakeDraft) {
  return draftFields.some((field) => hasDraftValue(draft[field.key]));
}

function readStoredConversationUuid() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.sessionStorage.getItem(INTAKE_CONVERSATION_STORAGE_KEY);
  } catch {
    return null;
  }
}

function rememberActiveConversation(conversation: ResearchIntakeConversation) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    if (conversation.status === "active") {
      window.sessionStorage.setItem(
        INTAKE_CONVERSATION_STORAGE_KEY,
        conversation.uuid,
      );
      return;
    }

    window.sessionStorage.removeItem(INTAKE_CONVERSATION_STORAGE_KEY);
  } catch {
    // Session restore is best-effort.
  }
}

function forgetActiveConversation() {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.sessionStorage.removeItem(INTAKE_CONVERSATION_STORAGE_KEY);
  } catch {
    // Session restore is best-effort.
  }
}

export function ResearchIntakeChat({
  onEditDraft,
}: {
  onEditDraft?: (draft: ResearchIntakeDraft) => void;
}) {
  const { t } = useLanguage();
  const router = useRouter();
  const [conversation, setConversation] =
    useState<ResearchIntakeConversation | null>(null);
  const [message, setMessage] = useState("");
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRestoringConversation, setIsRestoringConversation] = useState(false);
  const messagesViewportRef = useRef<HTMLDivElement | null>(null);

  const starterPrompts = useMemo(
    () => sampleResearchRequests.map((sample) => sample.payload.brief),
    [],
  );

  const messageMutation = useMutation({
    mutationFn: async (content: string) => {
      if (conversation) {
        return sendResearchIntakeMessage(conversation.uuid, content);
      }

      return createResearchIntakeConversation({ message: content });
    },
    onSuccess: (nextConversation) => {
      setConversation(nextConversation);
      setMessage("");
      setError(nextConversation.error_summary);
      rememberActiveConversation(nextConversation);
    },
    onError: (mutationError) => {
      setError(
        mutationError instanceof Error
          ? mutationError.message
          : t("消息发送失败，请稍后重试。"),
      );
    },
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!conversation) {
        throw new Error(t("请先发送一条研究需求。"));
      }

      return updateResearchIntakeRequirements(conversation.uuid);
    },
    onSuccess: (nextConversation) => {
      setConversation(nextConversation);
      setError(nextConversation.error_summary);
      rememberActiveConversation(nextConversation);
    },
    onError: (mutationError) => {
      setError(
        mutationError instanceof Error
          ? mutationError.message
          : t("需求更新失败，请稍后重试。"),
      );
    },
  });

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (!conversation) {
        throw new Error(t("请先发送一条研究需求。"));
      }

      return confirmResearchIntakeConversation(conversation.uuid);
    },
    onSuccess: (result) => {
      setConversation(result.conversation);
      rememberActiveConversation(result.conversation);

      if (result.research_task_uuid) {
        router.push(`/research/tasks/${result.research_task_uuid}`);
        return;
      }

      setError(result.error_summary ?? t("任务已创建，但暂时无法打开进度页。"));
    },
    onError: (mutationError) => {
      setError(
        mutationError instanceof Error
          ? mutationError.message
          : t("确认启动失败，请稍后重试。"),
      );
    },
  });

  const isSending = messageMutation.isPending;
  const isUpdating = updateMutation.isPending;
  const isConfirming = confirmMutation.isPending;
  const isBusy =
    isRestoringConversation || isSending || isUpdating || isConfirming;
  const hasUserMessages = Boolean(
    conversation?.messages.some((item) => item.role === "user"),
  );
  const canCreate = Boolean(conversation?.can_create_task);
  const canEditDraft = Boolean(
    onEditDraft && conversation && hasDraftContent(conversation.draft),
  );
  const hasVisibleMessages = Boolean(
    conversation?.messages.length || pendingMessage,
  );
  const latestAssistantMessageUuid = useMemo(() => {
    const messages = conversation?.messages ?? [];

    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === "assistant") {
        return messages[index].uuid;
      }
    }

    return null;
  }, [conversation?.messages]);

  useEffect(() => {
    const storedUuid = readStoredConversationUuid();
    if (!storedUuid) {
      return;
    }

    let ignore = false;
    queueMicrotask(() => {
      if (!ignore) {
        setIsRestoringConversation(true);
      }
    });
    fetchResearchIntakeConversation(storedUuid)
      .then((nextConversation) => {
        if (ignore) {
          return;
        }

        if (nextConversation.status === "active") {
          setConversation(nextConversation);
          setError(nextConversation.error_summary);
          rememberActiveConversation(nextConversation);
          return;
        }

        rememberActiveConversation(nextConversation);
      })
      .catch(() => {
        if (typeof window === "undefined") {
          return;
        }

        try {
          window.sessionStorage.removeItem(INTAKE_CONVERSATION_STORAGE_KEY);
        } catch {
          // Session restore is best-effort.
        }
      })
      .finally(() => {
        if (!ignore) {
          setIsRestoringConversation(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!hasVisibleMessages) {
      return;
    }

    const viewport = messagesViewportRef.current;
    viewport?.scrollTo({ top: viewport.scrollHeight });
  }, [conversation?.messages.length, hasVisibleMessages, pendingMessage]);

  async function submitMessage(content: string) {
    const trimmed = content.trim();
    if (
      !trimmed ||
      isRestoringConversation ||
      isSending ||
      isUpdating ||
      isConfirming
    ) {
      return;
    }

    setError(null);
    setMessage("");
    setPendingMessage(trimmed);

    try {
      await messageMutation.mutateAsync(trimmed);
    } catch {
      setMessage(trimmed);
    } finally {
      setPendingMessage(null);
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(message);
  }

  function handleResetConversation() {
    setConversation(null);
    setMessage("");
    setPendingMessage(null);
    setError(null);
    forgetActiveConversation();
    messageMutation.reset();
    updateMutation.reset();
    confirmMutation.reset();
  }

  function handleMessageKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key !== "Enter" ||
      event.shiftKey ||
      event.nativeEvent.isComposing
    ) {
      return;
    }

    event.preventDefault();
    void submitMessage(message);
  }

  return (
    <div className="grid min-h-0 gap-5 lg:h-full lg:overflow-y-auto lg:[scrollbar-width:none] lg:[&::-webkit-scrollbar]:hidden xl:grid-cols-[minmax(0,1fr)_360px] xl:overflow-y-visible">
      <Card className="min-h-0 min-w-0 rounded-lg lg:h-full">
        <CardHeader className="grid-cols-[auto_minmax(0,1fr)] grid-rows-[auto] items-center gap-x-3 gap-y-0">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <MessageCircle className="size-5" aria-hidden="true" />
          </div>
          <div className="grid min-w-0 gap-1">
            <CardTitle>{t("聊天对齐需求")}</CardTitle>
            <CardDescription>
              {t("把模糊想法整理为可启动的研究任务草稿。")}
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col gap-4">
          <div
            ref={messagesViewportRef}
            className="grid min-h-0 flex-1 content-start gap-3 overflow-y-auto rounded-lg border bg-card p-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
            {hasVisibleMessages ? (
              <>
                {conversation?.messages.map((item) => {
                  const showSuggestions =
                    item.role === "assistant" &&
                    item.uuid === latestAssistantMessageUuid &&
                    !pendingMessage;

                  return (
                    <ChatMessage
                      key={item.uuid}
                      message={item}
                      suggestedReplies={
                        showSuggestions ? item.suggested_replies : []
                      }
                      suggestionsDisabled={
                        isRestoringConversation ||
                        isSending ||
                        isUpdating ||
                        isConfirming
                      }
                      onSuggestionSelect={submitMessage}
                    />
                  );
                })}
                {pendingMessage ? (
                  <>
                    <ChatBubble role="user" content={pendingMessage} />
                    <ChatThinkingMessage />
                  </>
                ) : null}
              </>
            ) : (
              <div className="grid gap-3">
                <p className="text-sm leading-6 text-muted-foreground">
                  {isRestoringConversation
                    ? t("正在恢复上次聊天...")
                    : t(
                        "可以先发几句想法，商机顾问会追问补充信息；信息足够后点击「更新需求」整理研究草稿。",
                      )}
                </p>
                {!isRestoringConversation ? (
                  <div className="flex flex-wrap gap-2">
                    {starterPrompts.map((prompt) => (
                      <Button
                        key={prompt}
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-auto max-w-full whitespace-normal text-left"
                        disabled={isSending || isUpdating}
                        onClick={() => void submitMessage(prompt)}
                      >
                        {t(prompt)}
                      </Button>
                    ))}
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {error ? (
            <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          ) : null}

          <form className="grid shrink-0 gap-3" onSubmit={handleSubmit}>
            <Textarea
              className="min-h-24 resize-none focus-visible:border-input focus-visible:ring-0"
              value={message}
              placeholder={t("例如：我想用 5000 元以内做小红书轻库存选品，不做食品。")}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={handleMessageKeyDown}
              disabled={
                isRestoringConversation || isSending || isUpdating || isConfirming
              }
            />
            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="submit"
                disabled={!message.trim() || isBusy}
              >
                {t("发送")}
                <Send data-icon="inline-end" />
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={!hasUserMessages || isBusy}
                onClick={() => updateMutation.mutate()}
              >
                {isUpdating ? t("更新中") : t("更新需求")}
                {isUpdating ? (
                  <LoaderCircle className="animate-spin" data-icon="inline-end" />
                ) : (
                  <RefreshCcw data-icon="inline-end" />
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="ml-auto bg-secondary/60 hover:bg-secondary"
                disabled={isBusy}
                onClick={handleResetConversation}
              >
                {t("重置")}
                <RotateCcw data-icon="inline-end" />
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <aside className="min-h-0 min-w-0 self-stretch">
        <Card className="h-full min-h-0 rounded-lg">
          <CardHeader className="shrink-0">
            <CardTitle>{t("研究草稿")}</CardTitle>
            <CardDescription>
              {t("确认后会创建真实研究任务并进入进度页。")}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid min-h-0 flex-1 gap-4 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <ReadinessSummary conversation={conversation} />
            <Button
              type="button"
              disabled={
                !canCreate || isRestoringConversation || isUpdating || isConfirming
              }
              onClick={() => confirmMutation.mutate()}
            >
              {isConfirming ? t("正在启动") : t("确认并启动研究")}
              <Rocket data-icon="inline-end" />
            </Button>
            {onEditDraft ? (
              <Button
                type="button"
                variant="outline"
                disabled={
                  !canEditDraft ||
                  isRestoringConversation ||
                  isUpdating ||
                  isConfirming
                }
                onClick={() => {
                  if (conversation) {
                    onEditDraft(conversation.draft);
                  }
                }}
              >
                {t("带入表单编辑")}
                <ClipboardList data-icon="inline-end" />
              </Button>
            ) : null}
            {conversation?.research_task_uuid ? (
              <Button type="button" variant="outline" asChild>
                <Link href={`/research/tasks/${conversation.research_task_uuid}`}>
                  {t("打开已创建任务")}
                  <ClipboardList data-icon="inline-end" />
                </Link>
              </Button>
            ) : null}
            <div className="grid gap-3">
              {draftFields.map((field) => (
                <div key={field.key} className="grid gap-1 rounded-md border p-3">
                  <span className="text-xs text-muted-foreground">
                    {t(field.label)}
                  </span>
                  <span className="break-words text-sm font-medium leading-6">
                    {draftValue(conversation?.draft[field.key] ?? null)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </aside>
    </div>
  );
}

function ChatMessage({
  message,
  suggestedReplies,
  suggestionsDisabled,
  onSuggestionSelect,
}: {
  message: ResearchIntakeMessage;
  suggestedReplies: string[];
  suggestionsDisabled: boolean;
  onSuggestionSelect: (reply: string) => void;
}) {
  return (
    <ChatBubble
      role={message.role}
      content={message.content}
      suggestedReplies={suggestedReplies}
      suggestionsDisabled={suggestionsDisabled}
      onSuggestionSelect={onSuggestionSelect}
    />
  );
}

function ChatBubble({
  role,
  content,
  suggestedReplies = [],
  suggestionsDisabled = false,
  onSuggestionSelect,
}: {
  role: ResearchIntakeMessage["role"];
  content: string;
  suggestedReplies?: string[];
  suggestionsDisabled?: boolean;
  onSuggestionSelect?: (reply: string) => void;
}) {
  const { t } = useLanguage();
  const isUser = role === "user";
  const senderLabel = isUser ? t("你") : t("商机顾问");
  const showSuggestions =
    !isUser && suggestedReplies.length > 0 && Boolean(onSuggestionSelect);

  return (
    <div
      className={cn(
        "flex items-start gap-2",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {!isUser ? <ChatAvatar sender="assistant" /> : null}
      <div className="grid max-w-[min(560px,72%)] gap-2">
        <div
          aria-label={senderLabel}
          className={cn(
            "rounded-lg border px-3 py-2 text-sm leading-6 shadow-sm",
            isUser
              ? "border-primary/10 bg-secondary text-secondary-foreground"
              : "bg-card text-foreground",
          )}
        >
          <span className="sr-only">{senderLabel}</span>
          <p className="whitespace-pre-wrap break-words">{content}</p>
        </div>
        {showSuggestions ? (
          <div className="flex flex-wrap gap-2" aria-label={t("可选回复")}>
            {suggestedReplies.map((reply) => (
              <Button
                key={reply}
                type="button"
                variant="outline"
                size="xs"
                className="rounded-full bg-secondary/60 hover:bg-secondary"
                disabled={suggestionsDisabled}
                onClick={() => onSuggestionSelect?.(reply)}
              >
                {reply}
              </Button>
            ))}
          </div>
        ) : null}
      </div>
      {isUser ? <ChatAvatar sender="user" /> : null}
    </div>
  );
}

function ChatThinkingMessage() {
  const { t } = useLanguage();

  return (
    <div className="flex items-start justify-start gap-2" aria-live="polite">
      <ChatAvatar sender="assistant" />
      <div className="flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm leading-6 text-muted-foreground shadow-sm">
        <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
        <span>{t("思考中")}</span>
      </div>
    </div>
  );
}

function ChatAvatar({ sender }: { sender: "assistant" | "user" }) {
  if (sender === "user") {
    return (
      <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <UserRound className="size-5" aria-hidden="true" />
      </div>
    );
  }

  return (
    <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
      <Compass className="size-5" aria-hidden="true" />
    </div>
  );
}

function ReadinessSummary({
  conversation,
}: {
  conversation: ResearchIntakeConversation | null;
}) {
  const { t } = useLanguage();

  if (!conversation) {
    return (
      <div className="rounded-md border bg-muted/30 p-3 text-sm leading-6 text-muted-foreground">
        {t("发送消息后，商机顾问会先追问；点击「更新需求」后会显示草稿完整度。")}
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={conversation.can_create_task ? "default" : "secondary"}>
          {conversation.can_create_task ? t("可启动") : t("需补充")}
        </Badge>
        {conversation.status === "converted" ? (
          <Badge variant="outline">{t("已创建任务")}</Badge>
        ) : null}
      </div>

      {conversation.can_create_task ? (
        <div className="flex items-start gap-2 rounded-md border border-primary/20 bg-primary/5 p-3 text-sm leading-6 text-primary">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{t("草稿已经足够启动一次基础研究，仍可继续补充条件。")}</span>
        </div>
      ) : null}

      {conversation.missing_fields.length > 0 ? (
        <div className="grid gap-2 rounded-md border p-3">
          <span className="text-sm font-medium">{t("缺失条件")}</span>
          <div className="flex flex-wrap gap-2">
            {conversation.missing_fields.map((field) => (
              <Badge key={field} variant="secondary">
                {t(missingFieldLabels[field] ?? field)}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {conversation.assumptions.length > 0 ? (
        <div className="grid gap-2 rounded-md border p-3">
          <span className="text-sm font-medium">{t("默认假设")}</span>
          <ul className="grid gap-1 text-sm leading-6 text-muted-foreground">
            {conversation.assumptions.map((assumption) => (
              <li key={assumption}>{t(assumption)}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
