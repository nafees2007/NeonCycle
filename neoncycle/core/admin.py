from django.contrib import admin
from .models import UserProfile, GarbagePrice, CollectionOrder, RecyclerDemand, RecycledProduct

admin.site.register(UserProfile)
admin.site.register(GarbagePrice)
admin.site.register(CollectionOrder)
admin.site.register(RecyclerDemand)
admin.site.register(RecycledProduct)