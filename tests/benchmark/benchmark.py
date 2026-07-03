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


def _git(cwd: Path, *args: str) -> None:
    """Run a git command in ``cwd``, raising on failure.

    Args:
        cwd: working directory for the git command.
        args: git command arguments.
    """
    subprocess.run(  # nosec B603 B607
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
    )


def build_git_repo(base_dir: Path, num_domains: int, num_commits: int) -> tuple[str, list[str]]:
    """Build a synthetic DNS-records repository with a realistic long history.

    Creates a bare "remote" repository and seeds it with ``num_domains`` zone files and
    ``num_commits`` incremental record changes, mimicking how the provider accumulates
    history one record at a time.

    Args:
        base_dir: directory in which to create the repositories.
        num_domains: number of ``*.domain`` zone files to create.
        num_commits: number of incremental record-change commits to add.

    Returns:
        A tuple of the ``file://`` URL of the bare remote and the list of domain FQDNs.
    """
    remote = base_dir / "remote.git"
    work = base_dir / "work"
    _git(base_dir, "init", "--bare", "-b", "main", str(remote))
    _git(base_dir, "init", "-b", "main", str(work))
    _git(work, "config", "user.email", "benchmark@example.com")
    _git(work, "config", "user.name", "benchmark")

    domains = [f"example{i}.com" for i in range(num_domains)]
    for domain in domains:
        zone_file = work / f"{domain}.domain"
        zone_file.write_text(
            f"; zone file for {domain}\n"
            "@ 600 IN SOA ns.example.com. admin.example.com. 1 7200 3600 1209600 3600\n",
            encoding="utf-8",
        )
    _git(work, "add", ".")
    _git(work, "commit", "-m", "Seed zone files")

    logger.info("Building %d commits of history across %d zone files", num_commits, num_domains)
    for i in range(num_commits):
        domain = domains[i % num_domains]
        zone_file = work / f"{domain}.domain"
        with zone_file.open("a", encoding="utf-8") as handle:
            handle.write(RECORD_LINE.format(sub=f"_rec{i}", value=secrets.token_hex(8)))
        _git(work, "add", f"{domain}.domain")
        _git(work, "commit", "-m", f"Add record {i} to {domain}")

    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "origin", "main")
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
