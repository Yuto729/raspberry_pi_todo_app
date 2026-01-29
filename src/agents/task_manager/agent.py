"""Task management agent using Claude Agent SDK."""

import asyncio
import sys
import time
from io import StringIO
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookContext,
    HookInput,
    HookJSONOutput,
    HookMatcher,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from ulid import ULID

from db import create_task, get_all_tasks, get_task_by_id, init_db, update_task

console = Console()

TASK_STATUSES = ["todo", "done", "archived"]
STATUS_LABELS = {"todo": "未完了", "done": "完了", "archived": "アーカイブ"}
STATUS_ICONS = {"todo": "⭕", "done": "✅", "archived": "📦"}

SYSTEM_PROMPT = """\
あなたはタスク管理専門のエージェントです。
ユーザーのメッセージを解釈し、適切なツールを使ってタスクを操作してください。
回答は簡潔な日本語で行ってください。

利用可能なツール:
- add_task: タスク追加（title必須）
- list_tasks: タスク一覧（statusでフィルタ可能: todo/done/archived）
- complete_task: タスク完了（タイトル部分一致またはID指定）

タスク管理以外のリクエストには対応できません。"""

# =============================================================================
# MCP Tools
# =============================================================================


@tool("add_task", "新しいタスクを追加します。", {"title": str})
async def add_task_tool(args: dict[str, Any]) -> dict[str, Any]:
    title = args.get("title", "").strip()
    if not title:
        return {"content": [{"type": "text", "text": "エラー: タイトルは空にできません"}]}

    task_id = str(ULID())
    created_at = int(time.time())
    task = create_task(task_id, title, created_at)
    return {
        "content": [
            {
                "type": "text",
                "text": f"タスクを追加しました: {task['title']}",
            }
        ]
    }


@tool(
    "list_tasks",
    "タスク一覧を表示します。statusでフィルタ可能（todo/done/archived）。省略時は全件。",
    {"status": str},
)
async def list_tasks_tool(args: dict[str, Any]) -> dict[str, Any]:
    status = args.get("status") or None
    if status and status not in TASK_STATUSES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"エラー: statusは {', '.join(TASK_STATUSES)} のいずれかです",
                }
            ]
        }

    tasks = get_all_tasks(status=status)
    if not tasks:
        label = STATUS_LABELS.get(status, "") if status else ""
        return {"content": [{"type": "text", "text": f"{label}タスクはありません"}]}

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim", width=8)
    table.add_column("タスク", style="bold", min_width=20)
    table.add_column("状態", justify="center", width=10)

    for task in tasks:
        icon = STATUS_ICONS.get(task["status"], "")
        label = STATUS_LABELS.get(task["status"], task["status"])
        table.add_row(task["id"][:8], task["title"], f"{icon} {label}")

    buf = StringIO()
    Console(file=buf, width=80, legacy_windows=False).print(table)
    return {"content": [{"type": "text", "text": buf.getvalue()}]}


@tool(
    "complete_task",
    "タスクを完了にします。タイトルの部分一致またはIDで指定してください。",
    {"query": str},
)
async def complete_task_tool(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query", "").strip()
    if not query:
        return {"content": [{"type": "text", "text": "エラー: タスクを指定してください"}]}

    # ID検索
    task = get_task_by_id(query)
    if not task:
        # タイトル部分一致
        tasks = get_all_tasks(status="todo")
        matches = [t for t in tasks if query in t["title"]]
        if len(matches) == 0:
            return {
                "content": [
                    {"type": "text", "text": f"'{query}' に一致するタスクが見つかりません"}
                ]
            }
        if len(matches) > 1:
            names = "\n".join(f"- {m['title']} (ID: {m['id'][:8]})" for m in matches)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"複数一致しました。もう少し具体的に指定してください:\n{names}",
                    }
                ]
            }
        task = matches[0]

    updated_at = int(time.time())
    update_task(task["id"], None, "done", updated_at)
    return {"content": [{"type": "text", "text": f"完了しました: {task['title']}"}]}


# =============================================================================
# Pre-tool Hook
# =============================================================================

ALLOWED_TOOLS = {
    "mcp__task_manager__add_task",
    "mcp__task_manager__list_tasks",
    "mcp__task_manager__complete_task",
}


async def restrict_tools(
    input_data: HookInput,
    tool_use_id: str | None,
    context: HookContext,
) -> HookJSONOutput:
    tool_name = input_data.get("tool_name", "")
    if tool_name in ALLOWED_TOOLS:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"{tool_name} は許可されていません。タスク操作ツールのみ使用可能です。",
        }
    }


# =============================================================================
# Display
# =============================================================================


def display_message(msg: Any) -> None:
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                console.print(
                    Panel(
                        Text(block.text),
                        title="Claude",
                        title_align="left",
                        border_style="blue",
                        padding=(0, 1),
                    )
                )
            elif isinstance(block, ToolUseBlock):
                input_str = ", ".join(f"{k}={v}" for k, v in block.input.items())
                console.print(
                    Panel(
                        f"[cyan]{block.name}[/cyan] {input_str}",
                        title="Tool",
                        title_align="left",
                        border_style="green",
                        padding=(0, 1),
                    )
                )
    elif isinstance(msg, ResultMessage) and msg.total_cost_usd:
        console.print(f"[dim]cost: ${msg.total_cost_usd:.6f}[/dim]")


# =============================================================================
# Main
# =============================================================================


async def interactive_mode() -> None:
    init_db()

    task_server = create_sdk_mcp_server(
        name="task_manager",
        version="1.0.0",
        tools=[add_task_tool, list_tasks_tool, complete_task_tool],
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"task_manager": task_server},
        allowed_tools=list(ALLOWED_TOOLS),
        hooks={"PreToolUse": [HookMatcher(hooks=[restrict_tools])]},
    )

    console.print(
        Panel(
            "タスク管理エージェント\n自然な日本語でタスクを操作できます。\n[dim]終了: quit[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )

    while True:
        console.print()
        user_input = Prompt.ask("[bold cyan]you[/bold cyan]").strip()

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[green]終了します。[/green]")
            break
        if not user_input:
            continue

        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_input)
            with console.status("[green]考え中...", spinner="dots") as status:
                async for message in client.receive_response():
                    status.stop()
                    display_message(message)
                    if isinstance(message, (AssistantMessage, SystemMessage)):
                        status.start()


async def main() -> None:
    try:
        await interactive_mode()
    except KeyboardInterrupt:
        console.print("\n[yellow]中断しました。[/yellow]")
    except Exception as e:
        Console(stderr=True).print(f"[red]エラー: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
