import { useEffect, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  message,
} from "antd";
import { useTranslation } from "react-i18next";

import {
  approveRegistration,
  createCompetition,
  listCompetitionRegistrations,
  listCompetitions,
  publishCompetition,
  type Competition,
  type CompetitionRegistration,
  type CompetitionStatus,
  type CompetitionType,
} from "../api/competition";
import { listCourses, type Course } from "../api/course";
import {
  generateGroups,
  listGroups,
  movePlayer,
  startCompetition,
  type CompetitionGroup,
} from "../api/grouping";
import { listOrganizations, type Organization } from "../api/org";
import {
  listRankings,
  previewRankings,
  publishRankings,
  updateRankingAward,
  type Ranking as RankingRow,
  type RankingPreviewItem,
} from "../api/ranking";
import { adminReview, closePlay, listScorecards, type ScoreCard } from "../api/scoring";

const HOLES = Array.from({ length: 18 }, (_, i) => i + 1);

const TYPE_COLOR: Record<CompetitionType, string> = {
  official: "green",
  team: "blue",
  invitation: "purple",
  social: "orange",
  training: "cyan",
};

const STATUS_COLOR: Record<CompetitionStatus, string> = {
  draft: "default",
  open: "success",
  closed: "warning",
  playing: "processing",
  review: "gold",
  completed: "blue",
  cancelled: "error",
};

export default function CompetitionPage() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Competition[]>([]);
  const [branches, setBranches] = useState<Organization[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<Competition | null>(null);
  const [regs, setRegs] = useState<CompetitionRegistration[]>([]);
  const [groups, setGroups] = useState<CompetitionGroup[]>([]);
  const [scorecards, setScorecards] = useState<ScoreCard[]>([]);
  const [rejectTarget, setRejectTarget] = useState<ScoreCard | null>(null);
  const [rejectComment, setRejectComment] = useState("");
  const [rankings, setRankings] = useState<RankingRow[]>([]);
  const [previewRows, setPreviewRows] = useState<RankingPreviewItem[]>([]);
  const [form] = Form.useForm();
  const [groupForm] = Form.useForm();

  const loadCourses = () => listCourses().then(setCourses).catch(() => {});
  const load = () => listCompetitions().then(setRows).catch(() => {});
  useEffect(() => {
    load();
    loadCourses();
    listOrganizations()
      .then((os) => setBranches(os.filter((o) => o.level === "branch")))
      .catch(() => {});
  }, []);

  const onCreate = async () => {
    const v = await form.validateFields();
    try {
      const created = await createCompetition({
        name: v.name,
        description: v.description,
        competition_type: v.competition_type,
        level: v.level,
        course_id: v.course_id,
        branch_id: v.hqWide ? null : v.branch_id,
        start_time: v.start_time.toISOString(),
        end_time: v.end_time ? v.end_time.toISOString() : undefined,
        registration_deadline: v.registration_deadline
          ? v.registration_deadline.toISOString()
          : undefined,
        fee: v.fee,
        max_players: v.max_players,
        max_handicap: v.max_handicap,
      });
      await publishCompetition(created.id);
      message.success(t("competition.createSuccess"));
      setOpen(false);
      form.resetFields();
      load();
    } catch {
      message.error(t("competition.opFailed"));
    }
  };

  const openDetail = async (c: Competition) => {
    setDetail(c);
    try {
      const [r, g, s, rk] = await Promise.all([
        listCompetitionRegistrations(c.id),
        listGroups(c.id),
        listScorecards(c.id),
        listRankings(c.id),
      ]);
      setRegs(r);
      setGroups(g);
      setScorecards(s);
      setRankings(rk);
      setPreviewRows([]);
    } catch {
      message.error(t("competition.opFailed"));
    }
  };

  const onGenerateGroups = async (force = false) => {
    if (!detail) return;
    const v = await groupForm.validateFields();
    try {
      await generateGroups(detail.id, {
        group_size: v.group_size,
        force,
        first_tee_time: v.first_tee_time ? v.first_tee_time.toISOString() : undefined,
        interval_minutes: v.interval_minutes,
      });
      message.success(t("grouping.generateSuccess"));
      openDetail(detail);
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 409 && !force) {
        Modal.confirm({
          title: t("grouping.regenerateConfirmTitle"),
          content: t("grouping.regenerateConfirmContent"),
          onOk: () => onGenerateGroups(true),
        });
      } else {
        message.error(t("grouping.opFailed"));
      }
    }
  };

  const onMovePlayer = async (playerId: number, targetGroupId: number) => {
    if (!detail) return;
    try {
      await movePlayer(detail.id, playerId, targetGroupId);
      openDetail(detail);
    } catch {
      message.error(t("grouping.opFailed"));
    }
  };

  const onStart = async () => {
    if (!detail) return;
    try {
      await startCompetition(detail.id);
      message.success(t("grouping.startSuccess"));
      openDetail(detail);
      load();
    } catch (e: unknown) {
      const detailMsg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detailMsg || t("grouping.opFailed"));
    }
  };

  const onApproveScore = async (cardId: number) => {
    if (!detail) return;
    try {
      await adminReview(detail.id, cardId, true);
      message.success(t("scoring.approveSuccess"));
      openDetail(detail);
    } catch {
      message.error(t("scoring.opFailed"));
    }
  };

  const onRejectScore = async () => {
    if (!detail || !rejectTarget) return;
    try {
      await adminReview(detail.id, rejectTarget.id, false, rejectComment || undefined);
      message.success(t("scoring.rejectSuccess"));
      setRejectTarget(null);
      setRejectComment("");
      openDetail(detail);
    } catch {
      message.error(t("scoring.opFailed"));
    }
  };

  const onClosePlay = async () => {
    if (!detail) return;
    try {
      await closePlay(detail.id);
      message.success(t("scoring.closePlaySuccess"));
      openDetail(detail);
      load();
    } catch (e: unknown) {
      const detailMsg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detailMsg || t("scoring.opFailed"));
    }
  };

  const onPreviewRankings = async () => {
    if (!detail) return;
    try {
      const rows = await previewRankings(detail.id);
      setPreviewRows(rows);
    } catch {
      message.error(t("ranking.opFailed"));
    }
  };

  const onPublishRankings = async () => {
    if (!detail) return;
    try {
      await publishRankings(detail.id);
      message.success(t("ranking.publishSuccess"));
      openDetail(detail);
      load();
    } catch (e: unknown) {
      const detailMsg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detailMsg || t("ranking.opFailed"));
    }
  };

  const onUpdateAward = async (rankingId: number, award: string) => {
    if (!detail) return;
    try {
      await updateRankingAward(detail.id, rankingId, award || null);
      openDetail(detail);
    } catch {
      message.error(t("ranking.opFailed"));
    }
  };

  const onApprove = async (regId: number, approve: boolean) => {
    if (!detail) return;
    try {
      await approveRegistration(detail.id, regId, approve);
      message.success(
        approve ? t("competition.approveSuccess") : t("competition.rejectSuccess")
      );
      openDetail(detail);
      load();
    } catch {
      message.error(t("competition.opFailed"));
    }
  };

  const branchName = (id: number | null) =>
    id === null
      ? t("competition.hqWide")
      : branches.find((b) => b.id === id)?.name ?? id;
  const courseName = (id: number | null) =>
    id === null ? "-" : courses.find((c) => c.id === id)?.name_zh ?? id;

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: t("competition.name"), dataIndex: "name" },
    {
      title: t("competition.type"),
      dataIndex: "competition_type",
      render: (v: CompetitionType) => (
        <Tag color={TYPE_COLOR[v]}>{t(`competitionType.${v}`)}</Tag>
      ),
    },
    {
      title: t("competition.status"),
      dataIndex: "status",
      render: (v: CompetitionStatus) => (
        <Tag color={STATUS_COLOR[v]}>{t(`competitionStatus.${v}`)}</Tag>
      ),
    },
    {
      title: t("competition.branch"),
      dataIndex: "branch_id",
      render: (v: number | null) => branchName(v),
    },
    {
      title: t("competition.registered"),
      render: (_: unknown, r: Competition) =>
        `${r.registered_count ?? 0}/${r.max_players}`,
    },
    {
      title: t("competition.actions"),
      render: (_: unknown, row: Competition) => (
        <Button size="small" onClick={() => openDetail(row)}>
          {t("competition.detail")}
        </Button>
      ),
    },
  ];

  const regColumns = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: t("competition.memberId"), dataIndex: "member_id" },
    { title: t("competition.teamId"), dataIndex: "team_id" },
    {
      title: t("competition.paymentStatus"),
      dataIndex: "payment_status",
      render: (v: string) => t(`competitionRegPaymentStatus.${v}`),
    },
    {
      title: t("competition.approvalStatus"),
      dataIndex: "approval_status",
      render: (v: string) => t(`competitionRegApprovalStatus.${v}`),
    },
    { title: t("competition.remark"), dataIndex: "remark" },
    {
      title: t("competition.actions"),
      render: (_: unknown, row: CompetitionRegistration) =>
        row.approval_status === "pending" ? (
          <Space>
            <Button size="small" type="primary" onClick={() => onApprove(row.id, true)}>
              {t("competition.approve")}
            </Button>
            <Button size="small" danger onClick={() => onApprove(row.id, false)}>
              {t("competition.reject")}
            </Button>
          </Space>
        ) : null,
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Button type="primary" onClick={() => setOpen(true)}>
        {t("competition.add")}
      </Button>
      <Table rowKey="id" dataSource={rows} columns={columns} pagination={false} />

      <Modal
        title={t("competition.add")}
        open={open}
        onOk={onCreate}
        onCancel={() => setOpen(false)}
        okText={t("competition.submit")}
        cancelText={t("competition.cancel")}
        width={640}
      >
        <Form form={form} layout="vertical" initialValues={{ max_players: 40 }}>
          <Form.Item name="name" label={t("competition.name")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label={t("competition.description")}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item
            name="competition_type"
            label={t("competition.type")}
            rules={[{ required: true }]}
          >
            <Select
              options={(
                ["official", "team", "invitation", "social", "training"] as CompetitionType[]
              ).map((v) => ({ value: v, label: t(`competitionType.${v}`) }))}
            />
          </Form.Item>
          <Form.Item name="level" label={t("competition.level")}>
            <Input placeholder="A级" />
          </Form.Item>
          <Form.Item name="course_id" label={t("competition.course")}>
            <Select
              allowClear
              options={courses.map((c) => ({ value: c.id, label: c.name_zh }))}
            />
          </Form.Item>
          <Form.Item name="hqWide" label={t("competition.hqWide")} valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            noStyle
            shouldUpdate={(prev, cur) => prev.hqWide !== cur.hqWide}
          >
            {({ getFieldValue }) =>
              !getFieldValue("hqWide") && (
                <Form.Item
                  name="branch_id"
                  label={t("competition.branch")}
                  rules={[{ required: true }]}
                >
                  <Select options={branches.map((b) => ({ value: b.id, label: b.name }))} />
                </Form.Item>
              )
            }
          </Form.Item>
          <Form.Item
            name="start_time"
            label={t("competition.startTime")}
            rules={[{ required: true }]}
          >
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="end_time" label={t("competition.endTime")}>
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="registration_deadline" label={t("competition.registrationDeadline")}>
            <DatePicker showTime style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="fee" label={t("competition.fee")}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="max_players" label={t("competition.maxPlayers")}>
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="max_handicap"
            label={t("competition.maxHandicap")}
            extra={t("competition.maxHandicapHint")}
          >
            <InputNumber min={0} step={0.1} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={detail?.name}
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={880}
      >
        {detail && (
          <Tabs
            items={[
              {
                key: "registrations",
                label: t("competition.tabRegistrations"),
                children: (
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Descriptions bordered size="small" column={2}>
                      <Descriptions.Item label={t("competition.registered")}>
                        {detail.registered_count ?? 0}
                      </Descriptions.Item>
                      <Descriptions.Item label={t("competition.approved")}>
                        {detail.approved_count ?? 0}
                      </Descriptions.Item>
                      <Descriptions.Item label={t("competition.maxPlayers")}>
                        {detail.max_players}
                      </Descriptions.Item>
                      <Descriptions.Item label={t("competition.fee")}>
                        {detail.fee ?? "-"}
                      </Descriptions.Item>
                      <Descriptions.Item label={t("competition.course")}>
                        {courseName(detail.course_id)}
                      </Descriptions.Item>
                      <Descriptions.Item label={t("competition.maxHandicap")}>
                        {detail.max_handicap ?? t("competition.noLimit")}
                      </Descriptions.Item>
                    </Descriptions>
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={regs}
                      columns={regColumns}
                      pagination={false}
                    />
                  </Space>
                ),
              },
              {
                key: "groups",
                label: t("grouping.tabGroups"),
                children: (
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Form form={groupForm} layout="inline" initialValues={{ group_size: 4, interval_minutes: 10 }}>
                      <Form.Item name="group_size" label={t("grouping.groupSize")}>
                        <InputNumber min={2} style={{ width: 90 }} />
                      </Form.Item>
                      <Form.Item name="first_tee_time" label={t("grouping.firstTeeTime")}>
                        <DatePicker showTime />
                      </Form.Item>
                      <Form.Item name="interval_minutes" label={t("grouping.intervalMinutes")}>
                        <InputNumber min={1} style={{ width: 90 }} />
                      </Form.Item>
                      <Form.Item>
                        <Button onClick={() => onGenerateGroups(false)}>
                          {t("grouping.generate")}
                        </Button>
                      </Form.Item>
                      <Form.Item>
                        <Button type="primary" onClick={onStart}>
                          {t("grouping.start")}
                        </Button>
                      </Form.Item>
                    </Form>
                    {groups.map((g) => (
                      <Card
                        key={g.id}
                        size="small"
                        title={`${t("grouping.group")} ${g.group_number}${
                          g.tee_time ? " · " + new Date(g.tee_time).toLocaleTimeString() : ""
                        }`}
                      >
                        <Table
                          rowKey="id"
                          size="small"
                          pagination={false}
                          dataSource={g.players}
                          columns={[
                            { title: t("grouping.order"), dataIndex: "order_number", width: 60 },
                            { title: t("competition.memberId"), dataIndex: "member_id" },
                            { title: t("member.handicap"), dataIndex: "handicap" },
                            {
                              title: t("grouping.moveTo"),
                              render: (_: unknown, p) => (
                                <Select<number>
                                  size="small"
                                  style={{ width: 140 }}
                                  placeholder={t("grouping.moveTo")}
                                  value={undefined}
                                  options={groups
                                    .filter((og) => og.id !== g.id)
                                    .map((og) => ({
                                      value: og.id,
                                      label: `${t("grouping.group")} ${og.group_number}`,
                                    }))}
                                  onChange={(target) => onMovePlayer(p.id, target)}
                                />
                              ),
                            },
                          ]}
                        />
                      </Card>
                    ))}
                    {groups.length === 0 && (
                      <div style={{ color: "#999" }}>{t("grouping.empty")}</div>
                    )}
                  </Space>
                ),
              },
              {
                key: "scoring",
                label: t("scoring.tabScoring"),
                children: (
                  <Space direction="vertical" style={{ width: "100%" }}>
                    {detail.status === "playing" && (
                      <Button danger onClick={onClosePlay}>
                        {t("scoring.closePlay")}
                      </Button>
                    )}
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={scorecards}
                      pagination={false}
                      expandable={{
                        expandedRowRender: (card) => (
                          <Space wrap>
                            {HOLES.map((h) => (
                              <Tag key={h}>
                                {h}: {card[`hole${h}` as keyof ScoreCard] ?? "-"}
                              </Tag>
                            ))}
                          </Space>
                        ),
                      }}
                      columns={[
                        { title: t("competition.memberId"), dataIndex: "member_id" },
                        { title: t("grouping.tabGroups"), dataIndex: "group_id" },
                        { title: t("scoring.total"), dataIndex: "total_score" },
                        { title: t("scoring.net"), dataIndex: "net_score" },
                        {
                          title: t("competition.status"),
                          dataIndex: "status",
                          render: (v: string) => t(`scoreCardStatus.${v}`),
                        },
                        {
                          title: t("competition.actions"),
                          render: (_: unknown, card: ScoreCard) =>
                            card.status === "submitted" || card.status === "checking" ? (
                              <Space>
                                <Button
                                  size="small"
                                  type="primary"
                                  onClick={() => onApproveScore(card.id)}
                                >
                                  {t("competition.approve")}
                                </Button>
                                <Button
                                  size="small"
                                  danger
                                  onClick={() => setRejectTarget(card)}
                                >
                                  {t("competition.reject")}
                                </Button>
                              </Space>
                            ) : null,
                        },
                      ]}
                    />
                  </Space>
                ),
              },
              {
                key: "ranking",
                label: t("ranking.tabRanking"),
                children: (
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Space>
                      <Button onClick={onPreviewRankings}>{t("ranking.preview")}</Button>
                      <Button type="primary" onClick={onPublishRankings}>
                        {t("ranking.publish")}
                      </Button>
                    </Space>
                    {previewRows.length > 0 && (
                      <Card size="small" title={t("ranking.previewTitle")}>
                        <Table
                          rowKey={(r) => `${r.scope}-${r.member_id ?? r.team_id}`}
                          size="small"
                          pagination={false}
                          dataSource={previewRows}
                          columns={[
                            {
                              title: t("ranking.scope"),
                              dataIndex: "scope",
                              render: (v: string) => t(`rankingScope.${v}`),
                            },
                            { title: t("ranking.rank"), dataIndex: "rank" },
                            {
                              title: t("ranking.subject"),
                              render: (_: unknown, r: RankingPreviewItem) =>
                                r.member_id ?? r.team_id,
                            },
                            { title: t("ranking.score"), dataIndex: "score" },
                            {
                              title: t("ranking.award"),
                              render: (_: unknown, r: RankingPreviewItem) =>
                                r.award ? t(`award.${r.award}`) : "-",
                            },
                          ]}
                        />
                      </Card>
                    )}
                    <Card size="small" title={t("rankingScope.individual")}>
                      <Table
                        rowKey="id"
                        size="small"
                        pagination={false}
                        dataSource={rankings.filter((r) => r.scope === "individual")}
                        columns={[
                          { title: t("ranking.rank"), dataIndex: "rank" },
                          { title: t("competition.memberId"), dataIndex: "member_id" },
                          { title: t("ranking.score"), dataIndex: "score" },
                          {
                            title: t("ranking.award"),
                            render: (_: unknown, r: RankingRow) => (
                              <Input
                                size="small"
                                defaultValue={r.award ?? ""}
                                onBlur={(e) => onUpdateAward(r.id, e.target.value)}
                              />
                            ),
                          },
                        ]}
                      />
                    </Card>
                    <Card size="small" title={t("rankingScope.team")}>
                      <Table
                        rowKey="id"
                        size="small"
                        pagination={false}
                        dataSource={rankings.filter((r) => r.scope === "team")}
                        columns={[
                          { title: t("ranking.rank"), dataIndex: "rank" },
                          { title: t("org.team"), dataIndex: "team_id" },
                          { title: t("ranking.score"), dataIndex: "score" },
                          {
                            title: t("ranking.award"),
                            render: (_: unknown, r: RankingRow) => (
                              <Input
                                size="small"
                                defaultValue={r.award ?? ""}
                                onBlur={(e) => onUpdateAward(r.id, e.target.value)}
                              />
                            ),
                          },
                        ]}
                      />
                    </Card>
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Modal>

      <Modal
        title={t("scoring.rejectReason")}
        open={!!rejectTarget}
        onOk={onRejectScore}
        onCancel={() => setRejectTarget(null)}
      >
        <Input.TextArea
          rows={3}
          value={rejectComment}
          onChange={(e) => setRejectComment(e.target.value)}
        />
      </Modal>
    </Space>
  );
}
