from locust import HttpUser, task, between


class ApiUser(HttpUser):
    wait_time = between(0.1, 1)

    @task
    def list_competitors(self):
        self.client.get("/api/v1/competitors", name="competitors")
