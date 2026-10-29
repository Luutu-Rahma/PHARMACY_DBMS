from fastapi import Request

import web.security as security


def test_cashier_cannot_access_inventory(monkeypatch):
    monkeypatch.setattr(
        security,
        "get_current_user",
        lambda request: {"userid": 4, "fullname": "Cashier", "role": "Cashier"},
    )
    request = Request({"type": "http", "headers": [], "session": {"user_id": 4}})

    try:
        security.require_role(request, "Admin", "InventoryManager")
    except security.PermissionDenied:
        pass
    else:
        raise AssertionError("Cashier should not be authorized to manage inventory")


def test_pharmacist_can_access_read_only_reports(monkeypatch):
    monkeypatch.setattr(
        security,
        "get_current_user",
        lambda request: {"userid": 3, "fullname": "Pharmacist", "role": "Pharmacist"},
    )
    request = Request({"type": "http", "headers": [], "session": {"user_id": 3}})

    user = security.require_role(request, "Admin", "InventoryManager", "Pharmacist")
    assert user["role"] == "Pharmacist"
