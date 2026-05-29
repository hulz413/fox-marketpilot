import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  ClipboardList,
  FileText,
  History,
  Sparkles,
} from "lucide-react";

export type NavKey = "new" | "tasks" | "opportunities" | "report" | "history";

export type ProductNavItem = {
  key: NavKey;
  label: string;
  href: string;
  icon: LucideIcon;
};

export const productNavItems: ProductNavItem[] = [
  { key: "new", label: "新建研究", href: "/research/new", icon: Sparkles },
  { key: "tasks", label: "研究任务", href: "/research/tasks", icon: ClipboardList },
  { key: "opportunities", label: "商机推荐", href: "/opportunities", icon: BarChart3 },
  { key: "report", label: "最终报告", href: "/reports/demo-report", icon: FileText },
  { key: "history", label: "研究历史", href: "/history", icon: History },
];

export const samplePrompts = [
  "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。",
  "找适合社群团购的宠物清洁用品，首批验证预算控制在 3000 元内。",
  "面向租房办公人群，寻找低库存、可内容种草的桌面小物。",
];

export const researchStages = [
  { label: "收集来源", detail: "整理中文内容平台和供给市场公开信息", progress: 86 },
  { label: "分析供给", detail: "估算价格带、起订量和需要确认的问题", progress: 64 },
  { label: "生成推荐", detail: "合并需求、供给、竞品和风险判断", progress: 48 },
  { label: "生成报告", detail: "整理商机排序、详情摘要和行动建议", progress: 24 },
];

export const researchTasks = [
  {
    id: "task-demo-0528",
    title: "5000 元以内，小红书种草，不做食品和电子产品",
    createdAt: "2026-05-28 22:40",
    status: "运行中",
    stage: "分析供给",
    summary: "已收集 8 条公开来源，正在合并供给候选。",
    primaryHref: "/opportunities",
    reportHref: "/reports/demo-report",
  },
  {
    id: "task-demo-0527",
    title: "适合社群团购的宠物清洁用品",
    createdAt: "2026-05-27 19:16",
    status: "已完成",
    stage: "报告已生成",
    summary: "生成 4 个商机，推荐优先验证宠物外出清洁包。",
    primaryHref: "/opportunities",
    reportHref: "/reports/demo-report",
  },
  {
    id: "task-demo-0526",
    title: "低客单价露营配件验证",
    createdAt: "2026-05-26 14:08",
    status: "失败",
    stage: "收集来源",
    summary: "公开来源不足，建议放宽品类或补充目标渠道。",
    primaryHref: "/research/new",
    reportHref: "/reports/demo-report",
  },
];

export const opportunities = [
  {
    id: "opp-coffee",
    rank: "01",
    name: "低糖便携咖啡液",
    direction: "办公室补给与通勤便携",
    audience: "通勤白领",
    channel: "小红书 + 私域",
    price: "¥39-59/盒",
    margin: "38-45%",
    budget: "¥4,800",
    risk: "中",
    priority: "优先验证",
    reason: "内容种草门槛低，轻量试单成本可控，适合用小批量库存验证。",
    next: "先用 30 盒小批量测试收藏率、询单率和售后反馈，再决定是否扩大到私域组合装。",
  },
  {
    id: "opp-desk-light",
    rank: "02",
    name: "桌面收纳氛围灯",
    direction: "桌搭收纳与氛围改造",
    audience: "租房办公人群",
    channel: "小红书图文 + 短视频",
    price: "¥59-89/件",
    margin: "32-40%",
    budget: "¥4,200",
    risk: "低",
    priority: "备选验证",
    reason: "视觉表达强，适合做桌搭内容，但需要确认外观同质化和电池认证问题。",
    next: "先拍 3 组桌面改造内容测试收藏率，再询 3 家供应商确认打样周期。",
  },
  {
    id: "opp-pet-kit",
    rank: "03",
    name: "宠物外出清洁包",
    direction: "新手养宠出门场景",
    audience: "新手养宠家庭",
    channel: "社群团购 + 小红书",
    price: "¥29-49/套",
    margin: "35-42%",
    budget: "¥3,600",
    risk: "中",
    priority: "观察验证",
    reason: "组合包可重排，适合社群试单，但售后和材质反馈需要提前控制。",
    next: "首批 50 套记录复购和投诉点，同时准备替换耗材方案。",
  },
];

export const reportSections = [
  {
    title: "推荐结论",
    content: "优先验证低糖便携咖啡液，次选桌面收纳氛围灯，宠物外出清洁包作为社群方向观察。",
  },
  {
    title: "风险摘要",
    content: "主要风险来自质量稳定性、同质化竞争和供应商履约。MVP 阶段只做小批量验证，不建议囤货。",
  },
  {
    title: "下一步行动",
    content: "用 14 天完成供应商询价、内容脚本测试、首批试单和售后反馈记录。",
  },
];

export const historyRows = [
  {
    id: "hist-0528",
    title: "5000 元以内，小红书种草，不做食品和电子产品",
    createdAt: "2026-05-28 22:40",
    status: "运行中",
    reportHref: "/reports/demo-report",
  },
  {
    id: "hist-0527",
    title: "适合社群团购的宠物清洁用品",
    createdAt: "2026-05-27 19:16",
    status: "已完成",
    reportHref: "/reports/demo-report",
  },
  {
    id: "hist-0526",
    title: "低客单价露营配件验证",
    createdAt: "2026-05-26 14:08",
    status: "失败",
    reportHref: "/reports/demo-report",
  },
];
