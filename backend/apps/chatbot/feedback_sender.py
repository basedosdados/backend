# -*- coding: utf-8 -*-
from queue import Full, Queue
from threading import Thread

import langsmith
from django.utils import timezone
from loguru import logger

from backend.apps.chatbot.models import Feedback


class LangSmithFeedbackSender:
    """A feedback sender that sends feedback to LangSmith using a background worker."""

    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        self._langsmith_client = langsmith.Client(api_url=api_url, api_key=api_key)

        self._queue: Queue[tuple[Feedback, bool]] = Queue(maxsize=1000)

        self._thread = Thread(target=self._process_feedback, daemon=True)
        self._thread.start()

    def _create_langsmith_feedback(self, feedback: Feedback) -> bool:
        """Create feedback on LangSmith.

        Args:
            feedback (Feedback): The feedback instance to create.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            _ = self._langsmith_client.create_feedback(
                run_id=feedback.message_pair.id,
                key="helpfulness",
                feedback_id=feedback.id,
                score=feedback.rating,
                comment=feedback.comment,
            )
            logger.info(
                f"Successfully created feedback {feedback.id} "
                f"for run {feedback.message_pair.id} on LangSmith"
            )
            return True
        except Exception:
            logger.exception(
                f"Failed to create feedback {feedback.id} "
                f"for run {feedback.message_pair.id} on LangSmith"
            )
            return False

    def _update_langsmith_feedback(self, feedback: Feedback) -> bool:
        """Update existing feedback on LangSmith.

        Args:
            feedback (Feedback): The feedback instance to update.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self._langsmith_client.update_feedback(
                feedback_id=feedback.id, score=feedback.rating, comment=feedback.comment
            )
            logger.info(
                f"Successfully updated feedback {feedback.id} "
                f"for run {feedback.message_pair.id} on LangSmith"
            )
            return True
        except Exception:
            logger.exception(
                f"Failed to update feedback {feedback.id} "
                f"for run {feedback.message_pair.id} on LangSmith"
            )
            return False

    def _process_feedback(self):
        """Background worker that continuously processes feedbacks from the queue.
        Updates the feedback sync status in the local database after each operation.
        """
        while True:
            feedback, created = self._queue.get()

            if created:
                success = self._create_langsmith_feedback(feedback)
            else:
                success = self._update_langsmith_feedback(feedback)

            feedback.sync_status = "success" if success else "failed"
            feedback.synced_at = timezone.now()
            feedback.save()

            self._queue.task_done()

    def send_feedback(self, feedback: Feedback, created: bool):
        """Enqueue a feedback instance for creation or update on LangSmith.

        Args:
            feedback (Feedback): The feedback instance to send.
            created (bool): True if this is a new feedback, False if it's an update.
        """
        try:
            self._queue.put(
                item=(feedback, created),
                timeout=10,
            )
        except Full:
            operation = "create" if created else "update"
            logger.warning(
                f"LangSmith feedbacks queue is full - could not {operation} "
                f"feedback {feedback.id} on LangSmith"
            )
