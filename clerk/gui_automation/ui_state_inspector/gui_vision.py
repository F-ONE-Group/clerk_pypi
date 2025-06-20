from typing import Dict, Union, List, Tuple, Type, Literal
from pydantic import BaseModel, Field

from clerk.gui_automation.client import GUIVisionClerk

from ..client_actor.client_actor import get_screen
from .models import (
    States,
    BaseState,
    ExpectedState,
    TargetWithAnchor,
    Answer,
    ActionString,
)


class Vision(BaseModel):
    """
    Provides methods for interacting with a GUI for UI automation purposes. This class includes methods for finding
    targets on the screen, verifying the GUI's state, answering questions about the screen, classifying the state of
    the GUI, and generating action strings based on prompts.

    Attributes:
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
    clerk_client: GUIVisionClerk = GUIVisionClerk()

    class Config:
        arbitrary_types_allowed = True

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
        screen_b64 = get_screen()

        target = self.clerk_client.find_target(
            screen_b64,
            self.use_ocr,
            target_prompt,
        )
        assert isinstance(target, output_model)
        return target

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
        screen_b64 = get_screen()
        state = self.verify_state(
            screen_b64,
            self.use_ocr,
            possible_states,
        )
        assert isinstance(state, BaseState)
        sorted_state = self._sort_into_state_class(state, possible_states)
        return sorted_state

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
        screen_b64 = get_screen()
        answer = self.clerk_client.answer(
            screen_b64, self.use_ocr, question, output_model
        )
        assert isinstance(answer, output_model)
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
        screen_b64 = get_screen()
        state = self.clerk_client.classify_state(
            screen_b64, self.use_ocr, possible_states
        )
        # if output_model is provided, return the model, otherwise return the id and description of the default model
        if output_model is not None:
            return state
        assert isinstance(state, BaseState)
        return state.id, state.description

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
        screen_b64 = get_screen()
        action_string = self.clerk_client.write_action_string(
            screen_b64, self.use_ocr, action_prompt
        )
        assert isinstance(action_string, ActionString)
        return action_string
