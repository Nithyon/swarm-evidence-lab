"""Temporal and artifact metrics for heterogeneous agent activity logs.

Python 3.10+; only Poisson tests require the optional ``scipy`` package.
All timestamps and fixed-width bins use UTC. Missing timestamps are never
invented, and zero bins mean no events *within the declared observation span*.
The statistical tests measure association, not coordination or causation.
An exact match to an unspecified Observatory implementation is not claimed.

Example (AI Village chat; JSONL and gzip are streamed)::

    stats = ParseStats()
    events = iter_activity_events(
        iter_records(r"D:\\Datasets\\ai-village\\chat_messages.jsonl.gz"),
        source="ai-village", timestamp_field="created_at",
        actor_field="agent_speaker_id", text_fields=("content",),
        on_invalid="skip", stats=stats,
    )
    activity = bin_activity(events, window="daily")
    bursts = detect_bursts(activity, method="zscore", z_threshold=3.0)

German Wiki revisions: timestamp_field="time", actor_field="label",
artifact_fields=("page_id",), text_fields=("body",). Labels are asserted
handles, not verified identities; IP prefixes must not be treated as agents.
Revision bodies can retain earlier URLs; use diffs if measuring new URL
introductions rather than observed URL presence in edits.
SwarmTraces: timestamp_field="time_utc", text_fields=("text",); many records
have no timestamps or actor IDs and cannot support temporal/actor metrics.
Transluce: stream all-reports.csv once, filter disposition == "included",
timestamp_field="report_date_utc". Report IDs/URLs are observations, not actor
identities or the URLs visited by agents. Alternatively feed daily-counts.csv
using timestamp_field="date_utc", weight_field="total". Do not combine that
table with the underlying reports, or page summaries with wiki revisions.

For prospective analysis, pass baseline_window to use only earlier bins.
Account for collection gaps, partial boundary bins, daily/weekly schedules,
selection bias, and multiple source-pair comparisons in downstream analysis.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone, tzinfo
from itertools import combinations, groupby
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable, Iterator, Literal, Mapping, Sequence, TypeAlias
from urllib.parse import urlsplit

Timestamp: TypeAlias = datetime | date | str | int | float
ActorKey: TypeAlias = tuple[str, str]
UTC = timezone.utc
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_URL = re.compile(r"https?://[^\s<>\"'\\]+", re.IGNORECASE)

__all__ = [
    "ActivityEvent", "ActivitySeries", "BurstWindow", "BurstResult",
    "SimultaneityResult", "Interaction", "ReciprocityResult",
    "AdoptionLatency", "InfectionLatencyResult", "ParseStats",
    "parse_timestamp", "iter_records", "extract_urls", "iter_activity_events",
    "bin_activity", "adjust_pvalues", "detect_bursts", "cross_source_simultaneity",
    "pairwise_simultaneity", "artifact_interactions", "compute_reciprocity",
    "compute_infection_latency",
]


@dataclass(frozen=True)
class ActivityEvent:
    timestamp: Timestamp
    source: str = ""
    actor: str | None = None
    artifacts: tuple[str, ...] = ()
    weight: int = 1


@dataclass(frozen=True)
class ActivitySeries:
    starts: tuple[datetime, ...]
    counts: tuple[int, ...]
    window: timedelta

    def __post_init__(self) -> None:
        _window_size(self.window)
        if len(self.starts) != len(self.counts):
            raise ValueError("starts and counts must have equal lengths")
        for i, start in enumerate(self.starts):
            if start.tzinfo != UTC or _floor(start, self.window) != start:
                raise ValueError("bin starts must be UTC and aligned to the window")
            if i and start != self.starts[i - 1] + self.window:
                raise ValueError("activity bins must be contiguous")
        for count in self.counts:
            _count(count)


@dataclass(frozen=True)
class BurstWindow:
    start: datetime
    count: int
    expected_count: float | None
    z_score: float | None
    p_value: float | None
    adjusted_p_value: float | None
    is_burst: bool
    baseline_size: int


@dataclass(frozen=True)
class BurstResult:
    series: ActivitySeries
    windows: tuple[BurstWindow, ...]
    method: str

    @property
    def burst_starts(self) -> tuple[datetime, ...]:
        return tuple(w.start for w in self.windows if w.is_burst)


@dataclass(frozen=True)
class SimultaneityResult:
    n_windows: int
    burst_count_a: int
    burst_count_b: int
    joint_bursts: int
    expected_joint_bursts: float
    burst_correlation: float | None
    count_correlation: float | None
    overlap_p_value: float | None
    circular_shift_p_value: float | None
    aligned_starts: tuple[datetime, ...]
    lag_windows: int


@dataclass(frozen=True)
class Interaction:
    sender: ActorKey
    receiver: ActorKey
    artifact: str | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True)
class ReciprocityResult:
    directed_edges: int
    mutual_dyads: int
    dyads: int
    edge_reciprocity: float
    dyad_reciprocity: float
    weighted_reciprocity: float
    edge_weights: Mapping[tuple[ActorKey, ActorKey], int]


@dataclass(frozen=True)
class AdoptionLatency:
    artifact: str
    actor: ActorKey
    first_seen: datetime
    seed_time: datetime
    seed_actors: tuple[ActorKey, ...]
    seed_latency_seconds: float
    previous_adoption_latency_seconds: float
    previous_actors: tuple[ActorKey, ...]


@dataclass(frozen=True)
class InfectionLatencyResult:
    shared_artifacts: int
    seed_actors: int
    adoptions: tuple[AdoptionLatency, ...]
    mean_latency_seconds: float | None
    median_latency_seconds: float | None


@dataclass
class ParseStats:
    seen: int = 0
    emitted: int = 0
    missing_timestamp: int = 0
    invalid_record: int = 0
    missing_actor: int = 0


def parse_timestamp(value: Timestamp, *, naive_timezone: tzinfo = UTC) -> datetime:
    """Parse ISO dates/times or Unix *seconds* into UTC; naive values default UTC.

    Milliseconds must be converted explicitly. Null/empty/nonfinite values fail.
    Use naive_timezone=ZoneInfo(...) for logs documented in a different zone.
    """
    if not isinstance(naive_timezone, tzinfo):
        raise ValueError("naive_timezone must be a timezone object")
    try:
        if isinstance(value, datetime):
            result = value
        elif isinstance(value, date):
            result = datetime.combine(value, datetime.min.time())
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(value):
                raise ValueError("timestamp must be finite")
            return datetime.fromtimestamp(value, UTC)
        elif isinstance(value, str) and value.strip():
            result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        else:
            raise ValueError("expected an ISO timestamp, datetime, date or Unix seconds")
        if result.tzinfo is None:
            result = result.replace(tzinfo=naive_timezone)
        return result.astimezone(UTC)
    except (TypeError, OverflowError, OSError) as exc:
        raise ValueError("invalid or out-of-range timestamp") from exc


def iter_records(path: str | Path) -> Iterator[dict[str, Any]]:
    """Stream CSV or JSONL, optionally gzip-compressed; malformed input fails.

    Blank JSONL lines are ignored. Errors carry the file and physical line.
    """
    path = Path(path)
    suffixes = [s.lower() for s in path.suffixes]
    compressed = bool(suffixes and suffixes[-1] == ".gz")
    extension = suffixes[-2] if compressed and len(suffixes) > 1 else path.suffix.lower()
    if extension not in {".csv", ".jsonl", ".ndjson"}:
        raise ValueError("expected .csv, .jsonl or .ndjson (optionally .gz)")
    opener = gzip.open if compressed else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        if extension == ".csv":
            yield from csv.DictReader(handle)
            return
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("record must be an object")
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
            yield record


def extract_urls(text: str) -> tuple[str, ...]:
    """Extract distinct HTTP(S) URLs conservatively, preserving queries/fragments.

    Strip prose punctuation and unmatched closing parentheses. Redaction tokens
    are excluded rather than collapsed into apparently shared real endpoints.
    URL extraction is heuristic; supply curated artifact IDs for exact matching.
    """
    found: dict[str, None] = {}
    for match in _URL.finditer(text):
        url = match.group().rstrip(".,;!?:}")
        while url.endswith(")") and url.count(")") > url.count("("):
            url = url[:-1]
        while url.endswith("]") and url.count("]") > url.count("["):
            url = url[:-1]
        if "[REDACTED" in url or "[SERVICE" in url:
            continue
        try:
            parts = urlsplit(url)
            if parts.hostname and parts.scheme.lower() in {"http", "https"}:
                found[url] = None
        except ValueError:
            continue
    return tuple(found)


def iter_activity_events(
    records: Iterable[Mapping[str, Any]], *, source: str,
    timestamp_field: str, actor_field: str | None = None,
    artifact_fields: Sequence[str] = (), text_fields: Sequence[str] = (),
    weight_field: str | None = None, on_invalid: Literal["raise", "skip"] = "raise",
    stats: ParseStats | None = None,
) -> Iterator[ActivityEvent]:
    """Adapt records using explicit top-level fields; track skipped rows if requested.

    Missing actors remain None: those events count as activity but are excluded
    from actor metrics. String integer weights support preaggregated CSV rows.
    Filter unwanted record types/dispositions before calling this function.
    """
    if on_invalid not in {"raise", "skip"}:
        raise ValueError("on_invalid must be 'raise' or 'skip'")
    stats = stats if stats is not None else ParseStats()
    for row_number, record in enumerate(records, 1):
        stats.seen += 1
        raw_time = record.get(timestamp_field)
        if raw_time is None or raw_time == "":
            stats.missing_timestamp += 1
            if on_invalid == "raise":
                raise ValueError(f"record {row_number}: missing {timestamp_field}")
            continue
        try:
            timestamp = parse_timestamp(raw_time)
            raw_actor = record.get(actor_field) if actor_field else None
            actor = str(raw_actor) if raw_actor is not None and raw_actor != "" else None
            artifacts: dict[str, None] = {}
            for field in artifact_fields:
                value = record.get(field)
                if value is None or value == "":
                    continue
                values = value if isinstance(value, (list, tuple)) else (value,)
                for item in values:
                    if not isinstance(item, str) or not item:
                        raise ValueError(f"{field} must contain nonempty strings")
                    artifacts[item] = None
            for field in text_fields:
                text = record.get(field)
                if text is not None:
                    if not isinstance(text, str):
                        raise ValueError(f"{field} must be text")
                    artifacts.update(dict.fromkeys(extract_urls(text)))
            raw_weight = record.get(weight_field) if weight_field else 1
            weight = int(raw_weight) if isinstance(raw_weight, str) else raw_weight
            _count(weight)
        except (ValueError, TypeError) as exc:
            stats.invalid_record += 1
            if on_invalid == "raise":
                raise ValueError(f"record {row_number}: {exc}") from exc
            continue
        stats.missing_actor += actor is None
        stats.emitted += 1
        yield ActivityEvent(timestamp, source, actor, tuple(artifacts), weight)


def _count(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("counts/weights must be nonnegative integers")


def _window_size(window: str | timedelta) -> timedelta:
    if isinstance(window, str):
        aliases = {"hourly": timedelta(hours=1), "hour": timedelta(hours=1),
                   "daily": timedelta(days=1), "day": timedelta(days=1)}
        if window not in aliases:
            raise ValueError("window must be 'hourly', 'daily', or a positive timedelta")
        return aliases[window]
    if not isinstance(window, timedelta) or window <= timedelta(0):
        raise ValueError("window must be a positive timedelta")
    return window


def _floor(timestamp: datetime, window: timedelta) -> datetime:
    return _EPOCH + ((timestamp - _EPOCH) // window) * window


def bin_activity(
    events: Iterable[ActivityEvent | Timestamp], *, window: str | timedelta = "daily",
    start: Timestamp | None = None, end: Timestamp | None = None,
    max_bins: int = 1_000_000,
) -> ActivitySeries:
    """Count unsorted events into dense UTC bins, including zero-activity bins.

    Explicit bounds describe [start, end) and MUST be window-aligned, preventing
    partial bins from silently changing exposure. Without bounds, infer the
    first and last event bins; boundary bins may therefore be partial. Events
    outside bounds are ignored. Empty input with both bounds yields zero bins;
    otherwise empty input yields an empty series. max_bins prevents huge spans.
    """
    step = _window_size(window)
    _count(max_bins)
    if not max_bins:
        raise ValueError("max_bins must be positive")
    lower = parse_timestamp(start) if start is not None else None
    upper = parse_timestamp(end) if end is not None else None
    for bound in (lower, upper):
        if bound is not None and _floor(bound, step) != bound:
            raise ValueError("observation bounds must be window-aligned")
    if lower is not None and upper is not None and lower >= upper:
        raise ValueError("start must be before end")
    counts: Counter[datetime] = Counter()
    for event in events:
        timestamp = parse_timestamp(event.timestamp if isinstance(event, ActivityEvent) else event)
        weight = event.weight if isinstance(event, ActivityEvent) else 1
        _count(weight)
        if (lower is not None and timestamp < lower) or (upper is not None and timestamp >= upper):
            continue
        counts[_floor(timestamp, step)] += weight
    if not counts and (lower is None or upper is None):
        return ActivitySeries((), (), step)
    lower = lower if lower is not None else min(counts)
    upper = upper if upper is not None else max(counts) + step
    n_bins = (upper - lower) // step
    if n_bins > max_bins:
        raise ValueError(f"observation span exceeds max_bins={max_bins}")
    starts = tuple(lower + i * step for i in range(n_bins))
    return ActivitySeries(starts, tuple(counts[t] for t in starts), step)


def adjust_pvalues(
    pvalues: Sequence[float], method: Literal["none", "bonferroni", "bh"] = "bh",
) -> tuple[float, ...]:
    """Adjust p-values, preserving order.

    BH controls FDR under independent or appropriate positive dependence;
    Bonferroni controls familywise error under arbitrary dependence.
    """
    if method not in {"none", "bonferroni", "bh"}:
        raise ValueError("unknown multiple-testing correction")
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in pvalues):
        raise ValueError("p-values must be finite and in [0, 1]")
    n = len(pvalues)
    if method == "none":
        return tuple(pvalues)
    if method == "bonferroni":
        return tuple(min(1.0, p * n) for p in pvalues)
    adjusted = [1.0] * n
    running = 1.0
    for rank, index in reversed(list(enumerate(sorted(range(n), key=pvalues.__getitem__), 1))):
        running = min(running, pvalues[index] * n / rank)
        adjusted[index] = running
    return tuple(adjusted)


def detect_bursts(
    series: ActivitySeries, *, method: Literal["zscore", "poisson"] = "zscore",
    z_threshold: float = 3.0, alpha: float = 0.05, min_count: int = 1,
    baseline_window: int | None = None, min_baseline: int = 2,
    baseline_counts: Sequence[int] | None = None,
    correction: Literal["none", "bonferroni", "bh"] = "bh",
) -> BurstResult:
    """Flag upward bursts against a separate, prior, or leave-one-out baseline.

    Default: retrospective leave-one-out mean/population standard deviation.
    baseline_window=N uses up to N PRECEDING bins; baseline_counts uses an
    independent fixed reference sample. Both baseline options cannot be set.
    Zero variance gives +inf only for counts above the constant reference.
    Insufficient baselines remain untested (expected_count=None).

    Poisson p-values are P(X >= observed) at the estimated baseline mean, using
    scipy.stats.poisson.sf for numerical stability. BH correction is applied
    across tested bins. These are plug-in tests assuming equal exposure and a
    stationary Poisson rate; baseline uncertainty/overdispersion are not modeled.
    Z-scores are descriptive thresholds and have no inferred p-values.
    """
    if method not in {"zscore", "poisson"}:
        raise ValueError("method must be 'zscore' or 'poisson'")
    if not math.isfinite(z_threshold) or z_threshold <= 0:
        raise ValueError("z_threshold must be finite and positive")
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    _count(min_count)
    _count(min_baseline)
    if min_baseline < 1:
        raise ValueError("min_baseline must be positive")
    if baseline_window is not None:
        _count(baseline_window)
        if baseline_window < min_baseline:
            raise ValueError("baseline_window must be at least min_baseline")
    if baseline_window is not None and baseline_counts is not None:
        raise ValueError("choose prior bins or a fixed reference, not both")
    adjust_pvalues((), correction)
    poisson = None
    if method == "poisson":
        try:
            from scipy.stats import poisson
        except ImportError as exc:
            raise ImportError("Poisson tests require scipy; zscore uses only the standard library") from exc
    reference = tuple(baseline_counts) if baseline_counts is not None else None
    if reference is not None:
        for value in reference:
            _count(value)
    counts = series.counts
    total = sum(counts)
    squares = sum(c * c for c in counts)
    prior: deque[int] = deque()
    prior_total = prior_squares = 0
    fixed_mean = mean(reference) if reference else 0.0
    fixed_std = pstdev(reference) if reference else 0.0
    windows: list[BurstWindow] = []
    for start, count in zip(series.starts, counts):
        if reference is not None:
            n, expected, std = len(reference), fixed_mean, fixed_std
        else:
            if baseline_window is None:
                n, subtotal, subsquares = len(counts) - 1, total - count, squares - count * count
            else:
                n, subtotal, subsquares = len(prior), prior_total, prior_squares
            expected = subtotal / n if n else 0.0
            std = math.sqrt(max(0.0, subsquares / n - expected * expected)) if n else 0.0
        if n < min_baseline:
            windows.append(BurstWindow(start, count, None, None, None, None, False, n))
        else:
            delta = count - expected
            z = delta / std if std else (math.copysign(math.inf, delta) if delta else 0.0)
            p = float(poisson.sf(count - 1, expected)) if poisson is not None else None
            burst = count >= min_count and delta > 0 and z >= z_threshold if method == "zscore" else False
            windows.append(BurstWindow(start, count, float(expected), z, p, None, burst, n))
        if baseline_window is not None:
            prior.append(count)
            prior_total += count
            prior_squares += count * count
            if len(prior) > baseline_window:
                expired = prior.popleft()
                prior_total -= expired
                prior_squares -= expired * expired
    tested = [(i, w.p_value) for i, w in enumerate(windows) if w.p_value is not None]
    adjusted = adjust_pvalues([p for _, p in tested], correction)
    for (index, _), p_adjusted in zip(tested, adjusted):
        w = windows[index]
        expected_count = w.expected_count
        if expected_count is None:
            raise RuntimeError("a tested Poisson window must have a baseline")
        windows[index] = BurstWindow(
            w.start, w.count, w.expected_count, w.z_score, w.p_value, p_adjusted,
            w.count >= min_count and w.count > expected_count and p_adjusted <= alpha,
            w.baseline_size,
        )
    return BurstResult(series, tuple(windows), method)


def _correlation(a: Sequence[int], b: Sequence[int]) -> float | None:
    if len(a) < 2:
        return None
    center_a, center_b = mean(a), mean(b)
    da, db = [v - center_a for v in a], [v - center_b for v in b]
    denominator = math.sqrt(sum(v * v for v in da) * sum(v * v for v in db))
    if not denominator:
        return None
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(da, db)) / denominator))


def _overlap_tail(n: int, a: int, b: int, observed: int) -> float:
    # One-sided Fisher/hypergeometric tail under exchangeable bin labels.
    # Integer combinations avoid lgamma cancellation; support is bounded by n.
    denominator = math.comb(n, b)
    numerator = sum(math.comb(a, k) * math.comb(n - a, b - k)
                    for k in range(max(observed, a + b - n, 0), min(a, b) + 1))
    return numerator / denominator


def cross_source_simultaneity(
    a: BurstResult, b: BurstResult, *, lag_windows: int = 0,
) -> SimultaneityResult:
    """Compare bursts on shared, tested UTC bins; never pad disjoint coverage.

    Returns Pearson correlation of binary burst indicators (phi), raw count
    correlation, the one-sided exact overlap/Fisher p-value, and a circular-shift
    p-value for overlap. Undefined correlations and tests with no shared bins
    are None. Positive lag compares A(t) to B(t + lag * window).

    Circular shifts enumerate EVERY relative rotation, including the observed
    alignment: p = rotations with overlap >= observed / n. They preserve each
    binary series' burst clustering but assume circular stationarity, and are
    returned only for contiguous aligned bins with at least two observations.
    Exact overlap instead assumes exchangeable/independent bins. Neither test
    removes shared schedules, common causes, or collection artifacts. Pairwise
    p-values are unadjusted; use adjust_pvalues for the family you test.
    """
    if isinstance(lag_windows, bool) or not isinstance(lag_windows, int):
        raise ValueError("lag_windows must be an integer")
    if a.series.window != b.series.window:
        raise ValueError("sources must use identical window widths")
    left = {w.start: w for w in a.windows if w.expected_count is not None}
    right = {w.start: w for w in b.windows if w.expected_count is not None}
    offset = lag_windows * a.series.window
    starts = tuple(sorted(t for t in left if t + offset in right))
    x = [int(left[t].is_burst) for t in starts]
    y = [int(right[t + offset].is_burst) for t in starts]
    n, na, nb = len(starts), sum(x), sum(y)
    joint = sum(v * w for v, w in zip(x, y))
    shift_p: float | None = None
    if n >= 2 and all(starts[i] == starts[i - 1] + a.series.window for i in range(1, n)):
        # Sparse accumulation is O(n + burst_count_a * burst_count_b), rather
        # than O(n**2) for the usual sparse burst indicators.
        overlaps = [0] * n
        x_indices = [i for i, value in enumerate(x) if value]
        y_indices = [j for j, value in enumerate(y) if value]
        for i in x_indices:
            for j in y_indices:
                overlaps[(j - i) % n] += 1
        shift_p = sum(v >= joint for v in overlaps) / n
    return SimultaneityResult(
        n, na, nb, joint, na * nb / n if n else 0.0,
        _correlation(x, y),
        _correlation([left[t].count for t in starts], [right[t + offset].count for t in starts]),
        _overlap_tail(n, na, nb, joint) if n else None,
        shift_p, starts, lag_windows,
    )


def pairwise_simultaneity(
    sources: Mapping[str, BurstResult], *, lag_windows: int = 0,
) -> dict[tuple[str, str], SimultaneityResult]:
    """Compare every source pair in sorted name order; p-values are unadjusted."""
    return {(a, b): cross_source_simultaneity(sources[a], sources[b], lag_windows=lag_windows)
            for a, b in combinations(sorted(sources), 2)}


def _artifact_histories(
    events: Iterable[ActivityEvent],
) -> dict[str, dict[datetime, set[ActorKey]]]:
    histories: dict[str, dict[datetime, set[ActorKey]]] = defaultdict(lambda: defaultdict(set))
    for event in events:
        _count(event.weight)
        if event.actor is None or not event.actor or event.weight == 0:
            continue
        timestamp = parse_timestamp(event.timestamp)
        for artifact in set(event.artifacts):
            if not isinstance(artifact, str) or not artifact:
                raise ValueError("artifact IDs must be nonempty strings")
            histories[artifact][timestamp].add((event.source, event.actor))
    return histories


def artifact_interactions(events: Iterable[ActivityEvent]) -> Iterator[Interaction]:
    """Infer directed transitions between consecutive mention-time groups.

    For each artifact, every actor in one timestamp group points to each
    different actor in the next group. Duplicate mentions are deduplicated;
    actors at the same timestamp have no inferred direction between them.
    Returning mentions can produce reciprocal edges. This is a descriptive
    proxy, NOT evidence that one actor communicated with or infected another.
    Actor IDs are namespaced by source. Artifact IDs intentionally are not,
    allowing shared exact URLs across sources. Grouping requires memory.
    """
    for artifact, history in sorted(_artifact_histories(events).items()):
        previous: set[ActorKey] = set()
        for timestamp, actors in sorted(history.items()):
            for sender in sorted(previous):
                for receiver in sorted(actors):
                    if sender != receiver:
                        yield Interaction(sender, receiver, artifact, timestamp)
            previous = actors


def compute_reciprocity(interactions: Iterable[Interaction]) -> ReciprocityResult:
    """Compute directed, dyadic and weighted reciprocity, excluding self-loops.

    Edge reciprocity = directed edges with a reverse / all directed edges.
    Dyad reciprocity = mutual unordered pairs / all connected unordered pairs.
    Weighted reciprocity = sum(min(w_uv, w_vu)) / sum(w_uv), over directed edges.
    Each input interaction contributes unit weight. Empty graphs return zeros.
    Use explicit observed interactions when available; artifact_interactions
    provides a clearly labeled mention-order proxy.
    """
    weights: Counter[tuple[ActorKey, ActorKey]] = Counter()
    for interaction in interactions:
        if interaction.sender != interaction.receiver:
            weights[(interaction.sender, interaction.receiver)] += 1
    dyads = {frozenset((u, v)) for u, v in weights}
    reciprocated = sum((v, u) in weights for u, v in weights)
    mutual = reciprocated // 2
    total = sum(weights.values())
    matched = sum(min(weight, weights.get((v, u), 0)) for (u, v), weight in weights.items())
    return ReciprocityResult(
        len(weights), mutual, len(dyads), reciprocated / len(weights) if weights else 0.0,
        mutual / len(dyads) if dyads else 0.0, matched / total if total else 0.0,
        dict(sorted(weights.items())),
    )


def compute_infection_latency(events: Iterable[ActivityEvent]) -> InfectionLatencyResult:
    """Measure first-observed adoption delay for artifacts shared by >=2 actors.

    Report each nonseed actor's first mention minus the earliest observed
    mention, and minus the most recent strictly earlier first-adoption group.
    All actors tied at the earliest timestamp are seeds; no ordering or zero
    latency transmission is invented. Repeat mentions never reset adoption.
    Actor IDs are (source, actor) pairs. Latencies are seconds; empty samples
    have None summaries. Observations are left/right censored: true exposure,
    prior possession and causality cannot be inferred from these logs alone.
    """
    first_seen: dict[str, dict[ActorKey, datetime]] = defaultdict(dict)
    for event in events:
        _count(event.weight)
        if event.actor is None or not event.actor or event.weight == 0:
            continue
        timestamp = parse_timestamp(event.timestamp)
        actor = (event.source, event.actor)
        for artifact in set(event.artifacts):
            if not isinstance(artifact, str) or not artifact:
                raise ValueError("artifact IDs must be nonempty strings")
            previous = first_seen[artifact].get(actor)
            if previous is None or timestamp < previous:
                first_seen[artifact][actor] = timestamp
    adoptions: list[AdoptionLatency] = []
    shared = seeds_total = 0
    for artifact, actors in sorted(first_seen.items()):
        if len(actors) < 2:
            continue
        shared += 1
        ordered = sorted(actors.items(), key=lambda item: (item[1], item[0]))
        groups = [(timestamp, tuple(actor for actor, _ in group))
                  for timestamp, group in groupby(ordered, key=lambda item: item[1])]
        seed_time, seeds = groups[0]
        seeds_total += len(seeds)
        previous_time, previous_actors = seed_time, seeds
        for timestamp, group_actors in groups[1:]:
            for actor in group_actors:
                adoptions.append(AdoptionLatency(
                    artifact, actor, timestamp, seed_time, seeds,
                    (timestamp - seed_time).total_seconds(),
                    (timestamp - previous_time).total_seconds(), previous_actors,
                ))
            previous_time, previous_actors = timestamp, group_actors
    latencies = [adoption.seed_latency_seconds for adoption in adoptions]
    return InfectionLatencyResult(shared, seeds_total, tuple(adoptions),
                                  mean(latencies) if latencies else None,
                                  median(latencies) if latencies else None)


def _self_test() -> None:
    """Synthetic checks; no dataset reads, downloads or persistent writes."""
    import tempfile
    import unittest

    class MetricsTests(unittest.TestCase):
        def series(self, counts: Sequence[int], shift: int = 0) -> ActivitySeries:
            return ActivitySeries(tuple(_EPOCH + timedelta(days=i + shift) for i in range(len(counts))),
                                  tuple(counts), timedelta(days=1))

        def test_timestamp_and_bins(self) -> None:
            self.assertEqual(parse_timestamp("1970-01-01T01:00:00+01:00"), _EPOCH)
            self.assertEqual(parse_timestamp(0), _EPOCH)
            result = bin_activity(["1970-01-03", "1970-01-01"])
            self.assertEqual(result.counts, (1, 0, 1))
            self.assertEqual(bin_activity([], start=_EPOCH, end=_EPOCH + timedelta(days=3)).counts, (0, 0, 0))
            self.assertEqual(bin_activity([_EPOCH + timedelta(days=1)], start=_EPOCH,
                                          end=_EPOCH + timedelta(days=1)).counts, (0,))
            self.assertEqual(bin_activity(["1970-01-01T02:00:00Z", _EPOCH], window="hourly").counts, (1, 0, 1))
            self.assertEqual(bin_activity([]).counts, ())
            with self.assertRaises(ValueError):
                bin_activity([], start="1970-01-01T00:01:00", end="1970-01-02")
            with self.assertRaises(ValueError):
                bin_activity([_EPOCH, _EPOCH + timedelta(days=3)], max_bins=2)
            for invalid in (True, float("nan"), "", None):
                with self.assertRaises(ValueError):
                    parse_timestamp(invalid)

        def test_bursts(self) -> None:
            bursts = detect_bursts(self.series([1] * 9 + [20]))
            self.assertEqual(bursts.burst_starts, (_EPOCH + timedelta(days=9),))
            self.assertEqual(bursts.windows[-1].z_score, math.inf)
            self.assertFalse(any(w.is_burst for w in detect_bursts(self.series([0] * 10)).windows))
            self.assertFalse(any(w.is_burst for w in detect_bursts(self.series([1] * 10)).windows))
            rolling = detect_bursts(self.series([2, 2, 2, 10]), baseline_window=2)
            self.assertIsNone(rolling.windows[0].expected_count)
            self.assertEqual(rolling.windows[-1].expected_count, 2)
            self.assertTrue(rolling.windows[-1].is_burst)
            self.assertIsNone(detect_bursts(self.series([9])).windows[0].expected_count)
            fixed = detect_bursts(self.series([10]), baseline_counts=[1, 2, 3])
            self.assertTrue(fixed.windows[0].is_burst)
            self.assertEqual(adjust_pvalues([0.01, 0.04, 0.03]), (0.03, 0.04, 0.04))
            try:
                import scipy.stats
            except ImportError:
                return
            poisson = detect_bursts(self.series([1] * 9 + [20]), method="poisson")
            self.assertTrue(poisson.windows[-1].is_burst)
            self.assertAlmostEqual(poisson.windows[-1].p_value, scipy.stats.poisson.sf(19, 1))
            self.assertEqual(detect_bursts(self.series([0, 0, 1]), method="poisson").windows[-1].p_value, 0)

        def test_simultaneity(self) -> None:
            bursts = detect_bursts(self.series([1] * 9 + [20]))
            result = cross_source_simultaneity(bursts, bursts)
            self.assertEqual(result.burst_correlation, 1)
            self.assertEqual(result.joint_bursts, 1)
            self.assertAlmostEqual(result.overlap_p_value, 0.1)
            self.assertAlmostEqual(result.circular_shift_p_value, 0.1)
            disjoint = detect_bursts(self.series([1, 2, 10], shift=20))
            self.assertEqual(cross_source_simultaneity(bursts, disjoint).n_windows, 0)
            self.assertIsNone(cross_source_simultaneity(bursts, disjoint).overlap_p_value)
            constant = detect_bursts(self.series([1] * 10))
            self.assertIsNone(cross_source_simultaneity(constant, constant).burst_correlation)
            self.assertEqual(cross_source_simultaneity(constant, constant).overlap_p_value, 1)
            later = detect_bursts(self.series([1] * 9 + [20], shift=2))
            self.assertEqual(cross_source_simultaneity(bursts, later, lag_windows=2).joint_bursts, 1)
            partial = detect_bursts(self.series([1] * 4 + [20], shift=5))
            self.assertEqual(cross_source_simultaneity(bursts, partial).n_windows, 5)
            self.assertEqual(len(pairwise_simultaneity({"a": bursts, "b": later, "c": partial})), 3)

        def test_artifacts(self) -> None:
            events = [ActivityEvent(_EPOCH + timedelta(seconds=t), "s", a, ("url",))
                      for t, a in [(20, "C"), (0, "A"), (10, "B"), (30, "A"), (11, "B")]]
            latency = compute_infection_latency(events)
            self.assertEqual(latency.shared_artifacts, 1)
            self.assertEqual([a.seed_latency_seconds for a in latency.adoptions], [10, 20])
            self.assertEqual(latency.adoptions[-1].previous_adoption_latency_seconds, 10)
            self.assertEqual(latency.median_latency_seconds, 15)
            tied = [ActivityEvent(_EPOCH, "s", a, ("url",)) for a in ["A", "B"]]
            self.assertEqual(compute_infection_latency(tied).seed_actors, 2)
            self.assertEqual(list(artifact_interactions(tied)), [])
            self.assertIsNone(compute_infection_latency(tied).mean_latency_seconds)
            returning = [ActivityEvent(_EPOCH + timedelta(seconds=t), "s", a, ("url",))
                         for t, a in [(0, "A"), (1, "B"), (2, "A")]]
            self.assertEqual(compute_reciprocity(artifact_interactions(returning)).edge_reciprocity, 1)
            a, b, c = ("s", "A"), ("s", "B"), ("s", "C")
            graph = compute_reciprocity([Interaction(a, b), Interaction(a, b), Interaction(b, a),
                                        Interaction(b, c), Interaction(a, a)])
            self.assertAlmostEqual(graph.edge_reciprocity, 2 / 3)
            self.assertEqual(graph.dyad_reciprocity, 0.5)
            self.assertEqual(graph.weighted_reciprocity, 0.5)
            self.assertEqual(compute_reciprocity([]).edge_reciprocity, 0)
            namespaced = [ActivityEvent(_EPOCH, "s1", "A", ("url",)),
                          ActivityEvent(_EPOCH + timedelta(seconds=2), "s2", "A", ("url",))]
            self.assertEqual(compute_infection_latency(namespaced).shared_artifacts, 1)
            self.assertEqual(compute_infection_latency([]).adoptions, ())

        def test_io_and_adapter(self) -> None:
            stats = ParseStats()
            rows = [{"t": "1970-01-01", "actor": "A", "body": "See https://example.com/a_(b)."},
                    {"t": None}, {"t": "bad"}, {"t": "1970-01-02"}]
            events = list(iter_activity_events(rows, source="s", timestamp_field="t", actor_field="actor",
                                              text_fields=("body",), on_invalid="skip", stats=stats))
            self.assertEqual((stats.seen, stats.emitted, stats.missing_timestamp, stats.invalid_record,
                              stats.missing_actor), (4, 2, 1, 1, 1))
            self.assertEqual(events[0].artifacts, ("https://example.com/a_(b)",))
            self.assertEqual(extract_urls('[https://example.com/a]'), ("https://example.com/a",))
            self.assertEqual(extract_urls('https://[REDACTED:destination]'), ())
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "records.jsonl.gz"
                with gzip.open(path, "wt", encoding="utf-8") as f:
                    f.write(json.dumps(rows[0]) + "\n\n")
                self.assertEqual(list(iter_records(path)), rows[:1])
                path = Path(temp) / "daily.csv"
                path.write_text("date,total\n1970-01-01,3\n", encoding="utf-8")
                weighted = iter_activity_events(iter_records(path), source="s", timestamp_field="date",
                                                weight_field="total")
                self.assertEqual(bin_activity(weighted).counts, (3,))

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MetricsTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    _self_test()
