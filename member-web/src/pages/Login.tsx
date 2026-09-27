import { useEffect, useState } from "react";
import { Button, Divider, Form, Input, NavBar, Space, Toast } from "antd-mobile";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { type Lang } from "../i18n";

const ADMIN_APP_URL = import.meta.env.VITE_ADMIN_APP_URL || "http://localhost:5173";

export default function Login() {
  const { t, i18n } = useTranslation();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [quickLoading, setQuickLoading] = useState<"member" | null>(null);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
    } catch {
      Toast.show({ content: t("login.failed") });
    } finally {
      setLoading(false);
    }
  };

  const quickLoginMember = async () => {
    setQuickLoading("member");
    try {
      await login("demo", "demo123456");
    } catch {
      Toast.show({ content: t("login.failed") });
    } finally {
      setQuickLoading(null);
    }
  };

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("autologin") === "1") {
      quickLoginMember();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const viewAdminApp = () => {
    window.location.href = `${ADMIN_APP_URL}/?autologin=1`;
  };

  const toggleLang = () => {
    const next: Lang = i18n.language === "en" ? "zh-CN" : "en";
    i18n.changeLanguage(next);
    localStorage.setItem("lang", next);
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <NavBar
        backArrow={false}
        right={
          <Button size="mini" fill="none" onClick={toggleLang}>
            {i18n.language === "en" ? "中文" : "EN"}
          </Button>
        }
      >
        {t("login.title")}
      </NavBar>
      <div style={{ padding: 16, marginTop: 24 }}>
        <Form
          layout="vertical"
          onFinish={onFinish}
          footer={
            <Button block type="submit" color="primary" loading={loading}>
              {t("login.submit")}
            </Button>
          }
        >
          <Form.Item name="username" label={t("login.username")} rules={[{ required: true }]}>
            <Input placeholder={t("login.username")} />
          </Form.Item>
          <Form.Item name="password" label={t("login.password")} rules={[{ required: true }]}>
            <Input type="password" placeholder={t("login.password")} />
          </Form.Item>
        </Form>
        <Divider>{t("login.quickAccessHint")}</Divider>
        <Space direction="vertical" block>
          <Button
            block
            color="primary"
            fill="outline"
            loading={quickLoading === "member"}
            onClick={quickLoginMember}
          >
            {t("login.continueAsMember")}
          </Button>
          <Button block fill="outline" onClick={viewAdminApp}>
            {t("login.continueAsAdmin")}
          </Button>
        </Space>
      </div>
    </div>
  );
}
