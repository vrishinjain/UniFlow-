import reflex as rx

import ast
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANGED_PYTHON = (
    "UniFlow_/workspace_services.py",
    "UniFlow_/states/workspace_state.py",
    "UniFlow_/components/workspace.py",
    "UniFlow_/components/student.py",
    "UniFlow_/states/login_state.py",
    "UniFlow_/UniFlow_.py",
    "UniFlow_/chat_services.py",
    "UniFlow_/states/chat_state.py",
    "UniFlow_/components/workspace_chat.py",
    "UniFlow_/states/workspace_tab_state.py",
)


def main() -> None:
    """Syntax and component construction only: no services, fixtures, or DB reads."""
    for relative_path in CHANGED_PYTHON:
        ast.parse((ROOT / relative_path).read_text(), filename=relative_path)
    services = ast.parse((ROOT / "UniFlow_/workspace_services.py").read_text())
    expected = {"authorize_workspace", "get_workspace_team", "get_workspace"}
    defined = {
        node.name for node in services.body if isinstance(node, ast.FunctionDef)
    }
    assert expected <= defined
    importlib.import_module("UniFlow_.UniFlow_")
    from UniFlow_.components.workspace import workspace_portal

    from UniFlow_.components.workspace_chat import workspace_chat

    assert isinstance(workspace_chat(), rx.Component)
    component = workspace_portal()
    assert isinstance(component, rx.Component)
    assert component.render()
    print(
        "Workspace syntax and component construction checks passed; no database operations executed."
    )


if __name__ == "__main__":
    main()
