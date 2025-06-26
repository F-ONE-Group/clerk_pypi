from typing import Union, List, Optional, Type
from pydantic import BaseModel, Field

from clerk.gui_automation.client import CourseCorrectorClerk

from ..client_actor.client_actor import get_screen
from .models import ActionString


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
    use_ocr: bool = Field(
        default=True,
        description="Whether OCR of the screen should be included with in the model call (increases precision with "
        "small details).",
    )
    clerk_client: CourseCorrectorClerk = CourseCorrectorClerk()

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
        screen_b64 = get_screen()
        action_string = self.clerk_client.get_corrective_actions(
            screen_b64, self.use_ocr, self.goal, self.custom_instructions
        )
        assert isinstance(action_string, ActionString)
        return [action_string]

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
