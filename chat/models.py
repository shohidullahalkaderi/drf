from django.db import models

class Message(models.Model):
    sender_id = models.IntegerField()
    auth_id = models.IntegerField(default=0)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"User {self.sender_id} (Auth {self.auth_id}): {self.message[:30]}"