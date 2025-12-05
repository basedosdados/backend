# -*- coding: utf-8 -*-
import os
import time
import uuid

from dotenv import load_dotenv
from locust import HttpUser, between, task
from loguru import logger

load_dotenv()


class RegularUser(HttpUser):
    weight = 5
    wait_time = between(1, 5)

    @task
    def search(self):
        self.client.get("/search")


class ChatbotUser(HttpUser):
    weight = 1
    wait_time = between(10, 30)
    access_token = None

    def on_start(self):
        response = self.client.post(
            url="/chatbot/token/",
            data={
                "email": os.getenv("CHATBOT_USER_EMAIL"),
                "password": os.getenv("CHATBOT_USER_PASSWORD"),
            },
        )

        response.raise_for_status()

        access_token = response.json().get("access")

        self.access_token = access_token

    @task
    def start_thread(self):
        if not self.access_token:
            logger.warning("[START_THREAD] Access token is None")

        response = self.client.post(
            url="/chatbot/threads/",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={"title": "Mockup Title"},
        )

        response.raise_for_status()

        thread_data: dict = response.json()
        thread_id = thread_data.get("id")

        if thread_id is None:
            logger.warning("[START_THREAD] Thread ID is None")

        message = "Qual a proporção de mulheres no mercador de trabalho formal?"

        start_time = time.perf_counter()

        try:
            # Note: Locust reports TTFB (time to first byte) on streaming
            response = self.client.post(
                url=f"/chatbot/threads/{thread_id}/messages/",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"id": str(uuid.uuid4()), "content": message},
                stream=True,
                timeout=60,
                name="TTFB",
            )

            response.raise_for_status()

            chunks = 0
            for line in response.iter_lines():
                if line:
                    chunks += 1

            # Calculate TTLB (time to last byte) to log it
            ttlb_ms = int((time.perf_counter() - start_time) * 1000)

            logger.success(
                f"[START_THREAD] TTFC: {response.elapsed.total_seconds():.2f}s | "
                f"TTLB: {ttlb_ms/1000:.2f}s | "
                f"Chunks: {chunks}"
            )
        except Exception:
            logger.exception("[START_THREAD] Unexpected error:")
