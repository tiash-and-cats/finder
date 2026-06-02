from django.db import models

class CommonSearch(models.Model):
    phrase = models.CharField(max_length=200, unique=True)
    count = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name_plural = "common searches"

    def __str__(self):
        return self.phrase