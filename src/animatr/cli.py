"""CLI de ANIMATR usando Typer."""

import sys
from pathlib import Path

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="animatr",
    help="Motor Declarativo de Animación Audiovisual",
    add_completion=False,
)
console = Console()


@app.command()
def create(
    input_source: str = typer.Argument(
        ...,
        help="Prompt, archivo brief/script/yaml, o '-' para stdin",
    ),
    output: Path = typer.Option(
        Path("output/video.mp4"),
        "--output", "-o",
        help="Archivo de salida",
    ),
    no_agents: bool = typer.Option(
        False,
        "--no-agents",
        help="Bypass agentes AI (requiere YAML spec válido)",
    ),
    preview_only: bool = typer.Option(
        False,
        "--preview",
        help="Solo generar preview sin render completo",
    ),
    verbose: bool = typer.Option(
        True,
        "--verbose/--quiet", "-v/-q",
        help="Output detallado",
    ),
    max_iterations: int = typer.Option(
        3,
        "--iterations", "-i",
        help="Máximo de iteraciones del feedback loop",
    ),
) -> None:
    """Crea un video desde cualquier tipo de input usando AI agents.

    Ejemplos:
        animatr create "Hazme un video de 30s sobre blockchain"
        animatr create brief.yaml -o video.mp4
        animatr create script.txt --preview
        animatr create spec.yaml --no-agents
        cat spec.yaml | animatr create -
    """
    from animatr.sdk.orchestrator import AgentConfig, AgentOrchestrator

    # Leer input
    if input_source == "-":
        user_input = sys.stdin.read()
        console.print("[bold blue]📥 Leyendo desde stdin...[/]")
    elif Path(input_source).exists():
        user_input = Path(input_source).read_text()
        console.print(f"[bold blue]📥 Leyendo archivo:[/] {input_source}")
    else:
        user_input = input_source
        console.print("[bold blue]📥 Procesando prompt...[/]")

    # Crear output directory
    output.parent.mkdir(parents=True, exist_ok=True)

    # Configurar orchestrator
    config = AgentConfig(
        max_turns=20,
        max_budget_usd=2.0,
        verbose=verbose,
    )
    orchestrator = AgentOrchestrator(config)

    if preview_only:
        console.print("\n[bold cyan]🔍 Generando preview...[/]")
        result = orchestrator.create(
            prompt=user_input,
            output=str(output),
            preview=True,
        )
        _display_preview_result(result)
        return

    # Ejecutar creación
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Procesando con AI agents...", total=None)

        result = orchestrator.create(
            prompt=user_input,
            output=str(output),
            no_agents=no_agents,
        )

        progress.update(task, completed=True)

    _display_create_result(result, output)


def _display_preview_result(result: dict) -> None:
    """Muestra resultado del preview."""
    if not result.get("success"):
        console.print(f"[bold red]✗ Error:[/] {result.get('error')}")
        raise typer.Exit(1)

    console.print("\n[bold green]📋 Preview del Spec:[/]")
    console.print(f"  Escenas: {result.get('total_scenes', 0)}")
    console.print(f"  Duración total: {result.get('total_duration', 0):.1f}s")

    output_config = result.get("output_config", {})
    console.print(f"  Formato: {output_config.get('format', 'mp4')}")
    console.print(f"  Resolución: {output_config.get('resolution', '1920x1080')}")

    scenes = result.get("scenes_preview", [])
    if scenes:
        console.print("\n[bold cyan]Escenas:[/]")
        for scene in scenes:
            audio = "🔊" if scene.get("has_audio") else "🔇"
            char = "👤" if scene.get("has_character") else "  "
            console.print(f"  {scene['id']}: {scene['duration']} {audio} {char}")


def _display_create_result(result: dict, output: Path) -> None:
    """Muestra resultado de la creación."""
    if not result.get("success"):
        console.print(f"\n[bold red]✗ Error:[/] {result.get('error')}")
        raise typer.Exit(1)

    console.print(f"\n[bold green]✓ Proceso completado[/]")
    console.print(f"  Input type: {result.get('input_type', 'unknown')}")

    if result.get("bypassed_agents"):
        console.print("  [dim]Agentes: bypassed (YAML spec directo)[/dim]")
    else:
        console.print(f"  Aprobado: {'✅' if result.get('approved') else '⚠️ Requiere revisión'}")

    if result.get("video_path"):
        console.print(f"\n[bold green]🎬 Video generado:[/] {result['video_path']}")


@app.command()
def render(
    spec_file: Path = typer.Argument(..., help="Archivo YAML con el spec de animación"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Archivo de salida"),
) -> None:
    """Renderiza un video desde un spec YAML."""
    from animatr.orchestrator import Orchestrator
    from animatr.schema import AnimationSpec

    console.print(f"[bold blue]Cargando spec:[/] {spec_file}")

    spec = AnimationSpec.from_yaml(spec_file)
    orchestrator = Orchestrator(spec)

    output_path = output or Path(f"{spec_file.stem}.mp4")
    result = orchestrator.render(output_path)

    console.print(f"[bold green]✓ Video renderizado:[/] {result}")


@app.command()
def validate(
    spec_file: Path = typer.Argument(..., help="Archivo YAML con el spec de animación"),
) -> None:
    """Valida un spec YAML sin renderizar."""
    from animatr.schema import AnimationSpec

    console.print(f"[bold blue]Validando:[/] {spec_file}")

    try:
        spec = AnimationSpec.from_yaml(spec_file)
        console.print(f"[bold green]✓ Spec válido[/]")
        console.print(f"  Versión: {spec.version}")
        console.print(f"  Escenas: {len(spec.scenes)}")
        console.print(f"  Output: {spec.output.format} @ {spec.output.resolution}")
    except (ValidationError, yaml.YAMLError) as e:
        console.print(f"[bold red]✗ Error de validación:[/] {e}")
        raise typer.Exit(1)


@app.command()
def preview(
    spec_file: Path = typer.Argument(..., help="Archivo YAML con el spec de animación"),
    scene_id: str | None = typer.Option(None, "--scene", "-s", help="ID de escena específica"),
) -> None:
    """Genera un preview rápido del spec."""
    from animatr.schema import AnimationSpec

    console.print(f"[bold blue]Generando preview:[/] {spec_file}")

    spec = AnimationSpec.from_yaml(spec_file)

    if scene_id:
        scenes = [s for s in spec.scenes if s.id == scene_id]
        if not scenes:
            console.print(f"[bold red]✗ Escena no encontrada:[/] {scene_id}")
            raise typer.Exit(1)
    else:
        scenes = spec.scenes

    for scene in scenes:
        console.print(f"\n[bold cyan]Escena:[/] {scene.id}")
        console.print(f"  Duración: {scene.duration}")
        if scene.character:
            console.print(f"  Personaje: {scene.character.asset}")
        if scene.audio:
            console.print(f"  Audio: {scene.audio.provider} ({scene.audio.voice})")


if __name__ == "__main__":
    app()
