from rest_framework import serializers

from recipes.models import Category, Ingredient, Recipe, RecipeIngredient


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name"]


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="ingredient.id", read_only=True)
    name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ["id", "name", "amount"]


class RecipeListSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(source="category.id", read_only=True)

    class Meta:
        model = Recipe
        fields = ["id", "title", "time_minutes", "calories", "category_id"]


class RecipeSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
    )

    class Meta:
        model = Recipe
        fields = [
            "id",
            "title",
            "description",
            "time_minutes",
            "calories",
            "category_id",
        ]

    def validate_time_minutes(self, value):
        if value == 0:
            raise serializers.ValidationError("Час приготування має бути більшим за 0.")
        return value


class RecipeDetailSerializer(RecipeSerializer):
    ingredients = RecipeIngredientSerializer(
        source="recipe_ingredients",
        many=True,
        read_only=True,
    )

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ["ingredients"]


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    ingredient_id = serializers.PrimaryKeyRelatedField(
        source="ingredient",
        queryset=Ingredient.objects.all(),
    )

    class Meta:
        model = RecipeIngredient
        fields = ["ingredient_id", "amount"]
