# ANIMATR AI Agents System Design

**Date**: 2024-12-29
**Status**: Approved
**Author**: Brainstorming Session (Claude + User)

---

## Executive Summary

This document describes the design for integrating an AI multi-agent system into ANIMATR. The system combines **Claude Agent SDK** (orchestration) with **CrewAI** (agent collaboration) to enable hybrid input processing - from natural language prompts to complete YAML specs.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Hybrid (Agent SDK + CrewAI) | Best of both: Claude control + agent collaboration |
| LLM Backend | DeepSeek for CrewAI | Cost-effective for high-volume agent operations |
| TTS Provider | ElevenLabs (primary) | Already integrated, high quality |
| Input Format | Hybrid (prompt/brief/script/yaml) | Maximum flexibility for users |

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ANIMATR + AI AGENTS                              │
├─────────────────────────────────────────────────────────────────────────┤
│  INPUT LAYER (HYBRID)                                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                    │
│  │ Prompt  │  │  Brief  │  │ Script  │  │  YAML   │ ← BYPASS           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘                    │
│       └───────────┬┴───────────┬┘            │                          │
├───────────────────┼────────────┼─────────────┼──────────────────────────┤
│  ORCHESTRATION (Claude Agent SDK)            │                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Claude Orchestrator                                             │   │
│  │  • MCP Server → CrewAI                                          │   │
│  │  • Permission hooks                                              │   │
│  │  • Flow control                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│  CREW LAYER (CrewAI + DeepSeek)                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Director → Head Filmmaker → Head Animator → Specialist Agents   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│  RENDER LAYER (Existing Pipeline)                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                       │
│  │ElevenLab│ │  Moho   │ │ Blender │ │ FFmpeg  │                       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘                       │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUT: MP4 / Preview / Multi-format                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Hierarchy

```
                    ┌─────────────────┐
                    │  Claude (SDK)   │  ← Backend/Infrastructure
                    │   Orchestrator  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  🎯 DIRECTOR    │  ← JEFE MÁXIMO
                    │  Visión global  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                              ▼
    ┌─────────────────┐            ┌─────────────────┐
    │ 🎬 HEAD FILMMAKER│            │ 🎭 HEAD ANIMATOR │
    │   Narrativa      │            │   Visual/Motion  │
    └────────┬────────┘            └────────┬────────┘
             │                              │
    ┌────────┴────────┐            ┌────────┴────────┐
    ▼        ▼        ▼            ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐    ┌──────┐ ┌──────┐ ┌──────┐
│Intake│ │Guion-│ │ QA   │    │Design│ │Técni-│ │Render│
│      │ │ista  │ │      │    │er    │ │co    │ │er    │
└──────┘ └──────┘ └──────┘    └──────┘ └──────┘ └──────┘
```

### Agent Definitions

| Agent | Role | Reports To | Key Responsibility |
|-------|------|------------|-------------------|
| **Director** | Creative Director | Claude SDK | Final approval, creative vision |
| **Head Filmmaker** | Narrative Lead | Director | Storytelling, pacing, dialogue |
| **Head Animator** | Visual Lead | Director | Animation quality, expressions |
| **Intake** | Input Analyst | Filmmaker | Parse any input → structured brief |
| **Guionista** | Scriptwriter | Filmmaker | Dialogue, narration, emotions |
| **Designer** | Visual Designer | Animator | Assets, colors, composition |
| **Técnico** | Spec Engineer | Animator | Generate valid YAML specs |
| **Renderer** | Pipeline Executor | Animator | Trigger render, handle errors |
| **QA** | Quality Reviewer | Filmmaker | Validate output, suggest fixes |

---

## 3. Input Detection Flow

### Input Types

| Type | Example | Processing |
|------|---------|------------|
| **YAML Spec** | Complete AnimationSpec | BYPASS agents → Direct render |
| **Brief** | `{topic, duration, tone}` | PARTIAL crew (skip Intake) |
| **Script** | `ESCENA 1: [action] CHAR: dialog` | FULL crew |
| **Prompt** | "Hazme un video sobre..." | FULL crew with discovery |

### Detection Logic

```python
class InputType(Enum):
    YAML_SPEC = "yaml_spec"   # Bypass
    BRIEF = "brief"           # Partial
    SCRIPT = "script"         # Full
    PROMPT = "prompt"         # Full + discovery
```

---

## 4. CrewAI + Agent SDK Integration

### MCP Server Tools

```python
animatr_mcp_server = create_sdk_mcp_server(
    name="animatr",
    tools=[
        run_crew,        # Execute CrewAI crew
        render,          # Trigger render pipeline
        validate_spec,   # Validate YAML
        preview,         # Quick preview
    ]
)
```

### Claude SDK Configuration

```python
options = ClaudeAgentOptions(
    mcp_servers={"animatr": animatr_mcp_server},
    allowed_tools=["mcp__animatr__*"],
    hooks={
        "PreToolUse": [pre_render_validation],
        "PostToolUse": [post_render_qa]
    },
    max_turns=20,
    max_budget_usd=2.0
)
```

### CrewAI Configuration

```python
@CrewBase
class AnimatrCrew:
    llm = ChatOpenAI(
        base_url="https://api.deepseek.com/v1",
        api_key=DEEPSEEK_API_KEY,
        model="deepseek-chat"
    )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[...],
            tasks=[...],
            process=Process.hierarchical,
            manager_agent=self.director()
        )
```

---

## 5. Feedback Loop

### Flow

```
Render → QA Review → Approved?
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
         DELIVERY            REVISION
              │                   │
              │         Route to responsible agent
              │                   │
              │         Apply fixes → Re-render
              │                   │
              └─────────┬─────────┘
                        │
              Max 3 iterations
              Then: Human review required
```

### QA Scoring

| Aspect | Weight | Threshold |
|--------|--------|-----------|
| Lip-sync | 25% | ±50ms |
| Dialogue | 20% | Coherent |
| Pacing | 15% | Matches spec |
| Visual | 20% | Composition |
| Audio | 15% | Clear, no noise |
| Technical | 5% | Specs met |

**Approval**: Score ≥ 80% AND no critical issues

---

## 6. File Structure

```
src/animatr/
├── __init__.py
├── cli.py                    # ✅ Exists
├── schema.py                 # ✅ Exists
├── orchestrator.py           # ✅ Exists → Extend
│
├── engines/                  # ✅ Exists
│   ├── base.py
│   ├── audio.py             # ✅ ElevenLabs implemented
│   ├── moho.py              # 🆕 TODO
│   └── blender.py           # 🆕 TODO
│
├── agents/                   # 🆕 NEW MODULE
│   ├── __init__.py
│   ├── crew.py              # CrewAI crew definition
│   ├── director.py
│   ├── filmmaker.py
│   ├── animator.py
│   ├── intake.py
│   ├── guionista.py
│   ├── designer.py
│   ├── tecnico.py
│   ├── renderer.py
│   ├── qa.py
│   └── feedback_loop.py
│
└── sdk/                      # 🆕 NEW MODULE
    ├── __init__.py
    ├── orchestrator.py       # Claude Agent SDK wrapper
    ├── tools.py              # MCP tools
    └── hooks.py              # Permission hooks
```

---

## 7. Dependencies to Add

```toml
# pyproject.toml additions

[project.dependencies]
# ... existing ...
crewai = ">=0.86"
crewai-tools = ">=0.14"
claude-agent-sdk = ">=0.1"
langchain-openai = ">=0.2"
```

---

## 8. Environment Variables

```bash
# .env additions

# DeepSeek (CrewAI backend)
DEEPSEEK_API_KEY=sk-508af05460f9411895c0dc4729cd9249

# ElevenLabs (TTS)
ELEVENLABS_API_KEY=sk_2d052e89d3e36c601061d1e23cbf28dcedcc0e367c316f3e

# Claude (Agent SDK) - uses ANTHROPIC_API_KEY
ANTHROPIC_API_KEY=your_key_here
```

---

## 9. CLI Commands

### New Command: `animatr create`

```bash
# From natural language prompt
animatr create "Hazme un video de 30s sobre blockchain"

# From brief file
animatr create brief.yaml -o video.mp4

# From script
animatr create script.txt --preview

# Bypass agents (direct YAML)
animatr create spec.yaml --no-agents

# From stdin
cat spec.yaml | animatr create -
```

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Add dependencies (crewai, claude-agent-sdk)
- [ ] Create `agents/` module structure
- [ ] Create `sdk/` module structure
- [ ] Implement InputDetector

### Phase 2: Agents (Week 2)
- [ ] Implement all 9 agents
- [ ] Create YAML configs for agents/tasks
- [ ] Implement AnimatrCrew class
- [ ] Test crew with simple prompts

### Phase 3: Integration (Week 3)
- [ ] Implement MCP server tools
- [ ] Implement Claude SDK orchestrator
- [ ] Connect CrewAI ↔ Agent SDK
- [ ] Add hooks and permissions

### Phase 4: Feedback Loop (Week 4)
- [ ] Implement QA agent analysis tools
- [ ] Implement FeedbackLoopController
- [ ] Add revision routing logic
- [ ] Test full iteration cycle

### Phase 5: Polish (Week 5)
- [ ] Add `animatr create` CLI command
- [ ] Error handling and logging
- [ ] Documentation
- [ ] Integration tests

---

## 11. Success Criteria

1. ✅ Natural language prompt → rendered video (end-to-end)
2. ✅ All 4 input types correctly detected and processed
3. ✅ QA feedback loop improves output quality
4. ✅ Max 3 iterations before human review
5. ✅ CLI command works with all input types
6. ✅ Agents use DeepSeek (cost-effective)
7. ✅ Claude SDK maintains control and permissions

---

## Appendix A: Agent YAML Configs

Located in `src/animatr/agents/config/`

### agents.yaml
```yaml
director:
  role: Creative Director
  goal: Ensure cohesive creative vision and final approval
  backstory: >
    Veterano director con 20+ años en animación y publicidad.
    Tu ojo para el detalle garantiza que cada video cuente
    una historia coherente.

head_filmmaker:
  role: Head of Narrative & Storytelling
  goal: Craft compelling narratives with perfect pacing
  backstory: >
    Guionista y directora con background en cine documental.
    Especializada en storytelling para educación y marketing.

# ... etc
```

### tasks.yaml
```yaml
intake_task:
  description: >
    Analyze the user input and convert it to a structured creative brief.
    Input type: {input_type}
    Content: {user_input}
  expected_output: A structured CreativeBrief in JSON format

script_task:
  description: >
    Based on the creative brief, write engaging dialogue and narration.
    Brief: {creative_brief}
  expected_output: Script with dialogue, emotions, and timing markers

spec_task:
  description: >
    Generate a valid AnimationSpec YAML from the script and visual design.
  expected_output: Complete AnimationSpec YAML
  output_file: output/spec.yaml
```

---

## Appendix B: API Keys Reference

| Service | Key Variable | Purpose |
|---------|-------------|---------|
| DeepSeek | `DEEPSEEK_API_KEY` | CrewAI agent LLM |
| ElevenLabs | `ELEVENLABS_API_KEY` | TTS audio generation |
| OpenAI | `OPENAI_API_KEY` | Backup TTS |
| Anthropic | `ANTHROPIC_API_KEY` | Claude Agent SDK |

---

**Document Status**: Complete
**Ready for**: Implementation
