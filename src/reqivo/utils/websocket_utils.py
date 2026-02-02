"""src/reqivo/utils/websocket_utils.py

WebSocket utilities for Reqivo.
"""

import os
import struct
from typing import Optional, Tuple

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


class WebSocketError(Exception):
    """Exception raised for WebSocket-related errors."""


def apply_mask(data: bytes, mask: bytes) -> bytes:
    """Apply XOR mask to data."""
    if not mask:
        return data
    return bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def create_frame(payload: bytes, opcode: int, mask: bool = True) -> bytes:
    """Create a WebSocket frame."""
    b0 = 0x80 | (opcode & 0x0F)  # FIN=1 + Opcode

    payload_len = len(payload)
    if payload_len <= 125:
        b1 = (0x80 if mask else 0x00) | payload_len
        header = struct.pack("!BB", b0, b1)

    elif payload_len <= 0xFFFF:
        b1 = (0x80 if mask else 0x00) | 126
        header = struct.pack("!BBH", b0, b1, payload_len)

    else:
        b1 = (0x80 if mask else 0x00) | 127
        header = struct.pack("!BBQ", b0, b1, payload_len)

    if mask:
        mask_key = os.urandom(4)
        header += mask_key
        payload = apply_mask(payload, mask_key)

    return header + payload


def parse_frame_header(
    data: bytes,
) -> Optional[Tuple[int, int, bool, int, int, int, int, bool]]:
    """
    Parse WebSocket frame header.
    Returns: (header_len, payload_len, fin, rsv1, rsv2, rsv3, opcode, masked)
    """
    if len(data) < 2:
        return None

    b0 = data[0]
    b1 = data[1]

    fin = bool(b0 & 0x80)
    rsv1 = (b0 & 0x40) >> 6
    rsv2 = (b0 & 0x20) >> 5
    rsv3 = (b0 & 0x10) >> 4
    opcode = b0 & 0x0F

    masked = bool(b1 & 0x80)
    payload_len = b1 & 0x7F

    offset = 2
    if payload_len == 126:
        if len(data) < 4:
            return None
        payload_len = struct.unpack_from("!H", data, offset)[0]
        offset += 2

    elif payload_len == 127:
        if len(data) < 10:
            return None
        payload_len = struct.unpack_from("!Q", data, offset)[0]
        offset += 8

    if masked:
        if len(data) < offset + 4:
            return None
        offset += 4

    return offset, payload_len, fin, rsv1, rsv2, rsv3, opcode, masked
