import random
from locust import HttpUser, task, between

QUESTIONS = [
    "What is Docker and how does it help with containerization?",
    "What is Kubernetes?",
    "Explain Infrastructure as Code.",
    "What is continuous integration?",
    "How does Terraform work?",
]


class RAGUser(HttpUser):
    wait_time = between(3, 8)

    def on_start(self):
        print("Locust user started — ready to send RAG request")

    @task
    def ask_question(self):
        question = random.choice(QUESTIONS)

        with self.client.post(
            "/api/v1/query",
            json={"question": question},
            name="/api/v1/query",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Request failed: HTTP {response.status_code}")
                return

            try:
                result = response.json()
                if not result.get("answer"):
                    response.failure("Empty answer returned")
                    return

                response.success()

            except ValueError:
                response.failure("Invalid JSON response")