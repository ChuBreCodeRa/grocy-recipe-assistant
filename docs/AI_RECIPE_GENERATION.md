# AI Recipe Generation

This document details the AI Recipe Generation feature in the Grocy Recipe Assistant, which creates custom recipes when Spoonacular doesn't return suitable matches.

## Overview

The AI Recipe Generation feature is a fallback mechanism that ensures users always get relevant recipe suggestions, even when their available ingredients don't match well with recipes in the Spoonacular database. This is particularly valuable for meal kits, prepared foods, and uncommon ingredient combinations.

## When AI Recipes Are Generated

The system generates AI recipes in two scenarios:

1. **No Results**: When Spoonacular returns zero recipe matches for the available ingredients
2. **Low Fit Scores**: When the best recipe match from Spoonacular has a fit score of 10% or lower

## How It Works

### 1. Creation Process

The AI recipe generation follows these steps:

1. **Input Collection**: The system gathers:
   - Available ingredients from inventory
   - User dietary restrictions
   - Time constraints (if specified)

2. **Prompt Engineering**: A carefully structured prompt is sent to the OpenAI API requesting:
   - A recipe using only available ingredients (plus basic pantry items)
   - Conformance to dietary restrictions
   - Complete details (title, cooking time, ingredient amounts, instructions)
   - Proper JSON format matching Spoonacular's structure

3. **Processing Response**: The system:
   - Extracts the JSON recipe data
   - Handles potential JSON parsing errors with multiple fallback mechanisms
   - Adds necessary metadata for compatibility with the rest of the system

4. **Integration**: The AI-generated recipe is:
   - Scored with the same algorithm as Spoonacular recipes
   - Classified for ingredient importance
   - Typically placed at the top of recipe suggestions

### 2. Sample Prompt Structure

```
You are a creative chef. Create a recipe using only ingredients from this inventory list.
        
Available ingredients: [list of ingredients]

[Dietary instructions if present]
[Time constraint if present]

Your recipe must:
1. Only use ingredients from the available list (plus basic salt, pepper, water)
2. Include a title, cooking time, servings, ingredient list with amounts, and step-by-step instructions
3. Be practical and reasonable to make at home
4. Maximize the use of available ingredients

Return your recipe in this JSON format EXACTLY as shown...
```

### 3. Error Handling

The system includes robust error handling:

- **JSON Parsing Fixes**: Automatically corrects common JSON formatting issues
- **Manual Extraction**: If JSON can't be parsed, extracts key elements (title, instructions) directly
- **Last-Resort Fallback**: Creates a minimal valid recipe structure if all else fails
- **Detailed Logging**: Records specific JSON errors for debugging

## Advantages

1. **Guaranteed Suggestions**: Users always get relevant recipe options
2. **Higher Satisfaction**: Recipes are tailored to exactly what's in the user's inventory
3. **Better Handling of Specialized Items**: Works well with prepared foods, meal kits, and unique ingredients
4. **Consistent Experience**: Presents AI recipes in the same format as Spoonacular recipes

## Limitations

1. **No Images**: AI-generated recipes don't include food images
2. **Estimated Taste Profile**: Uses default values for taste attributes
3. **No External Links**: Cannot provide source website links
4. **Requires OpenAI API**: Doesn't work in offline mode or without API access

## Development Guidelines

When modifying the AI recipe generation feature:

1. Maintain the consistent recipe format for UI compatibility
2. Preserve the error handling mechanisms for JSON parsing
3. Consider enhancing the prompt with additional context when needed
4. Test with challenging ingredient combinations, especially prepared foods

## Related Documents

- [[DECISIONS]] - See "Recipe Fallback Strategy"
- [[SYSTEM_OVERVIEW]] - AI-Assisted Elements section
- [[PROMPTS]] - For detailed prompt engineering principles