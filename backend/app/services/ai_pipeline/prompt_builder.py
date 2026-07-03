from typing import Any


def build_prompt(
    system_prompt: str,
    context_chunks: list[dict[str, Any]],
    task_instruction: str,
) -> tuple[str, str]:
    context_parts: list[str] = []
    for i, chunk in enumerate(context_chunks):
        source_info = f"Source chunk {i + 1}"
        if chunk.get("chapter_title"):
            source_info += f" (Chapter: {chunk['chapter_title']})"
        if chunk.get("topic_title"):
            source_info += f" (Topic: {chunk['topic_title']})"
        context_parts.append(f"{source_info}:\n{chunk['text']}")

    context_str = "\n\n---\n\n".join(context_parts)
    prompt = f"Context:\n\n{context_str}\n\n---\n\n{task_instruction}"

    return system_prompt, prompt
