#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

r"""Benchmark for the httprequest-lego-provider DNS request path.

Reveals the known bottleneck in ``api/dns.py``: every ``present`` / ``cleanup`` request
performs a full ``git clone`` of the DNS-records repository, which grows slower as the
repository accumulates history.

The benchmark builds a synthetic git repository whose shape mirrors a real DNS-records
repository -- a long commit history made of many small, one-record-per-commit changes
across several ``*.domain`` zone files, exactly the churn ``write_dns_record`` and
``remove_dns_record`` produce over time. It then drives ``present`` and ``cleanup``
requests through the real Django view layer (via the Django test client) against a real
test database, so the emitted trace shows the full ``request -> form -> permission-query
-> git`` flow with ``git.clone`` dominating.

All spans produced by the in-code OpenTelemetry instrumentation are collected in memory
and written as an OTLP JSON traces file (``resourceSpans`` format) that
``gen_flamegraph.py`` renders into a self-contained interactive flame graph.

Usage:
    python tests/benchmark/benchmark.py \\
        --commits 2000 \\
        --domains 5 \\
        --iterations 10 \\
        --traces-output traces.json
"""

import argparse
import base64
import logging
import os
import secrets
import subprocess  # nosec B404
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FQDN_PREFIX = "_acme-challenge."
RECORD_LINE = '{sub} 600 IN TXT "{value}"\n'


def _git_env() -> dict:
    """Return an environment that isolates git from ambient configuration.

    System and global git configuration are disabled and an explicit identity is
    supplied, so git behaves identically regardless of the host's configuration
    (e.g. CI runners that enable commit signing, auto-gc, or hooks).

    Returns:
        The environment mapping to pass to git subprocesses.
    """
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "benchmark",
        "GIT_AUTHOR_EMAIL": "benchmark@example.com",
        "GIT_COMMITTER_NAME": "benchmark",
        "GIT_COMMITTER_EMAIL": "benchmark@example.com",
    }


def _git(cwd: Path, *args: str) -> None:
    """Run a git command in ``cwd``, isolated from ambient git configuration.

    Args:
        cwd: working directory for the git command.
        args: git command arguments.

    Raises:
        RuntimeError: if the git command exits non-zero.
    """
    result = subprocess.run(  # nosec B603 B607
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=_git_env(),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


def _zone_content(domain: str, record: str | None = None) -> bytes:
    """Render the content of a zone file, optionally with a single TXT record.

    Args:
        domain: the domain the zone file belongs to.
        record: the ACME challenge subdomain to add a record for, if any.

    Returns:
        The encoded zone file content.
    """
    content = (
        f"; zone file for {domain}\n"
        "@ 600 IN SOA ns.example.com. admin.example.com. 1 7200 3600 1209600 3600\n"
    )
    if record is not None:
        content += RECORD_LINE.format(sub=record, value=secrets.token_hex(8))
    return content.encode("utf-8")


def _fast_import_stream(domains: list[str], num_commits: int) -> bytes:
    """Build a ``git fast-import`` stream for a long, realistic DNS-records history.

    The stream seeds one zone file per domain, then applies ``num_commits`` incremental
    record changes spread across the domains -- the same one-record-per-commit churn the
    provider produces over time. Building the whole history in a single stream is fast and
    avoids the object-store races that thousands of individual ``git commit`` invocations
    can trigger (background auto-gc/maintenance) on some hosts.

    Args:
        domains: the domain FQDNs to create zone files for.
        num_commits: the number of incremental record-change commits to add.

    Returns:
        The encoded fast-import stream.
    """
    chunks: list[bytes] = []
    counter = 0
    timestamp = 1700000000

    def add_blob(content: bytes) -> int:
        nonlocal counter
        counter += 1
        mark = counter
        chunks.append(f"blob\nmark :{mark}\ndata {len(content)}\n".encode("utf-8"))
        chunks.append(content)
        chunks.append(b"\n")
        return mark

    def add_commit(message: str, changes: list[tuple[int, str]]) -> None:
        nonlocal counter, timestamp
        counter += 1
        timestamp += 1
        msg = message.encode("utf-8")
        ident = f"benchmark <benchmark@example.com> {timestamp} +0000"
        chunks.append(f"commit refs/heads/main\nmark :{counter}\n".encode("utf-8"))
        chunks.append(f"author {ident}\ncommitter {ident}\n".encode("utf-8"))
        chunks.append(f"data {len(msg)}\n".encode("utf-8"))
        chunks.append(msg)
        chunks.append(b"\n")
        for blob_mark, path in changes:
            chunks.append(f"M 100644 :{blob_mark} {path}\n".encode("utf-8"))
        chunks.append(b"\n")

    seed_changes = [(add_blob(_zone_content(domain)), f"{domain}.domain") for domain in domains]
    add_commit("Seed zone files", seed_changes)

    for i in range(num_commits):
        domain = domains[i % len(domains)]
        blob_mark = add_blob(_zone_content(domain, record=f"_rec{i}"))
        add_commit(f"Add record {i} to {domain}", [(blob_mark, f"{domain}.domain")])

    chunks.append(b"done\n")
    return b"".join(chunks)


def build_git_repo(base_dir: Path, num_domains: int, num_commits: int) -> tuple[str, list[str]]:
    """Build a synthetic DNS-records repository with a realistic long history.

    Creates a bare "remote" repository and populates it, via a single ``git fast-import``
    stream, with ``num_domains`` zone files and ``num_commits`` incremental record changes,
    mimicking how the provider accumulates history one record at a time.

    Args:
        base_dir: directory in which to create the repository.
        num_domains: number of ``*.domain`` zone files to create.
        num_commits: number of incremental record-change commits to add.

    Returns:
        A tuple of the ``file://`` URL of the bare remote and the list of domain FQDNs.
    """
    remote = base_dir / "remote.git"
    _git(base_dir, "init", "--bare", "-b", "main", str(remote))

    domains = [f"example{i}.com" for i in range(num_domains)]
    logger.info("Building %d commits of history across %d zone files", num_commits, num_domains)
    stream = _fast_import_stream(domains, num_commits)
    result = subprocess.run(  # nosec B603 B607
        ["git", "fast-import", "--quiet", "--done"],
        cwd=str(remote),
        input=stream,
        capture_output=True,
        env=_git_env(),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git fast-import failed (exit {result.returncode}):\n"
            f"stderr: {result.stderr.decode('utf-8', 'replace')}"
        )
    return f"file://{remote}", domains


def setup_tracing():
    """Configure the global OpenTelemetry tracer with an in-memory exporter.

    Returns:
        The ``InMemorySpanExporter`` collecting all finished spans.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def export_traces(exporter, output: Path) -> int:
    """Write the collected spans to an OTLP JSON traces file.

    Args:
        exporter: the in-memory span exporter holding the finished spans.
        output: destination path for the OTLP JSON traces.

    Returns:
        The number of spans written.
    """
    from google.protobuf.json_format import MessageToJson
    from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans

    spans = exporter.get_finished_spans()
    request = encode_spans(spans)
    output.write_text(MessageToJson(request), encoding="utf-8")
    logger.info("Wrote %d spans to %s", len(spans), output)
    _report_clone_share(spans)
    return len(spans)


def _report_clone_share(spans) -> None:
    """Print how much wall-clock time is spent in ``git.clone`` versus the request roots.

    Args:
        spans: the finished spans collected by the exporter.
    """
    clone_ns = sum(s.end_time - s.start_time for s in spans if s.name == "git.clone")
    root_ns = sum(
        s.end_time - s.start_time for s in spans if s.name in ("handle_present", "handle_cleanup")
    )
    if not root_ns:
        return
    print(
        f"git.clone total={clone_ns / 1e9:.3f}s "
        f"({100 * clone_ns / root_ns:.1f}% of request time)",
        flush=True,
    )


def run_benchmark(repo_url: str, domains: list[str], iterations: int) -> None:
    """Drive present/cleanup requests through the Django view layer.

    Args:
        repo_url: the ``file://`` URL of the DNS-records repository.
        domains: the domain FQDNs seeded in the repository and database.
        iterations: number of present/cleanup cycles to run.
    """
    os.environ["DJANGO_GIT_REPO"] = repo_url
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.tests.settings")
    # Isolate every git invocation (including the provider's GitPython clone/commit path)
    # from the host's system/global git configuration, so runner settings such as commit
    # signing or auto-gc cannot break the benchmark. Identity is supplied via environment
    # variables, which take precedence over repository config and work without any config.
    os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
    os.environ["GIT_CONFIG_SYSTEM"] = os.devnull
    os.environ.setdefault("GIT_AUTHOR_NAME", "benchmark")
    os.environ.setdefault("GIT_AUTHOR_EMAIL", "benchmark@example.com")
    os.environ.setdefault("GIT_COMMITTER_NAME", "benchmark")
    os.environ.setdefault("GIT_COMMITTER_EMAIL", "benchmark@example.com")

    import django

    django.setup()

    from django.test.utils import setup_test_environment, teardown_test_environment

    setup_test_environment()

    from django.test.runner import DiscoverRunner

    runner = DiscoverRunner(verbosity=0)
    old_config = runner.setup_databases()
    try:
        _drive_requests(domains, iterations)
    finally:
        runner.teardown_databases(old_config)
        teardown_test_environment()


def _drive_requests(domains: list[str], iterations: int) -> None:
    """Seed the database and issue present/cleanup requests.

    Args:
        domains: the domain FQDNs to seed and exercise.
        iterations: number of present/cleanup cycles to run.
    """
    from api.models import AccessLevel, Domain, DomainUserPermission
    from django.contrib.auth.models import User
    from django.test import Client

    username = "benchmark"
    credential = secrets.token_hex()
    user = User.objects.create_user(username)
    user.set_password(credential)
    user.save()
    for fqdn in domains:
        domain = Domain.objects.create(fqdn=fqdn)
        DomainUserPermission.objects.create(
            domain=domain, user=user, access_level=AccessLevel.DOMAIN
        )

    token = base64.b64encode(f"{username}:{credential}".encode()).decode()
    auth = {"AUTHORIZATION": f"Basic {token}"}
    client = Client()

    present_times = []
    cleanup_times = []
    for i in range(iterations):
        fqdn = domains[i % len(domains)]
        challenge = f"{FQDN_PREFIX}{fqdn}"
        value = secrets.token_hex()

        start = time.perf_counter()
        response = client.post("/present", data={"fqdn": challenge, "value": value}, headers=auth)
        present_times.append(time.perf_counter() - start)
        assert response.status_code == 204, f"present failed: {response.status_code}"

        start = time.perf_counter()
        response = client.post("/cleanup", data={"fqdn": challenge, "value": value}, headers=auth)
        cleanup_times.append(time.perf_counter() - start)
        assert response.status_code == 204, f"cleanup failed: {response.status_code}"

    _report("present", present_times)
    _report("cleanup", cleanup_times)


def _report(label: str, times: list[float]) -> None:
    """Print timing statistics for a series of requests.

    Args:
        label: the request label.
        times: per-request durations in seconds.
    """
    if not times:
        return
    total = sum(times)
    print(
        f"{label}: n={len(times)} total={total:.3f}s mean={total / len(times):.3f}s "
        f"min={min(times):.3f}s max={max(times):.3f}s",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark.

    Args:
        argv: command-line arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commits",
        type=int,
        default=2000,
        help="Depth of the synthetic commit history (primary knob for clone cost).",
    )
    parser.add_argument(
        "--domains", type=int, default=5, help="Number of *.domain zone files to create."
    )
    parser.add_argument(
        "--iterations", type=int, default=10, help="Number of present/cleanup cycles to run."
    )
    parser.add_argument(
        "--traces-output",
        type=Path,
        default=Path("traces.json"),
        help="Path to write the OTLP JSON traces file.",
    )
    args = parser.parse_args(argv)

    exporter = setup_tracing()
    with TemporaryDirectory() as tmp_dir:
        repo_url, domains = build_git_repo(Path(tmp_dir), args.domains, args.commits)
        run_benchmark(repo_url, domains, args.iterations)
    export_traces(exporter, args.traces_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
