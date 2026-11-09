"""从 8 周计划 HTML 中抽取 T / V / M 三条线的任务卡。

用法：python scripts/extract_plan.py /path/to/8week-plan.html
输出：plan/scheduler-roadmap.md、plan/volcano-roadmap.md、plan/lm-roadmap.md
"""
import html
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "plan/8week-plan.html"

with open(SRC, encoding="utf-8") as f:
    raw = f.read()

raw = re.sub(r"<style.*?</style>", "", raw, flags=re.S)
raw = re.sub(r"<script.*?</script>", "", raw, flags=re.S)


def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(
        r"<code>(.*?)</code>",
        lambda m: "`" + re.sub(r"<[^>]+>", "", m.group(1)) + "`",
        s,
        flags=re.S,
    )
    s = re.sub(
        r"<b>(.*?)</b>",
        lambda m: "**" + re.sub(r"<[^>]+>", "", m.group(1)) + "**",
        s,
        flags=re.S,
    )
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


tiers = []
for m in re.finditer(r'<div class="tier">(.*?)</div>', raw, re.S):
    block = m.group(1)
    tg = re.search(r'<span class="tg">(.*?)</span>', block, re.S)
    tt = re.search(r'<span class="tt">(.*?)</span>', block, re.S)
    td = re.search(r'<span class="td">(.*?)</span>', block, re.S)
    tiers.append({
        "pos": m.start(),
        "tg": clean(tg.group(1)) if tg else "",
        "tt": clean(tt.group(1)) if tt else "",
        "td": clean(td.group(1)) if td else "",
    })

starts = [m.start() for m in re.finditer(r'<div class="task">', raw)]
markers = sorted([t["pos"] for t in tiers] + starts + [len(raw)])

all_tasks = []
for s in starts:
    end = min(x for x in markers if x > s)
    block = raw[s:end]
    tid = re.search(r'<span class="tid[^"]*">([^<]+)</span>', block)
    if not tid:
        continue
    tid = clean(tid.group(1))
    nm = re.search(r'<span class="nm">(.*?)</span>', block, re.S)
    mins = re.search(r'<span class="mins">(.*?)</span>', block, re.S)
    rows = re.findall(
        r'<span class="lb">(问题|动作|交付|验收|卡点)</span>(.*?)</div>',
        block,
        re.S,
    )
    tier = ""
    for t in tiers:
        if t["pos"] < s:
            tier = t
    all_tasks.append({
        "tid": tid,
        "name": clean(nm.group(1)) if nm else "",
        "mins": clean(mins.group(1)) if mins else "",
        "rows": [(label, clean(text)) for label, text in rows],
        "tier": tier,
    })


def render(prefix, title, intro, weeks, out):
    tasks = [t for t in all_tasks if t["tid"].startswith(prefix)]
    lines = []
    lines.append("# " + title)
    lines.append("")
    lines.append(intro)
    lines.append("")
    lines.append("## 周次映射")
    lines.append("")
    lines.append("| 周 | 必做 | 弹性 |")
    lines.append("|---|---|---|")
    for row in weeks:
        lines.append("| {} | {} | {} |".format(*row))
    lines.append("")

    current = None
    for t in tasks:
        tier = t["tier"]
        key = (tier["tg"], tier["tt"]) if tier else ("", "")
        if key != current:
            current = key
            lines.append("")
            if tier:
                lines.append("## {} · {}".format(tier["tg"], tier["tt"]))
                if tier["td"]:
                    lines.append("")
                    lines.append("> " + tier["td"])
            else:
                lines.append("## 未分组")
            lines.append("")
        lines.append("### {} {}".format(t["tid"], t["name"]))
        lines.append("")
        if t["mins"]:
            lines.append("**时长**：{}".format(t["mins"]))
            lines.append("")
        for label, text in t["rows"]:
            lines.append("- **{}**：{}".format(label, text.replace("\n", " ")))
        lines.append("")

    with open(out, "w", encoding="utf-8") as f:
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        f.write(text)
    print("{}: {} cards -> {}".format(prefix, len(tasks), out))


render(
    "T",
    "Scheduler 学习路线图（16 张任务卡）",
    "\n".join([
        "> 来源：《8 周学习 + 健身执行计划（源码攻坚版）》T 系列任务卡。",
        "> 线定位：调度的地基——单个 Pod 怎么选节点。",
        "> 用途：换机器后的完整考纲。每张卡都带问题 / 动作 / 交付 / 验收 / 卡点，验收时直接按「验收」一行考。",
        "",
        "## 阅读顺序（原文）",
        "",
        "`interface.go` 是字典，`schedule_one.go` 是小说。顺序是：",
        "",
        "1. 先看它跑（T0-1）",
        "2. 让它失败一次（T0-2）",
        "3. 追一次成功路径（T1-1）",
        "4. 遇到不认识的名字，才回去查 `interface.go`",
    ]),
    [
        ("W1", "T0-1 / T0-2 / T1-1", "T1-2"),
        ("W2", "T2-0 / T2-1 / T2-2", "T1-3"),
        ("W4", "T2-3 / T2-4 / T3-1", "T3-3"),
        ("W7", "—", "T3-2"),
        ("W8", "T5-1", "—"),
        ("收口", "T4-1 / T4-2", "—"),
    ],
    "plan/scheduler-roadmap.md",
)

render(
    "V",
    "Volcano 学习路线图（8 张任务卡）",
    "\n".join([
        "> 来源：《8 周学习 + 健身执行计划（源码攻坚版）》V 系列任务卡。",
        "> 线定位：你集群里真正在跑的那层——一批 Pod 怎么一起动。",
        "> 用途：从排障表 → 架构 → 核心插件 → 自己写插件。",
    ]),
    [
        ("W5", "V0-1 / V0-2 / V0-3", "—"),
        ("W6", "V1-1 / V1-2 / V2-1", "—"),
        ("W7", "V2-2 / V3-1", "—"),
    ],
    "plan/volcano-roadmap.md",
)

render(
    "M",
    "大模型框架学习路线图（9 张任务卡）",
    "\n".join([
        "> 来源：《8 周学习 + 健身执行计划（源码攻坚版）》M 系列任务卡。",
        "> 线定位：被调度的负载——它对调度提了哪些要求。",
        "> 用途：M0 体感 → M1 推理 → M2 训练 → M3 会师。",
    ]),
    [
        ("W3", "M0-1 / M0-2 / M1-1", "—"),
        ("W6", "—", "M1-2"),
        ("W7", "M2-1", "M2-2"),
        ("W8", "M3-2", "—"),
    ],
    "plan/lm-roadmap.md",
)
