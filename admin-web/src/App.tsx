import { useMemo, useState, type ReactNode } from "react";
import {
  ConfigProvider,
  Dropdown,
  Layout,
  Menu,
  Select,
  Space,
  Spin,
  Tag,
  theme,
} from "antd";
import enUS from "antd/locale/en_US";
import zhCN from "antd/locale/zh_CN";
import {
  DashboardOutlined,
  DollarOutlined,
  LogoutOutlined,
  MessageOutlined,
  ScheduleOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import MemberPage from "./pages/Member";
import ActivityPage from "./pages/Activity";
import FinancePage from "./pages/Finance";
import MessagePage from "./pages/Message";
import OrganizationPage from "./pages/Organization";
import { useAuth } from "./auth/AuthContext";
import { menusForRole, type MenuKey } from "./auth/roles";
import { SUPPORTED_LANGS, type Lang } from "./i18n";

const { Header, Sider, Content } = Layout;

const MENU_ICONS: Record<MenuKey, ReactNode> = {
  dashboard: <DashboardOutlined />,
  organization: <TeamOutlined />,
  member: <UserOutlined />,
  activity: <ScheduleOutlined />,
  finance: <DollarOutlined />,
  message: <MessageOutlined />,
};

export default function App() {
  const { t, i18n } = useTranslation();
  const { user, loading, logout } = useAuth();
  const [selected, setSelected] = useState<MenuKey>("dashboard");

  const changeLang = (lang: Lang) => {
    i18n.changeLanguage(lang);
    localStorage.setItem("lang", lang);
  };

  const visibleMenus = useMemo(
    () => (user ? menusForRole(user.role) : []),
    [user]
  );

  const menuItems = visibleMenus.map((key) => ({
    key,
    icon: MENU_ICONS[key],
    label: t(`menu.${key}`),
  }));

  const currentSelection = visibleMenus.includes(selected) ? selected : "dashboard";

  const configProvider = (children: ReactNode) => (
    <ConfigProvider
      locale={i18n.language === "en" ? enUS : zhCN}
      theme={{ token: { colorPrimary: "#1f7a3d" } }}
    >
      {children}
    </ConfigProvider>
  );

  if (loading) {
    return configProvider(
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (!user) {
    return configProvider(<Login />);
  }

  return configProvider(
    <Layout style={{ minHeight: "100vh" }}>
      <Sider theme="light" breakpoint="lg" collapsedWidth="0">
        <div
          style={{
            height: 56,
            margin: 16,
            display: "flex",
            alignItems: "center",
            fontWeight: 600,
            color: "#1f7a3d",
          }}
        >
          NZ Golf CRM
        </div>
        <Menu
          mode="inline"
          selectedKeys={[currentSelection]}
          items={menuItems}
          onClick={(e) => setSelected(e.key as MenuKey)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            paddingInline: 24,
          }}
        >
          <span style={{ fontWeight: 600 }}>{t("appTitle")}</span>
          <Space size="middle">
            <Select<Lang>
              value={i18n.language as Lang}
              style={{ width: 120 }}
              onChange={changeLang}
              options={SUPPORTED_LANGS.map((l) => ({
                value: l,
                label: l === "zh-CN" ? "简体中文" : "English",
              }))}
            />
            <Dropdown
              menu={{
                items: [
                  {
                    key: "logout",
                    icon: <LogoutOutlined />,
                    label: t("common.logout"),
                    onClick: logout,
                  },
                ],
              }}
            >
              <Space style={{ cursor: "pointer" }}>
                <UserOutlined />
                <span>{user.full_name || user.username}</span>
                <Tag color="green">{t(`role.${user.role}`)}</Tag>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: 24 }}>
          <ContentArea selected={currentSelection} />
        </Content>
      </Layout>
    </Layout>
  );
}

function ContentArea({ selected }: { selected: MenuKey }) {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  return (
    <div
      style={{
        padding: 24,
        minHeight: 360,
        background: colorBgContainer,
        borderRadius: borderRadiusLG,
      }}
    >
      {selected === "dashboard" && <Dashboard />}
      {selected === "organization" && <OrganizationPage />}
      {selected === "member" && <MemberPage />}
      {selected === "activity" && <ActivityPage />}
      {selected === "finance" && <FinancePage />}
      {selected === "message" && <MessagePage />}
      {selected !== "dashboard" &&
        selected !== "organization" &&
        selected !== "member" &&
        selected !== "activity" &&
        selected !== "finance" &&
        selected !== "message" && <Placeholder module={selected} />}
    </div>
  );
}

function Placeholder({ module }: { module: MenuKey }) {
  const { t } = useTranslation();
  return (
    <div style={{ color: "#999" }}>
      {t(`menu.${module}`)} — coming soon (Phase 2+)
    </div>
  );
}
