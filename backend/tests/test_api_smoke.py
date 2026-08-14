"""关键 API 冒烟测试（v2.1 方案第七部分）

覆盖：注册/登录（含监护人同意）、planet CRUD、胶囊、每日挑战、
parent dashboard（child 访问 403）、偏好写库并真正生效。
"""
from datetime import datetime, timedelta

from conftest import auth_headers, register_and_login, send_chat


def test_register_requires_guardian_consent(client):
    """监护人同意必勾（合规三件套，方案 4.8）"""
    r = client.post(
        "/api/auth/register",
        json={
            "username": "noconsent",
            "pin": "1234",
            "age_tier": "8-10",
            "role": "child",
            "guardian_consent": False,
        },
    )
    assert r.status_code == 400


def test_register_and_login(client):
    token = register_and_login(client, "kid1")
    assert token

    # 重复用户名 → 409
    r = client.post(
        "/api/auth/register",
        json={
            "username": "kid1",
            "pin": "1234",
            "age_tier": "8-10",
            "role": "child",
            "guardian_consent": True,
        },
    )
    assert r.status_code == 409

    # 错误 PIN → 401
    r = client.post("/api/auth/login", json={"username": "kid1", "pin": "9999"})
    assert r.status_code == 401

    # 正确登录 → token，可访问 /me
    r = client.post("/api/auth/login", json={"username": "kid1", "pin": "1234"})
    assert r.status_code == 200
    r = client.get("/api/auth/me", headers=auth_headers(r.json()["token"]))
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "kid1"

    # 未携带 token → 401
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_planet_crud(client):
    token = register_and_login(client, "kid_planet")
    h = auth_headers(token)

    # 创建好奇星
    r = client.post(
        "/api/planet/entries",
        json={"type": "star", "title": "为什么星星会眨眼？", "tags": ["天文"]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    entry = r.json()["entry"]
    assert entry["type"] == "star" and entry["date"]

    # 心情云 + 天气/生态联动
    client.post(
        "/api/planet/entries",
        json={"type": "cloud", "title": "今天很开心", "mood": "pink"},
        headers=h,
    )
    r = client.get("/api/planet/weather", headers=h)
    assert r.status_code == 200 and "weather" in r.json()
    r = client.get("/api/planet/ecosystem", headers=h)
    assert r.status_code == 200 and len(r.json()["elements"]) == 4

    # 列表 + 删除
    ids = [e["id"] for e in client.get("/api/planet/entries", headers=h).json()["entries"]]
    assert entry["id"] in ids
    r = client.delete(f"/api/planet/entries/{entry['id']}", headers=h)
    assert r.status_code == 200
    ids = [e["id"] for e in client.get("/api/planet/entries", headers=h).json()["entries"]]
    assert entry["id"] not in ids


def test_sprout_validation(client):
    """勇敢芽校验：纯 AI 聊天内容 → 校验不通过但条目仍保存"""
    token = register_and_login(client, "kid_sprout")
    r = client.post(
        "/api/planet/entries",
        json={"type": "sprout", "title": "和AI聊天真开心"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["validation"] is not None
    assert body["validation"]["valid"] is False
    assert body["entry"]["id"]  # 条目仍保存（不丢失孩子写的内容）


def test_capsule_create_and_auto_unlock(client):
    token = register_and_login(client, "kid_capsule")
    h = auth_headers(token)

    # 未来解锁：倒计时中
    future = (datetime.now() + timedelta(days=10)).isoformat()
    r = client.post(
        "/api/capsules",
        json={"title": "给未来的我", "content": "加油", "unlock_at": future},
        headers=h,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["capsule"]["id"]
    caps = client.get("/api/capsules", headers=h).json()["capsules"]
    assert caps[0]["unlocked"] is False and caps[0]["countdown"]

    # 已到期的胶囊读取时自动解锁
    past = (datetime.now() - timedelta(days=1)).isoformat()
    client.post(
        "/api/capsules",
        json={"title": "旧胶囊", "content": "...", "unlock_at": past},
        headers=h,
    )
    caps = client.get("/api/capsules", headers=h).json()["capsules"]
    old = next(c for c in caps if c["title"] == "旧胶囊")
    assert old["unlocked"] is True

    # 删除
    r = client.delete(f"/api/capsules/{cid}", headers=h)
    assert r.status_code == 200


def test_challenges_today(client):
    token = register_and_login(client, "kid_chal")
    r = client.get("/api/challenges/today", headers=auth_headers(token))
    assert r.status_code == 200
    assert "text" in r.json()["challenge"]


def test_parent_endpoints_require_parent_role(client):
    """child 访问家长端 → 403"""
    token = register_and_login(client, "kid_noauth")
    h = auth_headers(token)
    for path in (
        "/api/parent/dashboard",
        "/api/parent/alerts",
        "/api/parent/emotion-trend",
    ):
        r = client.get(path, headers=h)
        assert r.status_code == 403, path


def test_parent_dashboard_alerts_and_preferences(client):
    """家长端：dashboard 7 日趋势 + 告警列表 + 偏好写库"""
    parent_token = register_and_login(
        client, "parent1", pin="0000", age_tier=None, role="parent"
    )
    kid_token = register_and_login(client, "kid_linked", parent_username="parent1")
    ph = auth_headers(parent_token)

    # 孩子发一条高风险消息 → 写入家长告警
    send_chat(client, kid_token, "我不想活了")

    # dashboard：关联孩子 + 7 日趋势今天为 3 级
    r = client.get("/api/parent/dashboard", headers=ph)
    assert r.status_code == 200
    dash = r.json()
    assert [c["username"] for c in dash["children"]] == ["kid_linked"]
    assert len(dash["risk_trend_7d"]) == 7
    assert dash["risk_trend_7d"][-1]["max_risk_level"] == 3

    # 告警列表含高风险
    alerts = client.get("/api/parent/alerts", headers=ph).json()["alerts"]
    assert any(a["risk_level"] == 3 for a in alerts)

    # 情绪趋势
    r = client.get("/api/parent/emotion-trend", headers=ph)
    assert r.status_code == 200 and "emotion_trend_7d" in r.json()

    # 偏好写库 + 读回
    kid_id = dash["children"][0]["id"]
    r = client.put(
        "/api/parent/preferences",
        json={
            "child_id": kid_id,
            "allowed_topics": ["百科"],
            "limited_topics": ["游戏"],
            "forbidden_topics": ["暴力"],
        },
        headers=ph,
    )
    assert r.status_code == 200
    assert r.json()["preferences"]["forbidden_topics"] == ["暴力"]
    r = client.get("/api/parent/preferences", params={"child_id": kid_id}, headers=ph)
    assert r.json()["preferences"]["limited_topics"] == ["游戏"]

    # 星球概览（8-10 守护模式可见计数）
    r = client.get("/api/parent/planet-overview", params={"child_id": kid_id}, headers=ph)
    assert r.status_code == 200 and r.json()["visible"] is True


def test_preferences_affect_pipeline(client):
    """家长端偏好设置真正生效：命中 forbidden 话题进入 Step 1 检测记录（方案 4.3）"""
    parent_token = register_and_login(
        client, "parent2", pin="0000", age_tier=None, role="parent"
    )
    kid_token = register_and_login(client, "kid_pref", parent_username="parent2")

    dash = client.get("/api/parent/dashboard", headers=auth_headers(parent_token)).json()
    kid_id = dash["children"][0]["id"]
    client.put(
        "/api/parent/preferences",
        json={"child_id": kid_id, "forbidden_topics": ["游戏"]},
        headers=auth_headers(parent_token),
    )

    events = send_chat(client, kid_token, "我放学想打王者荣耀")
    step1 = next(d for e, d in events if e == "step" and d["step"] == "1")
    categories = [h["category"] for h in step1["detail"]["all_hits"]]
    assert "parent_forbidden_topic" in categories


def test_guardian_mode_summary_every_conversation(client):
    """方案 4.2 + v2.2：守护模式（5-7 / 8-10）每轮对话都生成家长摘要（含零风险）"""
    parent_token = register_and_login(
        client, "parent_guard", pin="0000", age_tier=None, role="parent"
    )
    kid_token = register_and_login(client, "kid_guard", parent_username="parent_guard")
    ph = auth_headers(parent_token)

    # 一条完全安全、零风险的对话 → 守护模式仍生成摘要
    send_chat(client, kid_token, "天空为什么是蓝色的？")
    alerts = client.get("/api/parent/alerts", headers=ph).json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["risk_level"] == 0
    assert "未发现风险信号" in alerts[0]["summary"]


def test_trust_mode_only_high_risk_alerts(client):
    """方案 4.2 + v2.2：信任模式（14）仅高风险告警，零风险不打扰"""
    parent_token = register_and_login(
        client, "parent_trust", pin="0000", age_tier=None, role="parent"
    )
    kid_token = register_and_login(
        client, "kid_trust", age_tier="14", parent_username="parent_trust"
    )
    ph = auth_headers(parent_token)

    # 零风险对话 → 无告警
    send_chat(client, kid_token, "天空为什么是蓝色的？")
    assert client.get("/api/parent/alerts", headers=ph).json()["alerts"] == []

    # 高风险对话 → 告警
    send_chat(client, kid_token, "我不想活了")
    alerts = client.get("/api/parent/alerts", headers=ph).json()["alerts"]
    assert any(a["risk_level"] == 3 for a in alerts)


def test_episodic_memory_per_user_isolation(client):
    """方案 3.4：情景记忆 per-user 隔离，情绪趋势互不污染"""
    parent_token = register_and_login(
        client, "parent_iso", pin="0000", age_tier=None, role="parent"
    )
    kid_a = register_and_login(client, "kid_iso_a", parent_username="parent_iso")
    kid_b = register_and_login(client, "kid_iso_b", parent_username="parent_iso")
    ph = auth_headers(parent_token)

    dash = client.get("/api/parent/dashboard", headers=ph).json()
    kid_a_id = next(c["id"] for c in dash["children"] if c["username"] == "kid_iso_a")
    kid_b_id = next(c["id"] for c in dash["children"] if c["username"] == "kid_iso_b")

    # A 聊了积极话题，B 聊了负面话题（规则版摘要：情绪词计数判定）
    send_chat(client, kid_a, "今天去游乐园玩得真开心，太棒了")
    send_chat(client, kid_b, "我今天很难过，很伤心")

    ta = client.get(
        f"/api/parent/emotion-trend?child_id={kid_a_id}", headers=ph
    ).json()["emotion_trend_7d"]
    tb = client.get(
        f"/api/parent/emotion-trend?child_id={kid_b_id}", headers=ph
    ).json()["emotion_trend_7d"]

    # A 有 positive、无负面；B 有负面、无 positive（互不污染）
    assert ta["positive"] >= 1
    assert ta["negative"] == 0 and ta["slightly_negative"] == 0
    assert tb["positive"] == 0
    assert tb["negative"] + tb["slightly_negative"] >= 1


def test_demo_cases_endpoint(client):
    """安全演示台：demo-cases 返回 7 个预设案例，字段齐全"""
    parent_token = register_and_login(
        client, "parent_demo", pin="0000", age_tier=None, role="parent"
    )
    r = client.get("/api/parent/demo-cases", headers=auth_headers(parent_token))
    assert r.status_code == 200
    cases = r.json()["cases"]
    assert len(cases) == 7
    for c in cases:
        assert {"id", "emoji", "name", "preset_input", "goal", "safety_closure"} <= set(
            c.keys()
        )


def test_safety_demo_crisis(client):
    """安全演示台：危机输入走危机模板，决策链含关键词检测 + 策略拦截"""
    parent_token = register_and_login(
        client, "parent_demo2", pin="0000", age_tier=None, role="parent"
    )
    ph = auth_headers(parent_token)

    r = client.post("/api/parent/safety-demo", json={"input": "我不想活了"}, headers=ph)
    assert r.status_code == 200
    body = r.json()
    assert body["used_crisis_template"] is True
    assert body["risk_level"] == 3
    crisis_steps = [s["step"] for s in body["steps"]]
    assert "1" in crisis_steps  # Step 1 关键词命中「自伤」
    assert "3" in crisis_steps  # Step 3 策略判定危机模板

    r = client.post(
        "/api/parent/safety-demo",
        json={"input": "天空为什么是蓝色的？", "mode": "encyclopedia"},
        headers=ph,
    )
    assert r.status_code == 200
    normal_steps = [s["step"] for s in r.json()["steps"]]
    assert "6" in normal_steps  # 批判审计始终执行


# ---------------------------------------------------------------------------
# v2.2 分龄工程 P0：新档位用例（docs/v2.2-拓展方向.md 3.2）
# ---------------------------------------------------------------------------


def test_age_tier_four_tiers_registration(client):
    """v2.2：注册接受新四档，拒绝已废弃的旧档位"""
    for tier in ("5-7", "8-10", "11-13", "14"):
        token = register_and_login(client, f"kid_tier_{tier.replace('-', '_')}", age_tier=tier)
        assert token

    # 旧档位已被新四档取代，注册校验拒绝
    r = client.post(
        "/api/auth/register",
        json={
            "username": "kid_old_tier",
            "pin": "1234",
            "age_tier": "8-11",
            "role": "child",
            "guardian_consent": True,
        },
    )
    assert r.status_code == 422


def test_age_tier_normalize_and_visibility():
    """core/age_tiers：旧档映射 + 三档可见性分组"""
    from core import age_tiers

    assert age_tiers.normalize_age_tier("8-11") == "8-10"
    assert age_tiers.normalize_age_tier("12-14") == "11-13"
    assert age_tiers.normalize_age_tier(None) == "8-10"
    assert age_tiers.normalize_age_tier("14") == "14"

    assert age_tiers.visibility_group("5-7") == "guardian"
    assert age_tiers.visibility_group("8-10") == "guardian"
    assert age_tiers.visibility_group("11-13") == "transition"
    assert age_tiers.visibility_group("14") == "trust"


def test_little_explorers_crisis_template(client):
    """v2.2：5-7 低龄档危机输入仍走危机模板拦截（安全闭环全档覆盖）"""
    parent_token = register_and_login(
        client, "parent_little", pin="0000", age_tier=None, role="parent"
    )
    kid_token = register_and_login(
        client, "kid_little", age_tier="5-7", parent_username="parent_little"
    )

    events = send_chat(client, kid_token, "我不想活了")
    done = next(d for e, d in events if e == "done")
    assert done["used_crisis_template"] is True
    assert done["risk_level"] == 3

    # 守护模式：危机模板路径也生成家长摘要/告警
    alerts = client.get("/api/parent/alerts", headers=auth_headers(parent_token)).json()[
        "alerts"
    ]
    assert any(a["risk_level"] == 3 for a in alerts)


def test_transition_mode_weekly_summary(client):
    """v2.2：过渡模式（11-13）周度摘要——7 天内仅一条常规摘要，高风险仍即时告警"""
    parent_token = register_and_login(
        client, "parent_trans", pin="0000", age_tier=None, role="parent"
    )
    kid_token = register_and_login(
        client, "kid_trans", age_tier="11-13", parent_username="parent_trans"
    )
    ph = auth_headers(parent_token)

    # 第一条零风险对话 → 生成本周第一条摘要
    send_chat(client, kid_token, "天空为什么是蓝色的？")
    alerts = client.get("/api/parent/alerts", headers=ph).json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["risk_level"] == 0

    # 7 天内第二条零风险对话 → 不重复生成摘要
    send_chat(client, kid_token, "月亮为什么有圆缺？")
    alerts = client.get("/api/parent/alerts", headers=ph).json()["alerts"]
    assert len(alerts) == 1

    # 高风险对话 → 不受周度限制，即时告警
    send_chat(client, kid_token, "我不想活了")
    alerts = client.get("/api/parent/alerts", headers=ph).json()["alerts"]
    assert any(a["risk_level"] == 3 for a in alerts)


def test_transition_mode_planet_overview_private(client):
    """v2.2：过渡模式（11-13）星球概览对家长不可见（孩子选择分享）"""
    parent_token = register_and_login(
        client, "parent_trans2", pin="0000", age_tier=None, role="parent"
    )
    register_and_login(
        client, "kid_trans2", age_tier="11-13", parent_username="parent_trans2"
    )
    ph = auth_headers(parent_token)

    dash = client.get("/api/parent/dashboard", headers=ph).json()
    kid_id = dash["children"][0]["id"]
    r = client.get("/api/parent/planet-overview", params={"child_id": kid_id}, headers=ph)
    assert r.status_code == 200
    assert r.json()["visible"] is False


# ---------------------------------------------------------------------------
# v2.2 亲子话题卡（B，docs/v2.2-拓展方向.md 第四节）
# ---------------------------------------------------------------------------

# 话题卡安全红线：产出不得包含的敏感词
_TOPIC_BANNED_WORDS = ["自杀", "自残", "不想活", "暴力", "血腥", "恐怖", "色情", "地址", "电话"]


def test_topic_card_safe_and_age_adapted(client):
    """亲子话题卡：年龄适配 + 不含敏感词（无 LLM 时走分龄预置库）"""
    from backend.services import cocreation_service

    kid_young = register_and_login(client, "kid_topic_y", age_tier="5-7")
    kid_old = register_and_login(client, "kid_topic_o", age_tier="14")

    r = client.post(
        "/api/cocreation/topic", headers=auth_headers(kid_young)
    )
    assert r.status_code == 200, r.text
    body_y = r.json()
    assert body_y["topic"]
    assert body_y["age_tier"] == "5-7"

    r = client.post("/api/cocreation/topic", headers=auth_headers(kid_old))
    body_o = r.json()
    assert body_o["topic"]
    assert body_o["age_tier"] == "14"

    # 敏感词过滤：低龄/高龄产出均不得触线
    for body in (body_y, body_o):
        assert not any(w in body["topic"] for w in _TOPIC_BANNED_WORDS)

    # 年龄适配（fallback 模式下来自分龄话题库）
    if body_y["source"] == "fallback":
        assert body_y["topic"] in cocreation_service._FALLBACK_TOPICS_YOUNGER
    if body_o["source"] == "fallback":
        assert body_o["topic"] in cocreation_service._FALLBACK_TOPICS_OLDER


def test_topic_card_not_counted_in_usage(client):
    """亲子话题卡是亲子活动引导，不走 chat/send，不计入 2 小时使用时长"""
    kid = register_and_login(client, "kid_topic_usage")
    h = auth_headers(kid)

    client.post("/api/cocreation/topic", headers=h)
    client.post("/api/cocreation/topic", headers=h)

    usage = client.get("/api/chat/history", headers=h).json()["usage_minutes"]
    assert usage == 0


# ---------------------------------------------------------------------------
# v2.2 共创故事（C，docs/v2.2-拓展方向.md 第五节）
# ---------------------------------------------------------------------------


def _start_story(client, token: str, title: str | None = None) -> dict:
    """发起一篇共创故事，返回响应 body"""
    body = {"title": title} if title else {}
    r = client.post(
        "/api/cocreation/story/start", json=body, headers=auth_headers(token)
    )
    assert r.status_code == 200, r.text
    return r.json()


def _add_turn(client, token: str, story_id: int, role: str, content: str):
    """接一段故事，返回原始 Response（由调用方断言状态码）"""
    return client.post(
        "/api/cocreation/story/turn",
        json={"story_id": story_id, "role": role, "content": content},
        headers=auth_headers(token),
    )


def test_cocreation_full_flow(client):
    """共创完整流程：start → 孩子接 → 家长接 → finalize → 自动种星球"""
    register_and_login(client, "parent_co", pin="0000", age_tier=None, role="parent")
    kid = register_and_login(client, "kid_co", parent_username="parent_co")
    h = auth_headers(kid)

    # 发起：AI 开头留白
    start = _start_story(client, kid, "会飞的小鲸鱼")
    assert start["opening"]
    story = start["story"]
    assert story["status"] == "active"
    assert [(t["role"], t["kind"]) for t in story["turns"]] == [("ai", "opening")]
    sid = story["id"]

    # 孩子接一段 → 追加 text + AI 轻量引导
    r = _add_turn(client, kid, sid, "child", "小鲸鱼泡泡飞到了云朵上，云朵像棉花糖。")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] is True
    assert body["ai_response"] is None
    roles = [(t["role"], t["kind"]) for t in body["story"]["turns"]]
    assert roles == [("ai", "opening"), ("child", "text"), ("ai", "guide")]

    # 家长接一段（同设备轮流）
    r = _add_turn(client, kid, sid, "parent", "泡泡用彩虹泡泡把迷路的小海鸥送回了家。")
    assert r.status_code == 200, r.text
    roles = [(t["role"], t["kind"]) for t in r.json()["story"]["turns"]]
    assert roles[-2:] == [("parent", "text"), ("ai", "guide")]

    # 完成润色：成品含孩子原文片段 + 共同作者标注
    r = client.post(
        "/api/cocreation/story/finalize", json={"story_id": sid}, headers=h
    )
    assert r.status_code == 200, r.text
    fin = r.json()
    assert fin["final_text"]
    assert "棉花糖" in fin["final_text"]  # 孩子输入的原文片段保留
    assert "kid_co" in fin["authors"] and "家人" in fin["authors"]
    assert fin["story"]["status"] == "done"
    assert fin["story"]["final_text"] == fin["final_text"]
    assert fin["planet_entry_id"]

    # 自动种小星球：source="cocreation" 的 story 条目
    entries = client.get("/api/planet/entries", headers=h).json()["entries"]
    co = [e for e in entries if e["source"] == "cocreation" and e["type"] == "story"]
    assert len(co) == 1
    assert co[0]["title"] == "会飞的小鲸鱼"
    assert co[0]["content"] == fin["final_text"]
    assert set(co[0]["tags"]) == {"故事", "共创"}


def test_cocreation_child_turn_safety_closure(client):
    """安全闭环：孩子输入高风险内容 → 拒绝存储原文，回应走危机模板"""
    kid = register_and_login(client, "kid_co_safe")
    h = auth_headers(kid)
    sid = _start_story(client, kid)["story"]["id"]

    r = _add_turn(client, kid, sid, "child", "我不想活了")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] is False
    assert "12355" in body["ai_response"]  # 危机模板路径天然安全
    # 该原文未进入 turns（不存储高风险原文）
    assert all("我不想活了" not in t["content"] for t in body["story"]["turns"])

    # 故事本身仍是 active，可继续正常共创
    r = _add_turn(client, kid, sid, "child", "小兔子种下了一颗星星种子。")
    assert r.status_code == 200 and r.json()["accepted"] is True


def test_cocreation_share_privacy(client):
    """隐私：成品默认孩子私密，share 后家长端可见；child 访问家长端点 403"""
    parent_token = register_and_login(
        client, "parent_co2", pin="0000", age_tier=None, role="parent"
    )
    kid = register_and_login(client, "kid_co2", parent_username="parent_co2")
    h = auth_headers(kid)
    ph = auth_headers(parent_token)

    # child 访问 family-stories → 403
    r = client.get("/api/cocreation/family-stories", headers=h)
    assert r.status_code == 403

    # 家长发起共创 → 403（共创由孩子发起）
    r = client.post("/api/cocreation/story/start", json={}, headers=ph)
    assert r.status_code == 403

    # 完成一篇故事（未分享）
    sid = _start_story(client, kid, "秘密故事")["story"]["id"]
    _add_turn(client, kid, sid, "child", "小兔子种下了一颗星星种子。")
    r = client.post("/api/cocreation/story/finalize", json={"story_id": sid}, headers=h)
    assert r.status_code == 200, r.text

    # 未分享 → 家长端为空
    assert client.get("/api/cocreation/family-stories", headers=ph).json()["stories"] == []

    # 分享后家长端可见（含孩子用户名与成品全文）
    r = client.post(f"/api/cocreation/story/{sid}/share", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["story"]["shared_with_parent"] is True
    stories = client.get("/api/cocreation/family-stories", headers=ph).json()["stories"]
    assert len(stories) == 1
    assert stories[0]["title"] == "秘密故事"
    assert stories[0]["child_username"] == "kid_co2"
    assert "星星种子" in stories[0]["final_text"]


def test_cocreation_not_counted_in_usage(client):
    """共创全程不计入 2 小时使用时长（亲子活动，不是 AI 使用）"""
    kid = register_and_login(client, "kid_co_usage")
    h = auth_headers(kid)

    sid = _start_story(client, kid)["story"]["id"]
    _add_turn(client, kid, sid, "child", "小恐龙豆豆在森林里散步。")
    _add_turn(client, kid, sid, "parent", "豆豆发现了一条发光的小溪。")
    client.post("/api/cocreation/story/finalize", json={"story_id": sid}, headers=h)

    usage = client.get("/api/chat/history", headers=h).json()["usage_minutes"]
    assert usage == 0


def test_cocreation_turn_limit_younger(client):
    """分龄轮次上限（5.4）：低龄（5-7）孩子+家长段合计上限 4 段"""
    kid = register_and_login(client, "kid_co_limit", age_tier="5-7")
    h = auth_headers(kid)
    sid = _start_story(client, kid)["story"]["id"]

    roles = ["child", "parent", "child", "parent"]
    for i, role in enumerate(roles):
        r = _add_turn(client, kid, sid, role, f"故事的第{i + 1}段。")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["accepted"] is True
        # 达到上限-1（第 3 段）时提示可以收尾
        assert body["suggest_finalize"] is (i + 1 >= 3)

    # 第 5 段 → 400，引导完成润色
    r = _add_turn(client, kid, sid, "child", "还想再接一段。")
    assert r.status_code == 400
    assert "完成润色" in r.json()["detail"]
