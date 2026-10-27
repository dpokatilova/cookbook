from django.contrib import admin

from recipes.models import Category, Ingredient, Recipe, RecipeIngredient

admin.site.register(Category)
admin.site.register(Ingredient)
admin.site.register(Recipe)
admin.site.register(RecipeIngredient)
