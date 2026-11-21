"""Entry point: ``python -m checkbaby_engine [--config FILE]``."""

from __future__ import annotations

import argparse
import logging
import math
import signal
import sys
import threading
from collections.abc import Sequence

from .capture import FrameSource, RtspSource, SyntheticSource
from .config import Config, ConfigError, load_config
from .publisher import Publisher
from .runner import Engine
from .signal import BreathingAnalyzer

_LOGGER = logging.getLogger("checkbaby_engine")

SYNTHETIC_SCHEME = "synthetic://"


def build_source(config: Config) -> FrameSource:
    """RTSP reader, or for ``synthetic://<breaths per minute>`` a test pattern."""
    if config.rtsp_url.startswith(SYNTHETIC_SCHEME):
        try:
            hz = float(config.rtsp_url.removeprefix(SYNTHETIC_SCHEME) or 40.0) / 60.0
        except ValueError:
            raise ConfigError("synthetic:// takes breaths per minute, e.g. synthetic://40") from None
        _LOGGER.warning("synthetic test pattern in use: no camera is being watched")
        return SyntheticSource(
            displacement=lambda t: 0.3 * math.sin(2.0 * math.pi * hz * t),
            fps=config.fps,
            duration_s=math.inf,
            realtime=True,
        )
    return RtspSource(config.rtsp_url, config.roi, config.fps, config.frame_width)


def install_signal_handlers(stop: threading.Event) -> None:
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="checkbaby_engine", description=__doc__)
    parser.add_argument("--config", help="YAML or JSON file (default: $CHECKBABY_CONFIG)")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        logging.basicConfig(
            level=config.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
        source = build_source(config)
    except ConfigError as err:
        print(f"configuration error: {err}", file=sys.stderr)
        return 2
    _LOGGER.info("starting: %s", config.describe())
    _LOGGER.info("this is a breathing-movement hint, not a medical monitor")
    stop = threading.Event()
    install_signal_handlers(stop)
    engine = Engine(source, BreathingAnalyzer(config.signal), Publisher(config.mqtt, config.engine_id))
    engine.run(stop)
    _LOGGER.info("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
