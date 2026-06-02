from django.contrib import admin
from api.models import Indexed

# Register your models here.
class IndexedAdmin(admin.ModelAdmin):
    list_display = ("title", "url", "desc",)
    search_fields = ['title', 'url', 'desc',]
    
    def get_ordering(self, request):
        return ['-rank',]  # Sort by rank descending

admin.site.register(Indexed, IndexedAdmin)