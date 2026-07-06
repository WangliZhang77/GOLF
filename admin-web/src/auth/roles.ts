import type { UserRole } from "../api/auth";

export const ALL_MENU_KEYS = [
  "dashboard",
  "organization",
  "member",
  "activity",
  "finance",
  "message",
] as const;

export type MenuKey = (typeof ALL_MENU_KEYS)[number];

// 每个角色在后台可见的菜单（Phase 1 基础版，后续模块细化按钮级权限）
export const ROLE_MENUS: Record<UserRole, MenuKey[]> = {
  super_admin: ["dashboard", "organization", "member", "activity", "finance", "message"],
  council_admin: ["dashboard", "organization", "member", "activity", "finance", "message"],
  team_captain: ["dashboard", "member", "activity", "message"],
  event_director: ["dashboard", "member", "activity", "message"],
  finance: ["dashboard", "member", "finance", "message"],
  member: ["dashboard"],
};

export function menusForRole(role: UserRole): MenuKey[] {
  return ROLE_MENUS[role] ?? ["dashboard"];
}
