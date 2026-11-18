from django.urls import path

from recipes import views

urlpatterns = [
    path("recipes/", views.RecipeListView.as_view(), name="recipe-list"),
    path(
        "recipes/<int:pk>/",
        views.RecipeDetailView.as_view(),
        name="recipe-detail",
    ),
    path(
        "recipes/<int:pk>/ingredients/",
        views.RecipeIngredientListView.as_view(),
        name="recipe-ingredient-list",
    ),
    path(
        "recipes/<int:pk>/ingredients/<int:ingredient_pk>/",
        views.RecipeIngredientDetailView.as_view(),
        name="recipe-ingredient-detail",
    ),
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path(
        "categories/<int:pk>/",
        views.CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path(
        "ingredients/",
        views.IngredientListView.as_view(),
        name="ingredient-list",
    ),
    path(
        "ingredients/<int:pk>/",
        views.IngredientDetailView.as_view(),
        name="ingredient-detail",
    ),
]
