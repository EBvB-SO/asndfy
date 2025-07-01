import os
import pytest
import openai

@pytest.fixture(autouse=True)
def ensure_api_key():
    """
    Make sure we have an API key in the environment.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key, "OPENAI_API_KEY environment variable must be set to run OpenAI integration tests"
    openai.api_key = api_key

def test_list_models():
    """
    A quick smoke‐test that the OpenAI API is reachable by listing models.
    """
    models = openai.Model.list()
    # We expect at least one model in the list
    assert hasattr(models, "data"), "Response shape has changed"
    assert len(models.data) > 0, "No models returned — check your API key and network"

def test_chat_completion_echo():
    """
    A minimal ChatCompletion call to verify the chat endpoint is working.
    """
    resp = openai.ChatCompletion.create(
        model="gpt-4.1",
        messages=[{"role": "system", "content": "Say hello"}],
        max_tokens=1,
        temperature=0.0
    )
    # We expect a 1‐token response and no errors
    assert "choices" in resp and len(resp.choices) == 1
    text = resp.choices[0].message.content.strip()
    assert text, "Empty response from chat API"
