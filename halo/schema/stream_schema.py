"""Pydantic contracts for streaming the monitored video to a chosen IP address."""

from ipaddress import IPv4Address, IPv6Address

from pydantic import Field, IPvAnyAddress

from bas_har.schema.plan_schema import StrictModel

STREAM_URL_PREFIX = "udp://"


class StreamOutputSettings(StrictModel):
    enabled: bool = False
    host: IPvAnyAddress = Field(
        default=IPv4Address("127.0.0.1"),
        description="Receiving computer's IP address; a multicast group also works.",
    )
    port: int = Field(default=5000, ge=1024, le=65535)
    fps: int = Field(default=15, ge=1, le=60)
    bitrate_kbps: int = Field(default=2500, ge=200, le=20000)

    @property
    def target(self) -> str:
        host = f"[{self.host}]" if isinstance(self.host, IPv6Address) else str(self.host)
        return f"{host}:{self.port}"

    @property
    def url(self) -> str:
        return f"{STREAM_URL_PREFIX}{self.target}?pkt_size=1316"

    @property
    def player_url(self) -> str:
        return f"udp://@:{self.port}"

    @classmethod
    def from_url(cls, url: str) -> "StreamOutputSettings":
        """Settings from `udp://<ip>:<port>`, enabled."""
        if not url.startswith(STREAM_URL_PREFIX):
            raise ValueError("stream target must look like udp://<ip>:<port>")
        address = url.removeprefix(STREAM_URL_PREFIX).split("?", 1)[0]
        host, separator, port = address.rpartition(":")
        if not separator or not port.isdigit():
            raise ValueError("stream target must include a port, like udp://192.168.1.20:5000")
        return cls(enabled=True, host=host.strip("[]"), port=int(port))


class StreamOutputStatus(StrictModel):
    enabled: bool
    target: str
    player_url: str
    frames_sent: int = Field(default=0, ge=0)
    codec: str | None = None
    error: str | None = None
