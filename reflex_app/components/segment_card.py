"""Render one transcript segment and its matched media."""

from __future__ import annotations

import reflex as rx

from ..schemas import MediaVM, SegmentVM


def _image_item(m: MediaVM) -> rx.Component:
    return rx.box(
        rx.image(
            src=m.url,
            width="100%",
            height="120px",
            object_fit="cover",
            border_radius="6px",
        ),
        rx.text(m.attribution, size="1", color_scheme="gray"),
    )


def _video_item(m: MediaVM) -> rx.Component:
    return rx.box(
        rx.video(src=m.url, width="100%", height="160px"),
        rx.text(m.attribution, size="1", color_scheme="gray"),
    )


def segment_card(seg: SegmentVM) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(seg.time_label, variant="soft"),
                rx.text(seg.search_query, weight="bold"),
                align="center",
                spacing="3",
                wrap="wrap",
            ),
            rx.text(seg.text, size="2", color_scheme="gray"),
            rx.cond(
                seg.images.length() > 0,
                rx.grid(
                    rx.foreach(seg.images, _image_item),
                    columns="3",
                    spacing="2",
                    width="100%",
                ),
            ),
            rx.cond(
                seg.videos.length() > 0,
                rx.grid(
                    rx.foreach(seg.videos, _video_item),
                    columns="2",
                    spacing="2",
                    width="100%",
                ),
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
    )
