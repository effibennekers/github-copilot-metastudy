import logging
import logging.config
import click

from src.config import LOGGING_CONFIG
from src.workflows.labeling import run_labeling
from src.workflows.imports import (
    run_metadata_import,
    run_paper_preparation,
    import_labels_questions,
)
from src.workflows.queues import run_prepare_metadata_labeling, run_prepare_paper_download
from src.workflows.reporting import print_stats, list_questions
from src.workflows.downloads import run_downloads


@click.group()
def cli():
    logging.config.dictConfig(LOGGING_CONFIG)


@cli.command("label")
@click.option(
    "--jobs",
    "labeling_jobs",
    default=10,
    type=int,
    show_default=True,
    help="Max aantal labeling jobs",
)
def cli_label(labeling_jobs: int):
    res = run_labeling(labeling_jobs=labeling_jobs)
    click.echo(res)


@cli.command("prepare-download")
@click.argument("label_id", type=int)
def cli_prepare_download(label_id: int):
    count = run_prepare_paper_download(label_id)
    click.echo({"enqueued": count})


@cli.command("import-metadata")
@click.option("--max-records", type=int, default=None, help="Max records uit JSON")
@click.option(
    "--batch-size", type=int, default=1000, show_default=True, help="Batchgrootte voor insert"
)
def cli_import_metadata(max_records: int | None, batch_size: int):
    count = run_metadata_import(max_records=max_records, batch_size=batch_size)
    click.echo({"imported": count})


@cli.command("prepare-paper")
@click.option("--batch-size", type=int, default=None)
@click.option("--limit", type=int, default=None)
def cli_prepare_paper(batch_size: int | None, limit: int | None):
    created = run_paper_preparation(batch_size=batch_size, limit=limit)
    click.echo({"created": created})


@cli.command("prepare-labeling")
@click.argument("question_id", type=int)
@click.option(
    "--date-after", default="2025-09-01", show_default=True, help="Alleen metadata na deze datum"
)
def cli_prepare_labeling(question_id: int, date_after: str):
    enqueued = run_prepare_metadata_labeling(question_id=question_id, date_after=date_after)
    click.echo({"enqueued": enqueued})


@cli.command("import-labels")
def cli_import_labels():
    added = import_labels_questions()
    click.echo({"added": added})


@cli.command("list-questions")
def cli_list_questions():
    for line in list_questions():
        click.echo(line)


@cli.command("stats")
def cli_stats():
    print_stats()


def main():
    cli()


@cli.command("run-download")
@click.option("--limit", type=int, default=None, help="Max aantal downloads")
def cli_run_download(limit: int | None):
    stats = run_downloads(limit=limit)
    click.echo(stats)
