"""Dữ liệu demo lưu trong RAM (reset khi restart backend)."""
from __future__ import annotations

from typing import Any

DEFAULT_VIDEOS = [
    {
        "id": 1,
        "duration": "1:32",
        "source": "Từ app",
        "category": "Quan điểm",
        "title": "Không giới nói thì quay trợn, AI edit cho",
        "description": "Hôm nay · Bản review",
        "views": "1.240",
        "status": "done",
        "platforms": ["facebook", "youtube", "tiktok"],
    },
    {
        "id": 2,
        "duration": "2:05",
        "source": "Từ máy",
        "category": "Show tính năng",
        "title": "Edit video bằng cái video ngắn",
        "description": "Hôm qua",
        "views": "1.240",
        "status": "processing",
        "platforms": ["facebook", "youtube"],
    },
]

state: dict[str, Any] = {
    "videos": [item.copy() for item in DEFAULT_VIDEOS],
    "schedule": {
        14: [
            {
                "id": 1,
                "time": "08:00",
                "title": "3 lỗi khi quay video bằng điện thoại",
                "channels": ["facebook", "tiktok"],
                "status": "Đã đăng",
                "type": "published",
            },
            {
                "id": 2,
                "time": "20:30",
                "title": "Không giới nội thì quay trơn",
                "channels": ["facebook", "youtube", "tiktok"],
                "status": "Đã lên lịch",
                "type": "scheduled",
            },
        ],
        15: [
            {
                "id": 3,
                "time": "11:30",
                "title": "Show tính năng: dựng video 2 phút",
                "channels": ["facebook"],
                "status": "Đang dựng",
                "type": "draft",
            },
        ],
    },
    "analytics": {
        "7 ngày": {
            "views": "25.032",
            "growth": "+18%",
            "videos": [
                {"id": 1, "title": "Không giỏi nói thì quay trơn", "views": "12.480", "comments": "312", "rank": 1},
                {"id": 2, "title": "Dựng 1 video chỉ mất 2 phút", "views": "6.902", "comments": "98", "rank": 2},
            ],
        },
        "30 ngày": {
            "views": "89.520",
            "growth": "+25%",
            "videos": [
                {"id": 1, "title": "Không giỏi nói thì quay trơn", "views": "12.480", "comments": "312", "rank": 1},
                {"id": 2, "title": "Dựng 1 video chỉ mất 2 phút", "views": "6.902", "comments": "98", "rank": 2},
            ],
        },
        "90 ngày": {
            "views": "245.800",
            "growth": "+32%",
            "videos": [
                {"id": 1, "title": "Không giỏi nói thì quay trơn", "views": "12.480", "comments": "312", "rank": 1},
                {"id": 2, "title": "Dựng 1 video chỉ mất 2 phút", "views": "6.902", "comments": "98", "rank": 2},
            ],
        },
    },
    "channels": [
        {
            "name": "Facebook",
            "description": "Fanpage nhu.digitalmkt",
            "icon": "f",
            "color": "#1877F2",
            "status": "Đã kết nối",
            "type": "connected",
        },
        {
            "name": "YouTube",
            "description": "Nhu Digital",
            "icon": "▶",
            "color": "#FF0000",
            "status": "Đã kết nối",
            "type": "connected",
        },
        {
            "name": "TikTok",
            "description": "@nhu.digitalmkt",
            "icon": "♪",
            "color": "#101827",
            "status": "Hết hạn",
            "type": "expired",
        },
        {
            "name": "Instagram",
            "description": "Chưa kết nối",
            "icon": "IG",
            "color": "#E1306C",
            "status": "Kết nối",
            "type": "disconnected",
        },
        {
            "name": "Website",
            "description": "nhudigital.vn/blog",
            "icon": "W",
            "color": "#526783",
            "status": "Đã kết nối",
            "type": "connected",
        },
    ],
    "notifications": [
        {"name": "Thông báo trên app", "icon": "♧", "enabled": True},
        {"name": "Zalo", "icon": "◉", "enabled": True},
        {"name": "Telegram", "icon": "➤", "enabled": False},
    ],
}
