from django.db import models

class Indexed(models.Model):
    url = models.URLField(max_length=255)
    desc = models.CharField(max_length=255)
    keywds = models.TextField()
    title = models.CharField(max_length=255, null=True)
    rank = models.IntegerField()
    content = models.TextField()
    favicon = models.URLField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "indexed pages"
    
    def __str__(self):
        return f"{self.title} ({self.url})"