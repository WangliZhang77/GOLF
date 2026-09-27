import { useEffect, useState } from "react";
import { Button, Card, List, NavBar, Space, Stepper, Tag, Toast } from "antd-mobile";
import {
  CheckCircleOutline,
  FlagOutline,
  HistogramOutline,
  SendOutline,
  TeamOutline,
} from "antd-mobile-icons";
import { useTranslation } from "react-i18next";

import {
  getMyScorecard,
  listGroupScorecards,
  peerConfirm,
  submitScorecard,
  updateHole,
  type ScoreCard,
} from "../api/scoring";
import IconBadge from "../components/IconBadge";

const HOLES = Array.from({ length: 18 }, (_, i) => i + 1);

export default function ScoreEntry({
  competitionId,
  onBack,
}: {
  competitionId: number;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  const [card, setCard] = useState<ScoreCard | null>(null);
  const [peers, setPeers] = useState<ScoreCard[]>([]);

  const load = () => {
    getMyScorecard(competitionId)
      .then(setCard)
      .catch(() => Toast.show({ content: t("scoring.noCard") }));
    listGroupScorecards(competitionId)
      .then(setPeers)
      .catch(() => {});
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [competitionId]);

  const editable = card ? card.status === "draft" || card.status === "rejected" : false;

  const onHoleChange = async (holeNumber: number, strokes: number) => {
    if (!card) return;
    try {
      const updated = await updateHole(competitionId, card.id, holeNumber, strokes);
      setCard(updated);
    } catch {
      Toast.show({ content: t("scoring.saveFailed") });
    }
  };

  const onSubmit = async () => {
    if (!card) return;
    try {
      const updated = await submitScorecard(competitionId, card.id);
      setCard(updated);
      Toast.show({ content: t("scoring.submitOk") });
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        t("scoring.submitFailed");
      Toast.show({ content: String(msg) });
    }
  };

  const onConfirmPeer = async (peerCardId: number) => {
    try {
      await peerConfirm(competitionId, peerCardId);
      Toast.show({ content: t("scoring.confirmOk") });
      load();
    } catch {
      Toast.show({ content: t("scoring.confirmFailed") });
    }
  };

  const filled = card ? HOLES.filter((h) => card[`hole${h}` as keyof ScoreCard] != null).length : 0;
  const otherPeers = peers.filter((p) => p.id !== card?.id && p.status === "submitted");

  return (
    <Space direction="vertical" block>
      <NavBar onBack={onBack}>{t("scoring.title")}</NavBar>

      {card && (
        <>
          <Card bodyStyle={{ padding: 16 }}>
            <Space align="center" style={{ marginBottom: 10 }}>
              <IconBadge icon={<HistogramOutline />} background="#e6f4ff" color="#1677ff" />
              <Tag color={card.status === "approved" ? "success" : "primary"}>
                {t(`scoreCardStatus.${card.status}`)}
              </Tag>
            </Space>
            <Space direction="vertical">
              <span>
                {t("scoring.out")}: {card.out_score ?? "-"} · {t("scoring.in")}:{" "}
                {card.in_score ?? "-"} · {t("scoring.total")}: {card.total_score ?? "-"}
              </span>
              {card.net_score !== null && (
                <span>
                  {t("scoring.net")}: {card.net_score}
                </span>
              )}
              <span>
                {filled}/18 {t("scoring.holesFilled")}
              </span>
            </Space>
          </Card>

          <List
            header={
              <Space align="center">
                <FlagOutline />
                <span>{t("scoring.holes")}</span>
              </Space>
            }
          >
            {HOLES.map((h) => {
              const value = card[`hole${h}` as keyof ScoreCard] as number | null;
              return (
                <List.Item key={h} extra={value ?? "-"}>
                  <Space align="center">
                    <span>{t("scoring.holeNumber", { n: h })}</span>
                    <Stepper
                      min={1}
                      max={15}
                      value={value ?? 4}
                      disabled={!editable}
                      onChange={(v) => onHoleChange(h, v)}
                    />
                  </Space>
                </List.Item>
              );
            })}
          </List>

          {editable && (
            <Button block color="primary" disabled={filled < 18} onClick={onSubmit}>
              <SendOutline /> {t("scoring.submit")}
            </Button>
          )}

          {card.status === "rejected" && (
            <Card>
              <div style={{ color: "#f5222d" }}>{t("scoring.rejectedHint")}</div>
            </Card>
          )}
        </>
      )}

      <List
        header={
          <Space align="center">
            <TeamOutline />
            <span>{t("scoring.peerReview")}</span>
          </Space>
        }
      >
        {otherPeers.map((p) => (
          <List.Item
            key={p.id}
            extra={
              <Button size="mini" onClick={() => onConfirmPeer(p.id)}>
                <CheckCircleOutline /> {t("scoring.confirm")}
              </Button>
            }
          >
            {t("competition.memberId")} {p.member_id} · {t("scoring.total")}{" "}
            {p.total_score ?? "-"}
          </List.Item>
        ))}
        {otherPeers.length === 0 && (
          <Card>
            <div style={{ color: "#999", padding: 12 }}>{t("scoring.noPeerPending")}</div>
          </Card>
        )}
      </List>
    </Space>
  );
}
