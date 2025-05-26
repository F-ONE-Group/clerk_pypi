from typing import Union, List, Optional, Tuple, Type, Literal
from pydantic import BaseModel, Field

from ..client_actor.client_actor import get_screen
from .models import ActionString
from f_one_core_utilities.ocr import get_ocr, OCRConfig

import json
import base64
import tempfile
from io import BytesIO
import backoff

from ... import MissingEnvironmentVariable
from ...llm import llm_call
from ...llm.exceptions.api import (
    NetworkError,
    InvalidJSONResponseError,
    ResponseValidationError,
    UnexpectedError,
)
from ...llm.llm import T
from ...llm.models.content import Content
from ...llm.models.message import UserMessage, SystemMessage, AiMessage, Message
from ...llm.types import HostType

from .ai_recovery_prompts import (
    SYSTEM_PROMPT,
    FEEDBACK_MEMORY,
    EXAMPLE,
    CUSTOM_INSTRUCTIONS_TEMPLATE,
)


class CourseCorrector(BaseModel):
    """
    Interface for a CourseCorrector class that can generate corrective actions based on a goal and feedback.
    """

    name: str
    goal: str
    custom_instructions: Optional[str] = None

    def get_corrective_actions(
        self, output_model: Type[ActionString] = ActionString
    ) -> List[ActionString]:
        """
        Writes an action string based on the provided prompt.
        Args:
            action_prompt: The prompt for the action to write.
            output_model: The model to use for the response.
        Returns:
            List of ActionString models.
        """
        raise NotImplementedError("get_corrective_action method is not implemented")

    def add_feedback(self, feedback: str) -> None:
        """
        Adds feedback to the CourseCorrector instance.
        Args:
            feedback: The feedback to add.
        """
        raise NotImplementedError("add_feedback method is not implemented")

    def get_latest_feedback(self) -> Optional[str]:
        """
        Gets the latest feedback added to the CourseCorrector instance.
        Returns:
            The latest feedback as a string, or None if no feedback has been added.
        """
        raise NotImplementedError("get_latest_feedback method is not implemented")

    def reset_feedback(self) -> None:
        """
        Resets the latest feedback added to the CourseCorrector instance.
        """
        raise NotImplementedError("reset_feedback method is not implemented")


class CourseCorrectorV1(CourseCorrector):
    name: str = "CourseCorrectorV1"
    goal: str
    HOST: HostType = "azure"
    GPT_MODEL: str = "gpt-4-vision-preview"
    MAX_TOKENS: int = 2000
    use_ocr: bool = Field(
        default=True,
        description="Whether OCR of the screen should be included with in the model call (increases precision with "
        "small details).",
    )
    messages: List[Message] = []
    image_resolution: Literal["high", "low"] = "low"
    latest_feedback: Optional[str] = None

    def _format_system_message(self, task: str) -> SystemMessage:
        """
        Formats a system message based on the specified task.
        Args:
            task: The task identifier.
        Returns:
            SystemMessage object.
        """
        # add system message
        system_prompt = SYSTEM_PROMPT
        example = json.dumps(EXAMPLE, indent=2)
        feedback_memory = FEEDBACK_MEMORY
        formatted_system_prompt = (
            system_prompt.format(feedback=feedback_memory, example=example)
            .replace("{{", "{")
            .replace("}}", "}")
        )
        system_message = SystemMessage(
            content=[
                Content(type="text", text=formatted_system_prompt).to_dict(),
            ]
        )
        return system_message

    @staticmethod
    def _format_custom_instructions(instructions: str) -> SystemMessage:
        """
        Formats a system message based on the specified custom instructions.
        Args:
            instructions: The custom instructions to include in the message.
        Returns:
            SystemMessage object.
        """
        prompt = CUSTOM_INSTRUCTIONS_TEMPLATE.format(instructions=instructions)
        custom_instructions_system_message = SystemMessage(
            content=[Content(type="text", text=prompt).to_dict()]
        )
        return custom_instructions_system_message

    @staticmethod
    def _format_user_screen_message(
        screen_b64: str,
        screen_ocr: Optional[str] = None,
        image_resolution: Literal["high", "low"] = "low",
    ) -> Message:
        """
        Formats a message for user screen display, including an optional OCR text.
        Args:
            screen_b64: Base64-encoded string of the screen image.
            screen_ocr: Optional OCR text extracted from the screen.
        Returns:
            A Message representing the formatted user message.
        """
        user_message: UserMessage = UserMessage(
            content=[
                Content(type="text", text="Here is the observed screen:").to_dict(),
                Content(
                    type="image_url",
                    image_url={
                        "url": f"data:image/x-png;base64,{screen_b64}",
                        "detail": image_resolution,
                    },
                ).to_dict(),
            ]
        )
        if screen_ocr is not None:
            user_message.content.append(
                Content(type="text", text=f"OCR of the screen: {screen_ocr}").to_dict()
            )
        return user_message

    @staticmethod
    def _format_user_message(message: str) -> Message:
        """
        Formats a user request message.
        Args:
            user_request: The user's request as a string.
        Returns:
            A Message representing the formatted request message.
        """
        return UserMessage(content=[Content(type="text", text=message).to_dict()])

    @staticmethod
    def _format_ai_response_as_message(response: BaseModel) -> Message:
        """
        Formats the AI response as a message.
        Args:
            response: The AI response to format.
        Returns:
            A message containing the formatted AI response.
        """
        if not hasattr(response, "action_string"):
            raise AttributeError(
                f" [_format_ai_response_as_message] action_string attr is missing in response"
            )
        return AiMessage(
            content=[Content(type="text", text=response.action_string).to_dict()]
        )

    @backoff.on_exception(
        backoff.expo,
        (
            NetworkError,
            InvalidJSONResponseError,
            ResponseValidationError,
            UnexpectedError,
            NotImplementedError,
            MissingEnvironmentVariable,
        ),
        max_tries=3,
    )
    def _try_openai_call(self, messages: List[Message], output_type: Type[T]) -> T:
        """
        Attempts to call the OpenAI API with exponential backoff on failure.
        Args:
            messages: A list of messages to send in the API call.
            output_type: The expected type of the response model.
        Returns:
            An instance of the expected response model.
        Raises:
            NotImplementedError: If the response model is not supported.
        """
        response = llm_call(
            prepared_messages=messages,
            max_tokens=self.MAX_TOKENS,
            host=self.HOST,
            model_name=self.GPT_MODEL,
            output_type=output_type,
        )
        if isinstance(response, BaseModel):
            return response
        raise NotImplementedError(
            "`Vision` can only use the default response model and parse the output string"
        )

    def _send_openai_request(
        self,
        screen_b64: str,
        output_model: Type[BaseModel],
        task: str,
        screen_text: Optional[str] = None,
        image_resolution: Literal["high", "low"] = "low",
    ) -> BaseModel:
        """
        Sends a request to the OpenAI API, formatting the input and handling the response.
        Args:
            screen_b64: Base64-encoded string of the screen image.
            task: The task identifier for the request.
            screen_text: Optional OCR text from the screen.
            output_model: The model type for the expected response.
            image_resolution: The desired resolution for the screen images.
        Returns:
            An instance of the specified output model containing the response.
        """
        # Initialize messages for the first turn of the conversation
        if not self.messages:
            self.messages.append(self._format_system_message(task))
            self.messages.append(self._format_user_message(self.goal))
            if self.custom_instructions:
                self.messages.append(
                    self._format_custom_instructions(self.custom_instructions)
                )

        if self.latest_feedback:
            self.messages.append(self._format_user_message(self.latest_feedback))

        # Add current screen message
        self.messages.append(
            self._format_user_screen_message(screen_b64, screen_text, image_resolution)
        )

        # call OpenAI API
        response: BaseModel = self._try_openai_call(self.messages, output_model)
        self.messages.append(self._format_ai_response_as_message(response))
        return response

    @staticmethod
    def _get_screen_ocr(screen_b64: str) -> Union[str, None]:
        """
        Extracts OCR text from a screen image encoded in base64.
        Args:
            screen_b64: The base64-encoded screen image.
        Returns:
            The OCR text as a string, or None if OCR fails.
        """
        try:
            # Decode the base64 string
            screen_bytes = base64.b64decode(screen_b64)
            screen = BytesIO(screen_bytes)
            screen.seek(0)

            # Store the screen in a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(screen.read())
                tmp_file_path = tmp_file.name

            # Use the temporary file path for OCR
            screen_text: Union[str, List[str], None] = get_ocr(
                tmp_file_path, OCRConfig(ocr_engine="google_vision")
            )
        except Exception as e:
            print(f"Error in OCR: {str(e)}, proceeding without OCR")
            screen_text = None
        if isinstance(screen_text, list):
            raise NotImplementedError(
                "`self._send_openai_request` only accepts screen_text: Union[str, None]"
            )
        return screen_text

    def _get_screen(self, use_ocr: bool = False) -> Tuple[str, Union[str, None]]:
        """
        Gets the current screen and optionally the OCR of the screen.
        Args:
            use_ocr: Whether OCR of the screen should be included with in the model call (increases precision with small details).
        Returns:
            Tuple of the screen in base64 and the OCR of the screen (if use_ocr is True).
        """
        screen_b64 = get_screen()
        screen_text: Union[str, None]
        if use_ocr:
            screen_text = self._get_screen_ocr(screen_b64)
        else:
            screen_text = None
        return screen_b64, screen_text

    def get_corrective_actions(
        self,
        output_model: Type[ActionString] = ActionString,
    ) -> List[ActionString]:
        """
        Writes an action string based on the provided prompt.
        Args:
            action_prompt: The prompt for the action to write.
            output_model: The model to use for the response.
        Returns:
            List of ActionString models.
        """

        screen_b64, screen_text = self._get_screen(self.use_ocr)
        action_string: BaseModel = self._send_openai_request(
            screen_b64,
            task="course_corrector",
            screen_text=screen_text,
            output_model=output_model,
            image_resolution=self.image_resolution,
        )
        if isinstance(action_string, ActionString):
            return [action_string]
        raise NotImplementedError("works with `ActionString` only")

    def add_feedback(self, feedback: str) -> None:
        """
        Adds feedback to the CourseCorrector instance.
        Args:
            feedback: The feedback to add.
        """
        self.latest_feedback = feedback

    def get_latest_feedback(self) -> Optional[str]:
        """
        Gets the latest feedback added to the CourseCorrector instance.
        Returns:
            The latest feedback as a string, or None if no feedback has been added.
        """
        return self.latest_feedback

    def reset_feedback(self) -> None:
        """
        Resets the latest feedback added to the CourseCorrector instance.
        """
        self.latest_feedback = None


def course_corrector_v1(
    goal: str, custom_instructions: Union[str, None] = None
) -> CourseCorrectorV1:
    """Factory function for generating a CourseCorrector instance with the specified goal."""
    return CourseCorrectorV1(goal=goal, custom_instructions=custom_instructions)
