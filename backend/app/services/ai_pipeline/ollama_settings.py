# Task 3: Right-size the model(s)

AGENT_MODEL_MAP = {
    "mcq_engine": "llama3.2",        # 3B parameter model for complex generation
    "document_agent": "llama3.2:1b", # 1B parameter for fast/simple text tasks
    "concept_agent": "llama3.2:1b",
    "curriculum_agent": "llama3.2:1b",
    "competency_agent": "llama3.2:1b"
}
