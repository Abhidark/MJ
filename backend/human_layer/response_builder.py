from human_layer.conversation_modes import MODE_STYLE


class ResponseBuilder:
    def build_response_prompt(
        self,
        user_text: str,
        intent: str,
        emotion: str,
        memory_context: str = ""
    ) -> str:
        mode = MODE_STYLE.get(intent, MODE_STYLE["casual"])

        prompt = f"[Context: intent={intent}, emotion={emotion}, tone={mode['tone']}, length={mode['max_length']}]"

        if memory_context:
            prompt += f"\n[Memory: {memory_context}]"

        prompt += f"\n\n{user_text}"

        return prompt
