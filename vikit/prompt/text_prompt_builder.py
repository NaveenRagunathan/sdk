from vikit.prompt.text_prompt import TextPrompt


class TextPromptBuilder:
    """
    Builds a text prompt

    Most functions are used by a prompt builder, as the way to generate a prompt may vary and get a bit complex
    """

    def __init__(self):
        super().__init__()
        self.prompt = TextPrompt()

    def set_prompt_text(self, text: str):
        if text is None:
            raise ValueError("The text prompt is not provided")
        self.prompt.text = text
        return self

    def build(self):
        return self.prompt
