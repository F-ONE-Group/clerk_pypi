from typing import Dict, Union, List, Optional, Tuple, Any, Type, Literal
from pydantic import BaseModel, Field

from ..client_actor.client_actor import get_screen
from .models import (
    States,
    BaseState,
    ExpectedState,
    TargetWithAnchor,
    Answer,
    ActionString,
)
from f_one_core_utilities.ocr import get_ocr, OCRConfig

import re
import json
import os
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
from ...llm.models.message import UserMessage, SystemMessage, Message
from ...llm.types import HostType


class Vision(BaseModel):
    """
    Provides methods for interacting with a GUI for UI automation purposes. This class includes methods for finding
    targets on the screen, verifying the GUI's state, answering questions about the screen, classifying the state of
    the GUI, and generating action strings based on prompts.

    Attributes:
        HOST: Specifies the host for the API calls, defaulting to "azure".
        GPT_MODEL: The model type used for processing, defaulting to "".
        MAX_TOKENS: The maximum number of tokens to use in the API call, set to 2000.
        response_models: A dictionary mapping task names to their corresponding response model classes.
        use_ocr: A boolean indicating whether OCR should be included in the model call to increase precision with small details.
        image_resolution: A parameter defining the resolution of the image used in the vision model.

    Methods:
        find_target(target_prompt: str, output_model: Type[TargetWithAnchor] = TargetWithAnchor) -> TargetWithAnchor:
            Finds a target in the current screen based on the provided prompt. Limited to one-word targets.

        verify_state(possible_states: States, output_model: Type[BaseState] = BaseState) -> BaseState:
            Verifies the current state of the GUI against a set of possible states.

        answer(question: str, output_model: Type[BaseModel] = Answer) -> Answer:
            Answers a question about the current screen using the specified model for the response.

        classify_state(possible_states: List[Dict[str, str]], output_model: Type[BaseState] = BaseState) -> Union[BaseModel, Tuple[str, str]]:
            Classifies the current state of the GUI into one of the provided possible states. Returns either a model instance or a tuple of the ID and description.

        write_action_string(action_prompt: str, output_model: Type[ActionString] = ActionString) -> ActionString:
            Generates an action string based on the provided prompt.

    Note: Each method that interacts with the screen can optionally include OCR data to improve accuracy, controlled by the `use_ocr` attribute.
    """

    HOST: HostType = "azure"
    GPT_MODEL: str = ""
    MAX_TOKENS: int = 2000
    response_models: Dict[str, Type[BaseModel]] = {
        "find_target": TargetWithAnchor,
        "answer": Answer,
        "verify_state": BaseState,
        "classify_state": BaseState,
        "write_action_string": ActionString,
    }
    use_ocr: bool = Field(
        default=False,
        description="Whether OCR of the screen should be included with in the model call (increases precision with "
        "small details).",
    )
    image_resolution: Literal["high", "low"] = "high"

    class Config:
        arbitrary_types_allowed = True

    def _format_user_screen_message(
        self,
        screen_b64: str,
        screen_ocr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Formats a message for user screen display, including an optional OCR text.
        Args:
            screen_b64: Base64-encoded string of the screen image.
            screen_ocr: Optional OCR text extracted from the screen.
        Returns:
            A dictionary representing the formatted user message.
        """
        user_message: UserMessage = UserMessage(
            content=[
                Content(type="text", text="Here is the observed screen:").to_dict(),
                Content(
                    type="image_url",
                    image_url={
                        "url": f"data:image/x-png;base64,{screen_b64}",
                        "detail": self.image_resolution,
                    },
                ).to_dict(),
            ]
        )
        if screen_ocr is not None:
            user_message.content.append(
                Content(type="text", text=f"OCR of the screen: {screen_ocr}").to_dict()
            )
        return user_message.dict()

    @staticmethod
    def _format_user_request_message(user_request: str) -> Dict[str, Any]:
        """
        Formats a user request message.
        Args:
            user_request: The user's request as a string.
        Returns:
            A dictionary representing the formatted request message.
        """
        return UserMessage(
            content=[Content(type="text", text=user_request).to_dict()]
        ).dict()

    def _format_state_message_screen(
        self,
        state_type: type[BaseState],
        possible_states: Dict,
    ) -> Dict[str, Any]:
        """
        Formats a message detailing a specific GUI state, including state description and screenshots.
        Args:
            state_type: The type of state being described.
            possible_states: A dictionary of possible states.
        Returns:
            A dictionary representing the formatted state message.
        """
        state = possible_states.get(state_type)
        if state is None:
            raise ValueError("state is not found in possible states")
        # Add state name and description
        user_message_text = (
            f"Possible state: '{state.name}', description: {state.description}"
        )
        user_message: UserMessage = UserMessage(
            content=[
                Content(type="text", text=user_message_text).to_dict(),
            ]
        )

        # Add screenshots
        for screenshot_url in state.get_screenshots_urls():
            user_message.content.append(Content(type="text", text="Example:").to_dict())
            user_message.content.append(
                Content(
                    type="image_url",
                    image_url={"url": screenshot_url, "detail": self.image_resolution},
                ).to_dict()
            )
        return user_message.dict()

    @staticmethod
    def _format_state_message_text(
        possible_states: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Formats a message listing possible GUI states.
        Args:
            possible_states: A list of dictionaries, each representing a possible GUI state.
        Returns:
            A dictionary representing the formatted states message.
        """
        return UserMessage(
            content=[
                Content(
                    type="text", text=f"Possible states: {possible_states}"
                ).to_dict(),
            ]
        ).dict()

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
        max_time=60,
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
        task: str,
        user_request: Optional[str] = None,
        possible_states_screen: Optional[States] = None,
        possible_states_text: Optional[List[Dict[str, str]]] = None,
        screen_text: Optional[str] = None,
        output_model: Optional[Type[BaseModel]] = None,
    ) -> BaseModel:
        """
        Sends a request to the OpenAI API, formatting the input and handling the response.
        Args:
            screen_b64: Base64-encoded string of the screen image.
            task: The task identifier for the request.
            user_request: Optional specific user request.
            possible_states_screen: Optional screen states for more detailed requests.
            possible_states_text: Optional text description of possible states.
            screen_text: Optional OCR text from the screen.
            output_model: The model type for the expected response.
        Returns:
            An instance of the specified output model containing the response.
        """
        # add known (default) states and instructions
        messages: List = self._format_system_message(task, output_model)
        # add observed state to messages
        if possible_states_text:
            messages.append(self._format_state_message_text(possible_states_text))
        messages.append(self._format_user_screen_message(screen_b64, screen_text))
        if user_request:
            messages.append(self._format_user_request_message(user_request))
        if possible_states_screen:
            for state in possible_states_screen.possible_states.keys():
                messages.append(
                    self._format_state_message_screen(
                        state, possible_states_screen.possible_states
                    )
                )
        # call OpenAI API
        try:
            # pick the right output model for parsing
            if output_model is not None:
                response_model = output_model
            else:
                response_model = self.response_models[task]
            return self._try_openai_call(messages, response_model)
        except Exception as e:
            print(str(e))
            raise e

    @staticmethod
    def _format_system_message(
        task: str, output_model: Optional[Type[BaseModel]] = None
    ) -> List[Message]:
        """
        Formats a system message based on the specified task.
        Args:
            task: The task identifier.
        Returns:
            A list of messages formatted for the system.
        """
        # add system message
        base_dir = os.path.join(os.path.dirname(__file__), "prompts", task)
        with open(os.path.join(base_dir, "system_prompt.txt"), "r") as f:
            system_prompt = f.read()
        if (
            output_model is not None
            and output_model not in Vision().response_models.values()
        ):
            # Create example from custom output model
            example = json.dumps(output_model().dict(), indent=2)
            feedback_memory = ""
        else:
            # Use default example from file
            with open(os.path.join(base_dir, "example.json"), "r") as f:
                example = json.dumps(json.load(f), indent=2)
            with open(os.path.join(base_dir, "feedback_memory.txt"), "r") as f:
                feedback_memory = f.read()
        formatted_system_prompt = (
            system_prompt.format(feedback=feedback_memory, example=example)
            .replace("{{", "{")
            .replace("}}", "}")
        )
        messages: List[Message] = []
        system_message = SystemMessage(
            content=[
                Content(type="text", text=formatted_system_prompt).to_dict(),
            ]
        )
        messages.append(system_message)
        return messages

    @staticmethod
    def _sort_into_state_class(
        model_response: BaseState, possible_states: States
    ) -> BaseState:
        """
        Sorts a model response into a corresponding state class.
        Args:
            model_response: The response from the model.
            possible_states: A collection of possible states.
        Returns:
            A state class matching the model response.
        """
        for state_class, state_object in possible_states.possible_states.items():
            if model_response.id == state_object.id:
                return state_class(description=model_response.description)
        # return expected by default
        return ExpectedState(description=model_response.description)

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

    def find_target(
        self,
        target_prompt: str,
        output_model: Type[TargetWithAnchor] = TargetWithAnchor,
    ) -> TargetWithAnchor:
        """
        Finds a target in the current screen. Currently limited to one word targets.
        Args:
            target_prompt: The prompt for the target to find.
            output_model: The model to use for the response. If not provided, the default model for the task will be used.
        Returns:
            TargetWithAnchor object with the response from the model. Access the target with the "target" attribute.
        """
        screen_b64, screen_text = self._get_screen(self.use_ocr)
        target: BaseModel = self._send_openai_request(
            screen_b64,
            task="find_target",
            user_request=target_prompt,
            screen_text=screen_text,
            output_model=output_model,
        )
        if isinstance(target, TargetWithAnchor):
            return target
        raise NotImplementedError("works with `TargetWithAnchor` only")

    def verify_state(
        self, possible_states: States, output_model: Type[BaseState] = BaseState
    ) -> BaseState:
        """
        Verifies the current state of the GUI.
        Args:
            possible_states: The possible states of the GUI (State class incl. screen examples).
            output_model: The model to use for the response. If not provided, the default model for the task will be used.
        Returns:
            The current state of the GUI (BaseState or a subclass of BaseState)
        """
        screen_b64, screen_text = self._get_screen(self.use_ocr)
        state: BaseModel = self._send_openai_request(
            screen_b64,
            task="verify_state",
            possible_states_screen=possible_states,
            screen_text=screen_text,
            output_model=output_model,
        )
        if isinstance(state, BaseState):
            sorted_state = self._sort_into_state_class(state, possible_states)
            return sorted_state
        raise NotImplementedError("works with `BaseState` only")

    def answer(
        self, question: str, output_model: Type[BaseModel] = Answer
    ) -> BaseModel:
        """
        Answers a question about the current screen.
        Args:
            question: The question to ask about the current screen.
            output_model: The model to use for the response. If not provided, the default model for the task will be used.
        Returns:
            Answer object with the response from the model. Access the text with the "answer" attribute.
        """
        screen_b64, screen_text = self._get_screen(self.use_ocr)
        answer: BaseModel = self._send_openai_request(
            screen_b64,
            task="answer",
            user_request=question,
            screen_text=screen_text,
            output_model=output_model,
        )
        return answer

    def classify_state(
        self,
        possible_states: List[Dict[str, str]],
        output_model: Type[BaseState] = BaseState,
    ) -> Union[BaseModel, Tuple[str, str]]:
        """
        Classify the current state of the GUI into one of the provided classes.
        Args:
            possible_states: The possible states of the GUI.
            output_model: The model to use for the response.
        Returns:
            The current state of the GUI (BaseState class if an output model was provided; access class key with the "id" attribute), otherwise Tuple of the id and description of the default model.
        """
        screen_b64, screen_text = self._get_screen(self.use_ocr)
        state: BaseModel = self._send_openai_request(
            screen_b64,
            task="classify_state",
            possible_states_text=possible_states,
            screen_text=screen_text,
            output_model=output_model,
        )

        # if output_model is provided, return the model, otherwise return the id and description of the default model
        if output_model is not None:
            return state
        elif isinstance(state, BaseState):
            return state.id, state.description
        raise NotImplementedError  # if state is Answer or TargetWithAnchor, because they don't have neither `id` nor
        # `description`

    def write_action_string(
        self, action_prompt: str, output_model: Type[ActionString] = ActionString
    ) -> ActionString:
        """
        Writes an action string based on the provided prompt.
        Args:
            action_prompt: The prompt for the action to write.
            output_model: The model to use for the response.
        Returns:
            The action string.
        """
        screen_b64, screen_text = self._get_screen(self.use_ocr)
        action_string: BaseModel = self._send_openai_request(
            screen_b64,
            task="write_action_string",
            user_request=action_prompt,
            screen_text=screen_text,
            output_model=output_model,
        )
        if isinstance(action_string, ActionString):
            return action_string
        raise NotImplementedError("works with `ActionString` only")
