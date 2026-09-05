"""客服工具：订单查询、物流、退款试算、工单。供回复子 Agent 调用。"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

# 模拟订单中台。真实系统里这些会打到 OMS / 物流网关。
ORDERS: dict[str, dict[str, Any]] = {
    "A20240901": {
        "order_id": "A20240901",
        "status": "已发货",
        "sku": "WH-100",
        "product": "星云降噪耳机 Pro",
        "amount": 899.0,
        "paid_at": "2026-09-03 10:12",
        "shipped_at": "2026-09-03 18:40",
        "signed_at": None,
        "carrier": "顺丰",
        "tracking_no": "SF1092388123",
        "eta": "2026-09-06",
        "last_event": "快件已到达【成都转运中心】",
        "refundable": True,
        "refund_reason_hint": "仍在7天无理由窗口内（尚未签收）。",
    },
    "A20240888": {
        "order_id": "A20240888",
        "status": "已签收",
        "sku": "WH-100",
        "product": "星云降噪耳机 Pro",
        "amount": 899.0,
        "paid_at": "2026-08-28 09:01",
        "shipped_at": "2026-08-28 16:20",
        "signed_at": "2026-08-31 14:08",
        "carrier": "京东物流",
        "tracking_no": "JD009128811",
        "eta": "2026-08-31",
        "last_event": "已签收，签收人：本人",
        "refundable": True,
        "refund_reason_hint": "签收未满7天，可走无理由退货。",
    },
    "A20240700": {
        "order_id": "A20240700",
        "status": "已签收",
        "sku": "WATCH-S2",
        "product": "星云手表 S2",
        "amount": 1299.0,
        "paid_at": "2026-07-01 11:00",
        "shipped_at": "2026-07-01 19:00",
        "signed_at": "2026-07-04 12:30",
        "carrier": "中通",
        "tracking_no": "ZT88120011",
        "eta": "2026-07-04",
        "last_event": "已签收",
        "refundable": False,
        "refund_reason_hint": "已超过7天无理由期限；若为质量问题仍可走质保。",
    },
    "A20241002": {
        "order_id": "A20241002",
        "status": "待发货",
        "sku": "WH-100",
        "product": "星云降噪耳机 Pro",
        "amount": 899.0,
        "paid_at": "2026-09-05 08:22",
        "shipped_at": None,
        "signed_at": None,
        "carrier": None,
        "tracking_no": None,
        "eta": None,
        "last_event": "仓库拣货中",
        "refundable": True,
        "refund_reason_hint": "未发货，可直接取消订单并全额退款。",
    },
}


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


@tool
def lookup_order(order_id: str) -> str:
    """查询订单状态、商品、金额和签收时间。订单号通常形如 A20240901。"""
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return _dump({"ok": False, "error": f"未找到订单 {order_id}"})
    return _dump(
        {
            "ok": True,
            "order_id": order["order_id"],
            "status": order["status"],
            "product": order["product"],
            "sku": order["sku"],
            "amount": order["amount"],
            "paid_at": order["paid_at"],
            "shipped_at": order["shipped_at"],
            "signed_at": order["signed_at"],
        }
    )


@tool
def get_shipping_status(order_id: str) -> str:
    """查询物流公司、运单号、最新轨迹和预计送达时间。"""
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return _dump({"ok": False, "error": f"未找到订单 {order_id}"})
    return _dump(
        {
            "ok": True,
            "order_id": order["order_id"],
            "status": order["status"],
            "carrier": order["carrier"],
            "tracking_no": order["tracking_no"],
            "eta": order["eta"],
            "last_event": order["last_event"],
        }
    )


@tool
def calculate_refund(order_id: str, reason: str = "无理由退货") -> str:
    """试算可退金额，并结合签收时间判断是否仍在无理由窗口。"""
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return _dump({"ok": False, "error": f"未找到订单 {order_id}"})
    quality = "质量" in reason or "损坏" in reason or "划痕" in reason
    refundable = bool(order["refundable"] or quality)
    amount = float(order["amount"]) if refundable else 0.0
    return _dump(
        {
            "ok": True,
            "order_id": order["order_id"],
            "reason": reason,
            "refundable": refundable,
            "refund_amount": amount,
            "hint": order["refund_reason_hint"],
        }
    )


@tool
def create_ticket(category: str, summary: str, order_id: str = "") -> str:
    """创建人工跟进工单。category 如 complaint / refund / shipping。"""
    oid = (order_id or "NA").strip().upper()
    ticket_id = f"TK-{oid[-4:] if oid != 'NA' else '0000'}-01"
    return _dump(
        {
            "ok": True,
            "ticket_id": ticket_id,
            "category": category,
            "order_id": order_id or None,
            "summary": summary,
            "sla": "将在2小时内由人工客服回电或在线回复",
        }
    )


# 模拟库存 / 会员 / 质保。真实系统会打到 WMS、CRM、质保中台。
STOCK: dict[str, dict[str, Any]] = {
    "WH-100": {
        "sku": "WH-100",
        "product": "星云降噪耳机 Pro",
        "in_stock": True,
        "warehouse": "成都仓",
        "qty": 128,
        "preorder_days": 0,
    },
    "WATCH-S2": {
        "sku": "WATCH-S2",
        "product": "星云手表 S2",
        "in_stock": True,
        "warehouse": "华东仓",
        "qty": 46,
        "preorder_days": 0,
    },
    "CASE-WH": {
        "sku": "CASE-WH",
        "product": "耳机保护套",
        "in_stock": False,
        "warehouse": "华东仓",
        "qty": 0,
        "preorder_days": 7,
    },
}

MEMBER_POINTS: dict[str, dict[str, Any]] = {
    "A20240901": {"order_id": "A20240901", "points": 1280, "level": "银卡", "expiring": 200, "expire_at": "2026-12-31"},
    "A20240888": {"order_id": "A20240888", "points": 560, "level": "普通", "expiring": 60, "expire_at": "2026-10-31"},
    "A20240700": {"order_id": "A20240700", "points": 2100, "level": "金卡", "expiring": 0, "expire_at": None},
    "A20241002": {"order_id": "A20241002", "points": 80, "level": "普通", "expiring": 80, "expire_at": "2026-09-30"},
}

WARRANTIES: dict[str, dict[str, Any]] = {
    "A20240901": {"order_id": "A20240901", "sku": "WH-100", "status": "在保", "warranty_until": "2028-09-03", "months": 24},
    "A20240888": {"order_id": "A20240888", "sku": "WH-100", "status": "在保", "warranty_until": "2028-08-28", "months": 24},
    "A20240700": {"order_id": "A20240700", "sku": "WATCH-S2", "status": "在保", "warranty_until": "2028-07-01", "months": 24},
    "A20241002": {"order_id": "A20241002", "sku": "WH-100", "status": "待激活", "warranty_until": None, "months": 24},
}


def _resolve_sku(sku: str = "", product: str = "") -> str | None:
    key = (sku or "").strip().upper()
    if key in STOCK:
        return key
    name = (product or "").strip()
    for item_sku, item in STOCK.items():
        title = str(item.get("product") or "")
        if name and (name in title or title in name):
            return item_sku
    if "耳机" in name:
        return "WH-100"
    if "手表" in name or "s2" in name.lower():
        return "WATCH-S2"
    return None


@tool
def check_stock(sku: str = "", product: str = "") -> str:
    """查询商品现货库存、仓位和缺货预售天数。sku 如 WH-100，或传商品名。"""
    resolved = _resolve_sku(sku, product)
    if not resolved:
        return _dump({"ok": False, "error": "未识别商品，请提供型号（WH-100 / WATCH-S2）或商品名"})
    item = STOCK[resolved]
    return _dump({"ok": True, **item})


@tool
def lookup_member_points(order_id: str = "", phone_last4: str = "") -> str:
    """查询会员积分、等级和即将过期积分。可凭订单号；手机尾号目前仅作备注。"""
    oid = (order_id or "").strip().upper()
    member = MEMBER_POINTS.get(oid)
    if not member:
        return _dump(
            {
                "ok": False,
                "error": "未找到会员积分，请提供订单号",
                "phone_last4": phone_last4 or None,
            }
        )
    return _dump({"ok": True, "phone_last4": phone_last4 or None, **member})


@tool
def check_warranty(order_id: str) -> str:
    """查询订单商品是否在保、质保截止日期。"""
    oid = (order_id or "").strip().upper()
    item = WARRANTIES.get(oid)
    if not item:
        return _dump({"ok": False, "error": f"未找到订单 {order_id} 的质保记录"})
    return _dump({"ok": True, **item})


CUSTOMER_TOOLS = [
    lookup_order,
    get_shipping_status,
    calculate_refund,
    create_ticket,
    check_stock,
    lookup_member_points,
    check_warranty,
]
TOOL_BY_NAME = {t.name: t for t in CUSTOMER_TOOLS}


def invoke_tool(name: str, args: dict[str, Any]) -> str:
    """启发式模式直接执行工具，保持与 ToolNode 相同的返回字符串。"""
    fn = TOOL_BY_NAME.get(name)
    if fn is None:
        return _dump({"ok": False, "error": f"未知工具 {name}"})
    return fn.invoke(args)
