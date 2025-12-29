"""CLI de ANIMATR usando Typer."""

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="animatr",
    help="Motor Declarativo de Animación Audiovisual",
    add_completion=False,
)
console = Console()


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
    except Exception as e:
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
