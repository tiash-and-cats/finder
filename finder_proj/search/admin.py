from django.contrib import admin
from .models import CommonSearch

# Register your models here.
class CommonSearchAdmin(admin.ModelAdmin):
    list_display = ("phrase", "count",)
    search_fields = ['phrase',]
    
    def get_ordering(self, request):
        return ['-count',]  # Sort by count descending

admin.site.register(CommonSearch, CommonSearchAdmin)