"""Unit tests for reqivo.utils.websocket_utils module."""

import struct

from reqivo.utils.websocket_utils import (
    OPCODE_BINARY,
    OPCODE_CLOSE,
    OPCODE_TEXT,
    WebSocketError,
    apply_mask,
    create_frame,
    parse_frame_header,
)


class TestWebSocketError:
    """Tests for WebSocketError exception."""

    def test_websocket_error(self):
        """Test WebSocketError can be raised."""
        assert issubclass(WebSocketError, Exception)

        error = WebSocketError("Test error")
        assert str(error) == "Test error"


class TestApplyMask:
    """Tests for apply_mask function."""

    def test_apply_mask_with_data(self):
        """Test XOR masking with data."""
        data = b"Hello"
        mask = b"\x12\x34\x56\x78"
        masked = apply_mask(data, mask)

        # Verify it's different
        assert masked != data

        # Verify it's reversible
        unmasked = apply_mask(masked, mask)
        assert unmasked == data

    def test_apply_mask_empty_mask(self):
        """Test apply_mask with empty mask returns data unchanged."""
        data = b"Test data"
        masked = apply_mask(data, b"")
        assert masked == data

    def test_apply_mask_xor_property(self):
        """Test that apply_mask correctly XORs each byte."""
        data = b"\x00\x00\x00\x00"
        mask = b"\xab\xcd\xef\x12"
        masked = apply_mask(data, mask)
        assert masked == mask  # XOR with 0 returns the mask


class TestCreateFrame:
    """Tests for create_frame function."""

    def test_create_frame_small_payload(self):
        """Test creating frame with small payload (<= 125 bytes)."""
        payload = b"Hello"
        frame = create_frame(payload, opcode=OPCODE_TEXT, mask=False)

        # Verify frame structure
        assert len(frame) >= 2 + len(payload)
        b0 = frame[0]
        assert b0 & 0x80  # FIN bit set
        assert (b0 & 0x0F) == OPCODE_TEXT

    def test_create_frame_medium_payload(self):
        """Test creating frame with medium payload (126-65535 bytes)."""
        payload = b"A" * 200
        frame = create_frame(payload, opcode=OPCODE_BINARY, mask=False)

        # Verify extended payload length encoding
        b1 = frame[1]
        assert (b1 & 0x7F) == 126  # Extended 16-bit length

        # Verify payload length is encoded correctly
        payload_len = struct.unpack("!H", frame[2:4])[0]
        assert payload_len == 200

    def test_create_frame_large_payload(self):
        """Test creating frame with large payload (> 65535 bytes)."""
        payload = b"B" * 70000
        frame = create_frame(payload, opcode=OPCODE_BINARY, mask=False)

        # Verify 64-bit length encoding
        b1 = frame[1]
        assert (b1 & 0x7F) == 127  # Extended 64-bit length

        payload_len = struct.unpack("!Q", frame[2:10])[0]
        assert payload_len == 70000

    def test_create_frame_with_mask(self):
        """Test creating masked frame."""
        payload = b"Secret"
        frame = create_frame(payload, opcode=OPCODE_TEXT, mask=True)

        # Verify mask bit is set
        b1 = frame[1]
        assert b1 & 0x80  # Mask bit set

        # Frame should include 4-byte mask key
        assert len(frame) >= 2 + 4 + len(payload)

    def test_create_frame_close(self):
        """Test creating CLOSE frame."""
        frame = create_frame(b"", opcode=OPCODE_CLOSE, mask=False)

        b0 = frame[0]
        assert (b0 & 0x0F) == OPCODE_CLOSE


class TestParseFrameHeader:
    """Tests for parse_frame_header function."""

    def test_parse_simple_frame_header(self):
        """Test parsing simple frame header."""
        # TEXT frame, FIN=1, unmasked, len=5
        data = b"\x81\x05Hello"
        result = parse_frame_header(data)

        assert result is not None
        header_len, payload_len, fin, rsv1, rsv2, rsv3, opcode, masked = result
        assert header_len == 2
        assert payload_len == 5
        assert fin is True
        assert opcode == OPCODE_TEXT
        assert masked is False

    def test_parse_masked_frame_header(self):
        """Test parsing masked frame header."""
        # TEXT frame, FIN=1, masked, len=5
        data = b"\x81\x85\x12\x34\x56\x78xxxxx"
        result = parse_frame_header(data)

        assert result is not None
        header_len, payload_len, fin, rsv1, rsv2, rsv3, opcode, masked = result
        assert masked is True
        assert header_len == 6  # 2 + 4 (mask key)

    def test_parse_extended_16bit_length(self):
        """Test parsing frame with 16-bit extended length."""
        # FIN=1, BINARY, unmasked, len=126 (triggers 16-bit)
        payload_len = 200
        data = b"\x82\x7e" + struct.pack("!H", payload_len)
        result = parse_frame_header(data)

        assert result is not None
        header_len, parsed_len, fin, rsv1, rsv2, rsv3, opcode, masked = result
        assert parsed_len == 200
        assert header_len == 4

    def test_parse_extended_64bit_length(self):
        """Test parsing frame with 64-bit extended length."""
        # FIN=1, BINARY, unmasked, len=127 (triggers 64-bit)
        payload_len = 70000
        data = b"\x82\x7f" + struct.pack("!Q", payload_len)
        result = parse_frame_header(data)

        assert result is not None
        header_len, parsed_len, fin, rsv1, rsv2, rsv3, opcode, masked = result
        assert parsed_len == 70000
        assert header_len == 10

    def test_parse_incomplete_header(self):
        """Test parsing incomplete header returns None."""
        # Only 1 byte (need at least 2)
        data = b"\x81"
        result = parse_frame_header(data)
        assert result is None

    def test_parse_incomplete_extended_16bit(self):
        """Test parsing incomplete 16-bit extended length returns None."""
        # Extended 16-bit marker but missing length bytes
        data = b"\x81\x7e\x00"  # Need 2 bytes for length
        result = parse_frame_header(data)
        assert result is None

    def test_parse_incomplete_extended_64bit(self):
        """Test parsing incomplete 64-bit extended length returns None."""
        # Extended 64-bit marker but missing length bytes
        data = b"\x81\x7f\x00\x00\x00\x00"  # Need 8 bytes for length
        result = parse_frame_header(data)
        assert result is None

    def test_parse_incomplete_masked_frame(self):
        """Test parsing frame with mask bit but incomplete mask key."""
        # Masked but only 2 bytes of mask key (need 4)
        data = b"\x81\x85\x12\x34"
        result = parse_frame_header(data)
        assert result is None

    def test_parse_rsv_bits(self):
        """Test parsing RSV bits."""
        # Set RSV1, RSV2, RSV3 bits
        data = b"\xf1\x00"  # FIN=1, RSV1=1, RSV2=1, RSV3=1, opcode=1
        result = parse_frame_header(data)

        assert result is not None
        header_len, payload_len, fin, rsv1, rsv2, rsv3, opcode, masked = result
        assert rsv1 == 1
        assert rsv2 == 1
        assert rsv3 == 1

    def test_parse_fragmented_frame(self):
        """Test parsing fragmented frame (FIN=0)."""
        # FIN=0, TEXT, unmasked, len=5
        data = b"\x01\x05Hello"
        result = parse_frame_header(data)

        assert result is not None
        header_len, payload_len, fin, rsv1, rsv2, rsv3, opcode, masked = result
        assert fin is False
        assert opcode == OPCODE_TEXT
