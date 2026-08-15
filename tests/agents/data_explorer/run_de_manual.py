import argparse
import asyncio
import hashlib
from pathlib import Path
from uuid import uuid4

import pandas as pd
from dotenv import load_dotenv

from cognieda.agents.data_explorer.agent import DataExplorer
from cognieda.agents.data_explorer.context import DEInput
from cognieda.application.ports.llm import ModelConfig


async def main() -> None:
    load_dotenv()
    
    import os
    default_provider = os.getenv("COGNIEDA_MODEL_PROVIDER", "openai")
    default_model = os.getenv("COGNIEDA_MODEL_NAME", "gpt-4o")

    parser = argparse.ArgumentParser(description="Run Data Explorer (DE) manually for fast feedback.")
    parser.add_argument("--dataset", type=str, required=True, help="Path to the dataset (CSV or Parquet)")
    parser.add_argument("--instruction", type=str, default=None, help="Optional initial instruction for the DE")
    parser.add_argument("--provider", type=str, default=default_provider, help=f"LLM Provider (default: {default_provider})")
    parser.add_argument("--model", type=str, default=default_model, help=f"Model name (default: {default_model})")
    
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset {dataset_path} does not exist.")
        return

    # Load dataframe
    if dataset_path.suffix == ".csv":
        df = pd.read_csv(dataset_path)
    elif dataset_path.suffix == ".parquet":
        df = pd.read_parquet(dataset_path)
    else:
        print("Error: Dataset must be a .csv or .parquet file.")
        return

    dataset_digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    
    from cognieda.infrastructure.llm.factory import AgentFactory

    class SimpleToolingConfig:
        @property
        def agents_config_path(self) -> Path:
            return Path("config/agents.toml")
        @property
        def mcp_config_path(self) -> Path:
            return Path("config/mcp.toml")
        @property
        def skills_config_path(self) -> Path:
            return Path("config/skills.toml")

    tooling_cfg = SimpleToolingConfig()
    factory = AgentFactory(tooling_config=tooling_cfg)

    # Resolve API Key
    api_key = (
        os.getenv("MODEL_API_KEY") or 
        os.getenv("OPENAI_API_KEY") or 
        os.getenv("GOOGLE_API_KEY") or 
        os.getenv("ANTHROPIC_API_KEY")
    )
    if not api_key:
        print("Warning: API Key environment variable not set. LLM calls will fail unless provided.")

    config = ModelConfig(provider=args.provider, model_name=args.model, api_key=api_key or "")
    de = DataExplorer(agent_factory=factory, model_config=config)
    
    print(f"\n--- Running Data Explorer ---")
    print(f"Dataset: {args.dataset} ({len(df)} rows)")
    if args.instruction:
        print(f"Initial Instruction: {args.instruction}")
    print(f"Model: {args.provider}/{args.model}\n")

    de_input = DEInput(
        task_instruction="Profile the dataset",
        dataset_path=str(dataset_path),
        dataset_digest=dataset_digest,
        data_profile=None,
        dataframe=df,
    )
    
    try:
        print("\n[Pass 1] Running Profiling...")
        profile_output = await de.run(uuid4(), de_input)
        
        if not profile_output.data_profile:
            print("Failed to generate DataProfile.")
            if profile_output.error:
                print(f"Error: {profile_output.error.message}")
            return
            
        print("DataProfile successfully generated!")
        
        while True:
            if args.instruction:
                instruction = args.instruction
                args.instruction = None  # Consume the initial instruction
                print(f"\n>>> Running initial instruction: {instruction}")
            else:
                try:
                    instruction = input("\nAsk a question (or type 'exit' to quit): ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                
                if not instruction:
                    continue
                if instruction.lower() in ('exit', 'quit'):
                    break
            
            print("\n[Analysis Pass] Thinking...")
            de_input_pass2 = DEInput(
                task_instruction=instruction,
                dataset_path=str(dataset_path),
                dataset_digest=dataset_digest,
                data_profile=profile_output.data_profile,
                dataframe=df,
            )
            
            analysis_output = await de.run(uuid4(), de_input_pass2)
            
            print("\n--- Analysis Output ---")
            print(f"Summary: {analysis_output.summary}")
            if analysis_output.evidence:
                print("\nEvidence Emitted:")
                for k, v in analysis_output.evidence.content.items():
                    print(f"  {k}: {v}")
            if analysis_output.error:
                print("\nError Emitted:")
                print(f"  [{analysis_output.error.code}] {analysis_output.error.message}")
            
    except Exception as e:
        print(f"\nExecution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
