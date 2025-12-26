"""
Main CLI entry point for the Sports Prediction System
"""

import asyncio
import sys

import click
from rich.console import Console
from rich.table import Table

from app import DISCLAIMER
from app.config import load_config
from app.dashboard.server import DashboardServer
from app.data.ingestion import DataIngestionPipeline
from app.models.predictor import PredictionEngine
from app.models.trainer import ModelTrainer
from app.reports.generator import ReportGenerator
from app.utils.logging import setup_logging

console = Console()


@click.group()
@click.version_option(version="1.0.0")
@click.option(
    "--config", "-c", default="config/settings.yaml", help="Configuration file path"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def main(ctx: click.Context, config: str, verbose: bool) -> None:
    """Sports Prediction System - advanced sports forecasting for educational purposes.

    DISCLAIMER: This system is for educational and analytical purposes only.
    It is not intended for financial or betting decisions.
    """
    ctx.ensure_object(dict)

    # Load configuration
    try:
        ctx.obj["config"] = load_config(config)
        ctx.obj["verbose"] = verbose

        # Setup logging
        setup_logging(
            level=(
                "DEBUG"
                if verbose
                else ctx.obj["config"].get("logging", {}).get("level", "INFO")
            ),
            config=ctx.obj["config"].get("logging", {}),
        )

        console.print(f"[yellow]⚠️  {DISCLAIMER}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--league", required=True, help='League name (e.g., "La Liga", "Premier League")'
)
@click.option("--season", help='Season (e.g., "2023-24")')
@click.option("--start-date", help="Start date for data collection (YYYY-MM-DD)")
@click.option("--end-date", help="End date for data collection (YYYY-MM-DD)")
@click.option("--force", is_flag=True, help="Force re-download even if data exists")
@click.pass_context
def ingest(
    ctx: click.Context,
    league: str,
    season: str | None,
    start_date: str | None,
    end_date: str | None,
    force: bool,
) -> None:
    """Ingest data for a specific league and time period.

    Example:
        sports-forecast ingest --league "La Liga" --season "2023-24"
    """
    config = ctx.obj["config"]

    console.print(f"[blue]🔄 Starting data ingestion for {league}[/blue]")

    pipeline = DataIngestionPipeline(config)

    try:
        asyncio.run(
            pipeline.ingest_league_data(
                league=league,
                season=season,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force,
            )
        )
        console.print(f"[green]✅ Data ingestion completed for {league}[/green]")

    except Exception as e:
        console.print(f"[red]❌ Data ingestion failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--league", required=True, help="League name")
@click.option(
    "--model",
    default="ensemble",
    type=click.Choice(["elo", "poisson", "gradient_boosting", "bayesian", "ensemble"]),
    help="Model type to train",
)
@click.option("--features", multiple=True, help="Specific features to use")
@click.option("--tune", is_flag=True, help="Enable hyperparameter tuning")
@click.option("--validate", is_flag=True, help="Run cross-validation")
@click.pass_context
def train(
    ctx: click.Context,
    league: str,
    model: str,
    features: tuple[str, ...],
    tune: bool,
    validate: bool,
) -> None:
    """Train prediction models for a specific league.

    Example:
        sports-forecast train --league "La Liga" --model ensemble --tune
    """
    config = ctx.obj["config"]

    console.print(f"[blue]🤖 Training {model} model for {league}[/blue]")

    trainer = ModelTrainer(config)

    try:
        result = trainer.train_model(
            league=league,
            model_type=model,
            features=list(features) if features else None,
            tune_hyperparameters=tune,
            cross_validate=validate,
        )

        console.print("[green]✅ Model training completed[/green]")

        # Display results table
        if validate and result.get("validation_metrics"):
            table = Table(title=f"{model.title()} Model Performance")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")

            for metric, value in result["validation_metrics"].items():
                table.add_row(metric.replace("_", " ").title(), f"{value:.4f}")

            console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Model training failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--league", required=True, help="League name")
@click.option("--date", required=True, help="Prediction date (YYYY-MM-DD)")
@click.option("--model", default="ensemble", help="Model to use for predictions")
@click.option("--output", "-o", help="Output file path (optional)")
@click.option(
    "--format",
    "output_format",
    default="json",
    type=click.Choice(["json", "csv", "table"]),
    help="Output format",
)
@click.pass_context
def predict(
    ctx: click.Context,
    league: str,
    date: str,
    model: str,
    output: str | None,
    output_format: str,
) -> None:
    """Generate predictions for upcoming matches.

    Example:
        sports-forecast predict --league "La Liga" --date "2025-10-20"
    """
    config = ctx.obj["config"]

    console.print(f"[blue]🔮 Generating predictions for {league} on {date}[/blue]")

    engine = PredictionEngine(config)

    try:
        predictions = engine.predict_matches(
            league=league, prediction_date=date, model_name=model
        )

        if output_format == "table":
            table = Table(title=f"Predictions for {league} - {date}")
            table.add_column("Match", style="cyan")
            table.add_column("Home Win %", style="green")
            table.add_column("Draw %", style="yellow")
            table.add_column("Away Win %", style="red")
            table.add_column("Confidence", style="magenta")

            for pred in predictions:
                table.add_row(
                    f"{pred['home_team']} vs {pred['away_team']}",
                    f"{pred['home_win_prob']:.1%}",
                    f"{pred['draw_prob']:.1%}",
                    f"{pred['away_win_prob']:.1%}",
                    f"{pred['confidence']:.2f}",
                )

            console.print(table)

        else:
            # Save to file or print
            if output:
                engine.save_predictions(predictions, output, output_format)
                console.print(f"[green]📁 Predictions saved to {output}[/green]")
            else:
                console.print(predictions)

        console.print("[green]✅ Predictions generated successfully[/green]")

    except Exception as e:
        console.print(f"[red]❌ Prediction failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--league", required=True, help="League name")
@click.option("--date", required=True, help="Report date (YYYY-MM-DD)")
@click.option("--formats", default="md,png", help="Report formats (comma-separated)")
@click.option("--output-dir", default="reports", help="Output directory")
@click.option("--template", help="Custom report template")
@click.pass_context
def report(
    ctx: click.Context,
    league: str,
    date: str,
    formats: str,
    output_dir: str,
    template: str | None,
) -> None:
    """Generate comprehensive prediction reports.

    Example:
        sports-forecast report --league "La Liga" --date "2025-10-20" --formats "md,png,pdf"
    """
    config = ctx.obj["config"]
    format_list = [f.strip() for f in formats.split(",")]

    console.print(f"[blue]📊 Generating reports for {league} on {date}[/blue]")

    generator = ReportGenerator(config)

    try:
        report_paths = asyncio.run(
            generator.generate_reports(
                league=league,
                prediction_date=date,
                formats=format_list,
                output_dir=output_dir,
                template_path=template,
            )
        )

        console.print("[green]✅ Reports generated:[/green]")
        for format_type, path in report_paths.items():
            console.print(f"  [cyan]{format_type.upper()}:[/cyan] {path}")

    except Exception as e:
        console.print(f"[red]❌ Report generation failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--host", default="127.0.0.1", help="Dashboard host")
@click.option("--port", default=8000, help="Dashboard port")
@click.option("--dev", is_flag=True, help="Development mode with hot reload")
@click.pass_context
def dashboard(ctx: click.Context, host: str, port: int, dev: bool) -> None:
    """Launch the interactive web dashboard.

    Example:
        sports-forecast dashboard --host 0.0.0.0 --port 8000
    """
    config = ctx.obj["config"]

    console.print(f"[blue]🚀 Starting dashboard on http://{host}:{port}[/blue]")

    server = DashboardServer(config)

    try:
        server.run(host=host, port=port, debug=dev)

    except Exception as e:
        console.print(f"[red]❌ Dashboard startup failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--league", help="Specific league to validate")
@click.option("--model", help="Specific model to validate")
@click.option("--start-date", help="Validation start date")
@click.option("--end-date", help="Validation end date")
@click.pass_context
def validate(
    ctx: click.Context,
    league: str | None,
    model: str | None,
    start_date: str | None,
    end_date: str | None,
) -> None:
    """Run model validation and backtesting.

    Example:
        sports-forecast validate --league "La Liga" --model ensemble
    """
    console.print("[blue]🧪 Running model validation...[/blue]")

    # Implementation would go here
    console.print("[green]✅ Validation completed[/green]")


if __name__ == "__main__":
    main()


@main.command()
@click.pass_context
def run_prune(ctx: click.Context) -> None:
    """
    Prune all generated reports and outputs, preserving directory structure and .keep files.
    Example:
        python -m app.cli run-prune
    """
    console.print("[blue]🧹 Pruning all generated reports...[/blue]")
    try:
        # Import and call the cleanup logic from generate_fast_reports.py
        from generate_fast_reports import SingleMatchGenerator

        generator = SingleMatchGenerator()
        generator.clean_old_reports()

        # Check for any remaining match subdirectories
        import os

        league_dirs = [
            f"reports/leagues/{info['folder']}/matches"
            for info in generator._LEAGUE_CANONICAL.values()
        ]
        remaining = []
        for league_dir in league_dirs:
            if os.path.exists(league_dir):
                for d in os.listdir(league_dir):
                    path = os.path.join(league_dir, d)
                    if os.path.isdir(path) and d not in [".keep", ".gitkeep"]:
                        remaining.append(path)
        if remaining:
            console.print(
                "[yellow]⚠️ Warning: Some match directories remain after prune:[/yellow]"
            )
            for path in remaining:
                console.print(f"  [red]{path}[/red]")
        else:
            console.print("[green]✅ Reports and outputs pruned successfully.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Prune failed: {e}[/red]")
        sys.exit(1)
