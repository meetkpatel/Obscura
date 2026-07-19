from server.constants import (
    HOSTED_DEMO_LLM_BASE_URL,
    HOSTED_DEMO_LLM_MODEL,
    HOSTED_DEMO_WHISPER_BASE_URL,
    HOSTED_DEMO_WHISPER_MODEL,
)
from server.database.config.defaults.templates import DefaultTemplates
from server.schemas.config import Config
from server.utils.llama_models import PRECONFIGURED_MODELS


def test_medgemma_is_a_first_class_local_model():
    model = PRECONFIGURED_MODELS["medgemma-4b"]

    assert model["repo_id"] == "unsloth/medgemma-4b-it-GGUF"
    assert model["filename"] == "medgemma-4b-it-Q4_K_M.gguf"
    assert model["recommended_ram_gb"] <= 8
    assert model["recommended_type"] == "recommended"


def test_soap_prompts_are_grounded_and_do_not_require_content():
    soap_template = next(
        template
        for template in DefaultTemplates.get_default_templates()
        if template["template_key"] == "soap_01"
    )

    prompts = {
        field["field_key"]: field["system_prompt"] for field in soap_template["fields"]
    }

    assert set(prompts) == {"subjective", "objective", "assessment", "plan"}
    for prompt in prompts.values():
        normalized = prompt.lower()
        assert "only information explicitly stated" in normalized
        assert "do not infer or invent" in normalized
        assert "not discussed" in normalized

    assert "minimum number" in prompts["plan"].lower()
    assert "at least 2 actions" not in prompts["plan"].lower()


def test_hosted_demo_defaults_use_gemma_and_whisper_without_storing_keys():
    config = Config()

    assert config.LLM_PROVIDER == "openai"
    assert config.LLM_BASE_URL == HOSTED_DEMO_LLM_BASE_URL
    assert config.PRIMARY_MODEL == HOSTED_DEMO_LLM_MODEL
    assert config.LLM_API_KEY == ""
    assert config.WHISPER_BASE_URL == HOSTED_DEMO_WHISPER_BASE_URL
    assert config.WHISPER_MODEL == HOSTED_DEMO_WHISPER_MODEL
    assert config.WHISPER_KEY == ""
