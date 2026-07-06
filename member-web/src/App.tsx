import { useEffect, useState } from "react";
import {
  Button,
  Card,
  NavBar,
  SpinLoading,
  Space,
  Tag,
  TabBar,
} from "antd-mobile";
import { useTranslation } from "react-i18next";

import { fetchWelcome } from "./api/client";
import { getUnreadCount } from "./api/message";
import { useAuth } from "./auth/AuthContext";
import Login from "./pages/Login";
import Profile from "./pages/Profile";
import Activities from "./pages/Activities";
import { type Lang } from "./i18n";

export default function App() {
  const { t, i18n } = useTranslation();
  const { user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState("home");
  const [profileUnread, setProfileUnread] = useState(0);
  const [status, setStatus] = useState<"checking" | "ok" | "error">("checking");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!user) return;
    setStatus("checking");
    fetchWelcome()
      .then((data) => {
        setStatus("ok");
        setMessage(data.message);
      })
      .catch(() => setStatus("error"));
    getUnreadCount()
      .then(setProfileUnread)
      .catch(() => {});
  }, [i18n.language, user]);

  useEffect(() => {
    if (!user) return;
    if (activeTab === "profile") {
      getUnreadCount()
        .then(setProfileUnread)
        .catch(() => {});
    }
  }, [activeTab, user]);

  const toggleLang = () => {
    const next: Lang = i18n.language === "en" ? "zh-CN" : "en";
    i18n.changeLanguage(next);
    localStorage.setItem("lang", next);
  };

  if (loading) {
    return (
      <div
        style={{
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <SpinLoading />
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  const statusTag = {
    checking: <Tag color="warning">{t("home.checking")}</Tag>,
    ok: <Tag color="success">{t("home.connected")}</Tag>,
    error: <Tag color="danger">{t("home.failed")}</Tag>,
  }[status];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <NavBar
        backArrow={false}
        right={
          <Button size="mini" fill="none" onClick={toggleLang}>
            {i18n.language === "en" ? "中文" : "EN"}
          </Button>
        }
      >
        {t("appTitle")}
      </NavBar>

      <div style={{ flex: 1, overflow: "auto", padding: 12 }}>
        {activeTab === "home" && (
          <Space direction="vertical" block>
            <Card title={t("home.welcome")}>
              <div style={{ color: "#999", marginBottom: 12 }}>{t("home.subtitle")}</div>
              <Space direction="vertical">
                <Space>
                  <span>{t("home.backendStatus")}:</span>
                  {statusTag}
                </Space>
                <Space>
                  <span>{t("home.backendMessage")}:</span>
                  <span>{message || "-"}</span>
                </Space>
              </Space>
            </Card>
          </Space>
        )}
        {activeTab === "activity" && <Activities />}
        {activeTab === "profile" && <Profile />}
      </div>

      <TabBar activeKey={activeTab} onChange={setActiveTab}>
        <TabBar.Item key="home" title={t("tab.home")} />
        <TabBar.Item key="activity" title={t("tab.activity")} />
        <TabBar.Item
          key="profile"
          title={t("tab.profile")}
          badge={profileUnread > 0 ? profileUnread : undefined}
        />
      </TabBar>
    </div>
  );
}
