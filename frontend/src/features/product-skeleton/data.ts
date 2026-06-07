import type { LucideIcon } from "lucide-react";
import {
  ClipboardList,
  Sparkles,
} from "lucide-react";

export type NavKey = "new" | "tasks";

export type ProductNavItem = {
  key: NavKey;
  label: string;
  href: string;
  icon: LucideIcon;
};

export const productNavItems: ProductNavItem[] = [
  { key: "new", label: "新建研究", href: "/", icon: Sparkles },
  { key: "tasks", label: "我的研究", href: "/research/tasks", icon: ClipboardList },
];

export type SampleResearchPayload = {
  brief: string;
  budget: string;
  target_channels: string[];
  preferred_categories: string[];
  excluded_categories: string[];
  target_audience: string;
  expected_profit: string;
  supply_preferences: string[];
  constraints: string;
};

export type SampleResearchRequest = {
  id: string;
  title: string;
  summary: string;
  tags: string[];
  payload: SampleResearchPayload;
};

export const sampleResearchRequests: SampleResearchRequest[] = [
  {
    id: "xiaohongshu-light-inventory",
    title: "小红书轻库存选品",
    summary: "5000 元以内，从 1688 找适合内容种草的非食品、非电子产品。",
    tags: ["5000 元以内", "小红书", "1688"],
    payload: {
      brief: "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。",
      budget: "5000 元以内",
      target_channels: ["小红书种草"],
      preferred_categories: ["轻库存", "内容种草"],
      excluded_categories: ["食品", "电子产品"],
      target_audience: "通勤白领、租房办公人群",
      expected_profit: "毛利 30%+",
      supply_preferences: ["1688", "公开供给市场"],
      constraints: "首批验证预算小，不囤货。",
    },
  },
  {
    id: "community-pet-cleaning",
    title: "社群团购宠物清洁",
    summary: "面向新手养宠家庭，寻找 3000 元内可小单验证的清洁用品。",
    tags: ["3000 元以内", "社群团购", "宠物清洁"],
    payload: {
      brief: "找适合社群团购的宠物清洁用品，首批验证预算控制在 3000 元内。",
      budget: "3000 元以内",
      target_channels: ["社群团购", "小红书种草"],
      preferred_categories: ["宠物清洁", "消耗品", "组合包"],
      excluded_categories: ["宠物食品", "药品", "电子产品"],
      target_audience: "新手养宠家庭、宠物社群用户",
      expected_profit: "毛利 25%+",
      supply_preferences: ["1688", "宠物用品批发市场"],
      constraints: "首批小样验证，优先选择低售后和易复购用品。",
    },
  },
  {
    id: "rental-desk-small-goods",
    title: "租房办公桌面小物",
    summary: "面向租房办公人群，寻找低库存、易拍摄、可内容种草的桌面小物。",
    tags: ["低库存", "桌面小物", "内容种草"],
    payload: {
      brief: "面向租房办公人群，寻找低库存、可内容种草的桌面小物。",
      budget: "4000 元以内",
      target_channels: ["小红书种草", "短视频"],
      preferred_categories: ["桌面收纳", "办公小物", "氛围改善"],
      excluded_categories: ["食品", "电子产品", "大件家具"],
      target_audience: "租房办公人群、通勤白领、远程办公用户",
      expected_profit: "毛利 30%+",
      supply_preferences: ["1688", "义乌小商品供给"],
      constraints: "单件体积小，首批不囤大货，优先测试 3 组内容角度。",
    },
  },
];

export const samplePrompts = sampleResearchRequests.map(
  (sample) => sample.payload.brief,
);
