from pathlib import Path


def assemble(
    instruction_dir: Path,
    operation_file: str,
    *,
    workspace_instruction: str | None = None,
) -> list[str]:
    """Assemble explicit built-in, workspace, and operation instruction layers."""

    base_instruction_path = instruction_dir / "agents.md"
    instruction_path = instruction_dir / operation_file

    if not base_instruction_path.is_file():
        raise FileNotFoundError(
            "Built-in agent instruction file was not found at: "
            f"{base_instruction_path}"
        )

    if not instruction_path.is_file():
        raise FileNotFoundError(
            f"Instruction file '{operation_file}' was not found at: "
            f"{instruction_path}"
        )

    instructions: list[str] = []
    base_instruction = base_instruction_path.read_text(encoding="utf-8")

    if base_instruction.strip():
        instructions.append(base_instruction)
    if workspace_instruction and workspace_instruction.strip():
        instructions.append(workspace_instruction)

    operation_instruction = instruction_path.read_text(encoding="utf-8")

    if operation_instruction.strip():
        instructions.append(operation_instruction)

    return instructions
