# 🎬 ANIMATR

> Motor Declarativo de Animación Audiovisual
>
> [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
> [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
> [![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
>
> **ANIMATR** te permite crear videos animados profesionales describiendo escenas en YAML, en lugar de animar manualmente.
>
> ## ✨ Features
>
> - 📝 **Specs Declarativos**: Define QUÉ quieres, no CÓMO hacerlo
> - - 🎭 **Personajes Animados**: Lip-sync automático y expresiones
>   - - 🎙️ **TTS Integrado**: OpenAI y ElevenLabs
>     - - 🎬 **Render Profesional**: Moho Pro + Blender pipeline
>       - - 💻 **CLI-First**: Perfecto para automatización
>        
>         - ## 🚀 Quick Start
>        
>         - ### Instalación
>        
>         - ```bash
> pip install animatr
> ```
>
> ### Uso Básico
>
> ```bash
> # Crear un video desde un spec
> animatr render video.yaml
>
> # Validar spec sin renderizar
> animatr validate video.yaml
>
> # Preview rápido
> animatr preview video.yaml
> ```
>
> ### Ejemplo de Spec
>
> ```yaml
> # video.yaml
> version: "1.0"
> output:
>   format: mp4
>   resolution: 1920x1080
>   fps: 30
>
> scenes:
>   - id: intro
>     duration: 5s
>     character:
>       asset: ./characters/presenter.moho
>       position: center
>       expression: happy
>     audio:
>       text: "¡Hola! Bienvenidos a este tutorial."
>       voice: alloy
>       provider: openai
>     background:
>       color: "#1a1a2e"
> ```
>
> ## 📚 Documentation
>
> - [Getting Started](docs/getting-started.md)
> - - [Spec Reference](docs/spec-reference.md)
>   - - [API Documentation](docs/api/)
>    
>     - ## 🛠️ Development
>    
>     - ```bash
>       # Clone
>       git clone https://github.com/nadalpiantini/animatr.git
>       cd animatr
>
>       # Install with dev dependencies
>       pip install -e ".[dev]"
>
>       # Run tests
>       pytest
>
>       # Lint
>       ruff check .
>       ```
>
> ## 📋 Requirements
>
> - Python 3.11+
> - - Moho Pro 14+ (for character animation)
>   - - Blender 4.0+ (for scene composition)
>     - - FFmpeg 6.0+
>      
>       - ## 🗺️ Roadmap
>      
>       - - [x] Core spec parser
>         - [ ] - [x] Audio engine (TTS)
>         - [ ] - [ ] Moho integration
>         - [ ] - [ ] Blender compositor
>         - [ ] - [ ] Web UI
>         - [ ] - [ ] API REST
>        
>         - [ ] ## 📄 License
>        
>         - [ ] MIT License - see [LICENSE](LICENSE) for details.
>
> ## 🤝 Contributing
>
> Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.
>
> ---
>
> Made with ❤️ for the animation community
