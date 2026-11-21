# CheckBaby Vital Engine

A small standalone process that watches a low-resolution RTSP sub-stream (from go2rtc), looks for
breathing-like micro-motion in a region of interest and publishes what it finds over MQTT. The
CheckBaby Home Assistant integration consumes these messages.

**This is a breathing-movement hint, not a medical monitor.** It cannot detect or prevent SIDS, it
misses things and it raises false hints. Keep following safe-sleep guidance and keep a plain audio
baby monitor as a fallback. The thresholds in this directory were tuned on synthetic data only;
tuning on real footage is still required. Any alarm built on this signal is gated behind a "shadow
mode" in the integration (log only, evaluate for at least two weeks, then decide).

## What it does

- Pulls the stream with PyAV, drops to about 8 frames per second, converts to grayscale, cuts the
  region of interest and shrinks it to about 64 pixels width.
- Splits the picture into 8 x 8 blocks and follows each block's brightness relative to the mean
  brightness of the whole region. A chest moving by a fraction of a pixel shows up as a small
  periodic change in the blocks that contain an edge or a fold.
- About once per second it analyses the last 12 to 25 seconds: detrend, Hann window, FFT per block,
  spectra averaged over the blocks, strongest component between 0.3 and 1.5 Hz (18 to 90
  breaths per minute). The confidence is the share of in-band power in that component that stands
  out above the noise floor.
- Separately it measures gross motion: the mean change of the blocks over half a second.
- It reports one of four statuses, and it is strict about one thing: missing or bad data is
  `unusable`, never `no_motion`.

## What it does not do

- No medical measurement, no oxygen, no heart rate, no apnoea diagnosis.
- No Eulerian video magnification, no pose or face detection, no automatic placement of the
  region of interest. It does not know whether a child is in the picture; presence has to come
  from elsewhere (the integration combines it with Frigate zones and other sensors).
- No recording. Frames are analysed in memory and discarded. Nothing is sent anywhere except the
  MQTT messages described below.
- No alarm logic. Whether and when to alert is decided in the integration.

## MQTT contract

Topic prefix `checkbaby/engine` (configurable), `<engine_id>` from the configuration.

| Topic | Payload | Retained |
|---|---|---|
| `checkbaby/engine/<engine_id>/availability` | `online` / `offline`. `offline` is the last will and is also published on a clean shutdown. | yes |
| `checkbaby/engine/<engine_id>/state` | JSON, see below. About every 2 seconds, and at once when the status changes. | no |

```json
{"status": "periodic", "rate": 41.3, "confidence": 0.87, "motion": 0.42, "ts": 1795280308.569}
```

| Field | Meaning |
|---|---|
| `status` | `periodic`, `gross_motion`, `no_motion` or `unusable` (exact strings) |
| `rate` | breaths per minute as a float; `null` unless `status` is `periodic` |
| `confidence` | 0..1; 0 for `gross_motion` and `unusable` |
| `motion` | gross motion measure of the newest frame, in percent of mean brightness; 0 when `unusable` |
| `ts` | Unix time in seconds (float) of the evaluation |

| Status | Meaning |
|---|---|
| `periodic` | Breathing-like periodic motion with sufficient confidence. |
| `gross_motion` | Large movement now, or within the last 12 s (`min_window_s`): after a movement the engine needs that long without one before it can judge again. Breathing is not measurable, which is fine. |
| `no_motion` | At least 12 s of valid, regular, live frames, and neither periodic nor gross motion in them. |
| `unusable` | Nothing can be said: not enough data yet, stream stalled or stale, picture too dark, saturated, too noisy, without contrast or frozen, timestamps irregular. The log names the reason on every change. |

Consequences worth knowing on the consuming side:

- After start, after a reconnect and after any bad stretch the status is `unusable` for 12 s.
- When breathing motion stops, `no_motion` follows within the window length (25 s, in the synthetic
  tests after 18 to 21 s), because the window still contains the earlier motion. This delay comes on
  top of whatever the integration waits.
- If the frame source fails or stalls, the engine keeps publishing `unusable`; it does not go
  silent while it is connected to the broker. If messages stop while availability is `online`,
  treat the engine as hung.
- The state interval is quantised by the one-second evaluation step.

## Configuration

Every setting can be given as an environment variable (`CHECKBABY_` plus the key in upper case), in
a YAML or JSON file with the same flat keys (`--config FILE` or `CHECKBABY_CONFIG`), or as Home
Assistant add-on option. Environment wins over the file. Unknown keys in the file are an error.

| Key | Default | Meaning |
|---|---|---|
| `rtsp_url` | (required) | Sub-stream URL, e.g. `rtsp://go2rtc:8554/nursery_sub`. `synthetic://40` runs a test pattern breathing at 40/min instead of a camera. |
| `engine_id` | `nursery` | Part of the topic. Letters, digits, `_`, `-`. |
| `roi_x`, `roi_y`, `roi_w`, `roi_h` | `0 0 1 1` | Region of interest as fractions of the picture, origin top left. Put it over the upper body. |
| `fps` | `8` | Target frame rate (5 to 30). Frames are dropped evenly, so the real rate lies between two thirds and four thirds of this, depending on the camera's rate. The analysis needs at least 4 fps. |
| `frame_width` | `64` | Width the region is shrunk to (by a whole factor, so it can come out wider). |
| `mqtt_host`, `mqtt_port` | `localhost`, `1883` | Broker. TLS is not supported yet. |
| `mqtt_username`, `mqtt_password` | empty | Broker credentials. |
| `topic_prefix` | `checkbaby/engine` | |
| `publish_interval_s` | `2` | |
| `log_level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

Thresholds (all tuned on synthetic data, see `checkbaby_engine/signal.py`):

| Key | Default | Meaning |
|---|---|---|
| `window_s` / `min_window_s` | `25` / `12` | Longest stretch analysed / shortest stretch that may be judged. |
| `band_low_hz` / `band_high_hz` | `0.3` / `1.5` | Breathing band. For a trial on an adult (12 to 18 breaths per minute) use `band_low_hz=0.15` with `min_window_s=20`. |
| `periodic_confidence` | `0.3` | Confidence needed for `periodic`. |
| `min_amplitude` | `0.02` | Smallest periodic component, percent of mean brightness. |
| `gross_motion_threshold` | `3.0` | Block change over `motion_lag_s` (0.5 s), percent of mean brightness. |
| `dark_level` | `16` | Mean grey level below which the picture is too dark. |
| `saturated_level` / `max_saturated_fraction` | `250` / `0.25` | More than this share of pixels at or above the level: saturated. |
| `min_contrast` | `3.0` | Spread of the block brightness, percent of mean. Below it nothing could show a movement. |
| `max_noise` | `0.08` | Pixel noise divided by mean brightness. |
| `min_fps`, `max_gap_s`, `stale_after_s`, `frozen_after_s` | `4`, `1`, `2`, `5` | Timing rules: effective frame rate, longest gap that is bridged, age of the newest frame, identical frames. |
| `peak_halfwidth_hz`, `grid` | `0.1`, `8` | Tolerated wobble of the rate; blocks per axis. |

Credentials are never logged. The RTSP URL appears in logs with its password masked
(`rtsp://user:***@host/path`), query strings are masked entirely, and error texts from FFmpeg have
the URL and its password replaced before they are logged.

## Running with Docker

```bash
cd engine
docker build -t checkbaby-engine .
docker run --rm \
  -e CHECKBABY_RTSP_URL=rtsp://go2rtc:8554/nursery_sub \
  -e CHECKBABY_ENGINE_ID=nursery \
  -e CHECKBABY_ROI_X=0.30 -e CHECKBABY_ROI_Y=0.35 -e CHECKBABY_ROI_W=0.40 -e CHECKBABY_ROI_H=0.30 \
  -e CHECKBABY_MQTT_HOST=mosquitto -e CHECKBABY_MQTT_USERNAME=checkbaby -e CHECKBABY_MQTT_PASSWORD=... \
  checkbaby-engine
```

Or copy `compose.example.yaml`, adjust it and put `CHECKBABY_MQTT_PASSWORD=...` into a `.env` file
next to it. The image runs as a non-root user and works with a read-only root file system. No
image is published yet; build it yourself.

To see the MQTT side without a camera: `CHECKBABY_RTSP_URL=synthetic://40`. The log then warns
that no camera is being watched.

Without Docker: `pip install -r requirements.txt && python -m checkbaby_engine --config engine.yaml`
(Python 3.13).

### Home Assistant add-on (untested)

`config.yaml` in this directory is an add-on manifest (name "CheckBaby Vital Engine", slug
`checkbaby_engine`), so the directory can later serve as an add-on. **This packaging has not been
installed or run under the Supervisor.** The manifest follows the documented format from memory.
Known open points:

- An add-on repository needs a `repository.yaml` at the repository root; that file does not exist yet.
- The engine reads the add-on options from `/data/options.json`. The image runs as uid 10001; if the
  Supervisor writes that file readable for root only, the engine cannot read it and the Dockerfile
  needs a different user for the add-on build.
- The broker is configured by hand (`mqtt_host` defaults to `core-mosquitto`); the Supervisor's
  MQTT service discovery is not used.
- Only `amd64` and `aarch64` are listed, because PyAV publishes binary wheels for those.

## Known limits

- **Swaddles and thick blankets** damp or hide the chest movement.
- **Child turned away** from the camera, or lying on the side with the back to it: little or no
  visible movement.
- **A fan, a mobile or anything else that moves in the region of interest** is reported as
  `periodic` or `gross_motion`, whatever the child does. The same goes for a swinging cradle, a
  curtain, a pet, an adult's hand. Keep such things out of the region.
- **Flat camera angle:** the chest moves towards the camera instead of across the picture, which
  changes hardly any pixel.
- **Infrared noise at night** lowers the confidence; above `max_noise` the picture is `unusable`.
  Real sensor and compression noise is not white, and the thresholds have only seen white noise.
- **Plain surfaces:** the method needs edges, folds or texture. A smooth single-coloured sleeping
  bag in even light can breathe without a single block changing. Below `min_contrast` this is
  `unusable`; just above it, it can be `no_motion` although the child breathes. That is a false
  hint the engine cannot tell apart from a real one.
- **Slow strong movement** below the band (9 to 17 per minute, a pixel or more) can be reported at
  two or three times its rate, because its harmonics fall into the band. This also applies to
  adults trying the engine on themselves with the default band.
- **Aliasing:** something moving faster than half the frame rate (a fan) can alias into the band.
- **H.264 keyframe pulsing:** some cameras change the picture slightly at every keyframe, every one
  to four seconds. That is periodic and in the band. Not examined yet.
- **Frozen picture versus perfectly still scene:** identical frames for 5 s are `unusable`
  (`frozen`), on the assumption that a live sensor always has some noise. A camera whose noise
  reduction and encoder deliver bit-identical frames of a still scene would therefore be `unusable`
  exactly when nothing moves. Not examined with real cameras.
- **Rates outside 18 to 90 per minute** are not reported as `periodic`.
- **Lighting changes** of the whole region (exposure steps, a lamp, day/night switch) are
  normalised out; a shadow or light moving across part of the region is not.
- **Latency:** see "Consequences" above. With the integration's own waiting time on top, a hint can
  be 40 s or more behind the event.
- One region, one child. Twins in one picture need two engines with two regions.

## Development

```bash
cd engine
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/python -m mypy          # strict, checks checkbaby_engine
```

The tests need no camera, no broker and no network: the MQTT client is faked and frames come from
`SyntheticSource`, a textured surface that shifts by a fraction of a pixel. Never add footage or
audio of real children to this repository.

Layout: `signal.py` (pure numpy, no I/O), `capture.py` (RTSP reader, synthetic source),
`publisher.py` (MQTT), `config.py`, `runner.py` (the loop), `__main__.py` (wiring, SIGTERM).

## What was tested and what was not

Tested, automatically (`pytest`, synthetic data only):

- Breathing at 20, 30, 40, 60 and 80 per minute at 5, 8 and 10 fps is found within 3 per minute;
  also with sensor noise, with a rate that wanders, and under 20 % lighting flicker.
- Sensor noise alone, lighting flicker at 0.1, 0.7 and 1 Hz and movement at 0.1, 3 and 4 Hz are not
  reported as breathing.
- Breathing that stops becomes `no_motion` within the window length plus 3 s.
- Gross motion, a single twitch and a slow turn are reported as `gross_motion`, and breathing is
  found again afterwards.
- Too little data, dark, saturated, contrast-free and very noisy pictures, a stalled stream, low or
  irregular frame rates, timestamps that repeat or jump back and a frozen picture all give
  `unusable`. A randomised test lets a breathing child run through dark, saturated, noisy, frozen
  and missing stretches and checks that `no_motion` never appears.
- Publisher: topics, retained availability, last will, payload shape, immediate publish on a status
  change, `offline` on shutdown. Loop: a failing or stalling source keeps publishing `unusable`;
  SIGTERM ends the process with `offline`.
- RTSP reader against a fake container: frame-rate reduction, grayscale conversion, region crop,
  reconnect with backoff, masked URLs in logs. One test decodes a generated MPEG-4 file with the
  real PyAV.
- Configuration from environment and file, validation, and that credentials appear in no log line
  or `repr`.

Tested once by hand, not part of the test suite (versions: Python 3.13, numpy 2.5.5, PyAV 19.0.2,
paho-mqtt 2.2.0, PyYAML 6.0.4, Mosquitto 2.1.4, MediaMTX 1.21.4):

- The image built from this Dockerfile (with the base image pulled through a registry mirror) ran
  as uid 10001 with a read-only root file system against a Mosquitto broker with password
  authentication, using the synthetic source: state messages arrived, `offline` was published on
  `docker stop` (exit code 0), the last will fired on `docker kill`, availability was retained.
- The RTSP reader read a synthetic H.264 stream (320 x 240, 10 fps) over RTSP/TCP from a local
  MediaMTX server; the 40/min pattern was reported as 40.0. When the stream ended, and when the
  server was frozen so that the stream stalled without an error, the status became `unusable`
  within about 2 s, the reader gave up after its 5 s read timeout, reconnected with backoff and
  reported `periodic` again 12 s after frames returned.

Not tested:

- **Any real camera, any real child, any real room.** Everything about real noise, real compression
  artefacts, infrared pictures, real breathing amplitudes and real false-hint rates is unknown.
  The thresholds will need tuning; that is what the shadow mode is for.
- go2rtc as the RTSP server, RTSP over UDP, RTSP authentication, streams with B-frames or with
  missing presentation timestamps (handled in code, exercised only with a fake).
- The Home Assistant add-on packaging (see above).
- Long runs: memory use and clock drift over days, behaviour across broker restarts.
- CPU load on small hardware. On the development machine the analysis itself takes about 0.3 ms per
  frame and 1 ms per evaluation; decoding the stream was not measured.
- Other versions of the dependencies than the ones listed; `requirements.txt` allows a wider range.
