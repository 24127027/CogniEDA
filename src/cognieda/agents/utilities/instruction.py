import inspect
from pathlib import Path


def assemble(
    file_name: str,
    base_instruction: str | None = None,
) -> list[str]:
    """
    Load an operation instruction and optionally prepend the agent's
    base instruction.

    The operation instruction is loaded from the calling agent's
    ``instruction/`` directory.

    If ``base_instruction`` is not provided, ``agents.md`` in the same
    directory is used when present.

    :param file_name: Filename or relative path inside the agent's
        ``instruction/`` directory.
    :param base_instruction: Optional base agent instruction.
    :return: Instruction parts in base-then-operation order.
    """
    caller_frame = inspect.stack()[1]
    caller_path = Path(caller_frame.filename).resolve()

    instruction_dir = caller_path.parent / "instruction"
    instruction_path = instruction_dir / file_name

    if not instruction_path.is_file():
        raise FileNotFoundError(
            f"Instruction file '{file_name}' was not found at: "
            f"{instruction_path}"
        )

    if base_instruction is None:
        base_instruction_path = instruction_dir / "agents.md"

        if base_instruction_path.is_file():
            base_instruction = base_instruction_path.read_text(
                encoding="utf-8"
            )

    instructions: list[str] = []

    if base_instruction and base_instruction.strip():
        instructions.append(base_instruction)

    operation_instruction = instruction_path.read_text(encoding="utf-8")

    if operation_instruction.strip():
        instructions.append(operation_instruction)

    return instructions