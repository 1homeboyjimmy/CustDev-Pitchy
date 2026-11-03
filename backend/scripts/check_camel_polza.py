"""Exercise a real CAMEL tool call using the approved simulation model."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_settings import sync_polza_environment
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType


def main():
    settings = sync_polza_environment()
    calls = []

    def record_answer(answer: str) -> str:
        """Record an interview answer.

        Args:
            answer: The respondent's answer.

        Returns:
            Confirmation that the answer was recorded.
        """
        calls.append(answer)
        return 'recorded'

    model = ModelFactory.create(model_platform=ModelPlatformType.OPENAI,
        model_type=settings['models']['simulation'], api_key=settings['api_key'], url=settings['base_url'],
        model_config_dict={'temperature': 0.2, 'max_tokens': 1024}, timeout=90, max_retries=1)
    agent = ChatAgent(system_message='Follow instructions. Use the provided tool when requested.',
        model=model, tools=[FunctionTool(record_answer)])
    result = agent.step('Call record_answer with answer="ok", then reply "done".')
    if calls != ['ok']:
        raise RuntimeError(f'CAMEL tool call did not complete; calls={len(calls)}')
    print(f"CAMEL tool call passed: {settings['models']['simulation']}, provider={settings['base_url']}")


if __name__ == '__main__':
    main()
