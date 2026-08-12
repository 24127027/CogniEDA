import inspect
from pathlib import Path

def load(file_name: str) -> str:
    """
    Reads an instruction file from the calling agent's 'instruction/' directory.
    
    :param file_name: Filename or relative path inside the agent's instruction/ folder.
    :return: Content of the file as a string.
    """
    caller_frame = inspect.stack()[1]
    caller_path = Path(caller_frame.filename).resolve()
    
    agent_dir = caller_path.parent
    instruction_path = agent_dir / "instruction" / file_name
    
    if not instruction_path.is_file():
        raise FileNotFoundError(
            f"Instruction file '{file_name}' was not found at: {instruction_path}"
        )
    
    return instruction_path.read_text(encoding="utf-8")