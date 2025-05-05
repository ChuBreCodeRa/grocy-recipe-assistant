# Ingredient Handling Strategy

This document details the ingredient handling approach in the Grocy Recipe Assistant, particularly focusing on preserving original ingredient names and improving matching algorithms.

## Overview

The Grocy Recipe Assistant handles ingredients with precision, preserving original names while still enabling effective recipe matching. This document explains the key strategies and implementation details.

## Core Principles

1. **Preserve Original Names**: Maintain the exact names from Grocy inventory rather than generalizing them
2. **Intelligent Matching**: Use multiple strategies to match recipe ingredients to inventory items
3. **Culinary-Aware Grouping**: Group ingredients based on real culinary principles
4. **AI Fallback**: Generate custom recipes when standard matching fails

## Implementation Details

### 1. Original Name Preservation

The system preserves exact ingredient names throughout the process:

- **AI Filtering Prompt**: Modified to explicitly keep original names:
  ```
  Return the EXACT original names of food items without generalizing them
  ```
- **No Generalization**: Only filters out non-food items, never changes food item names
- **Handling Size Information**: Quantities like "20oz" are preserved but ignored for matching purposes

This approach maintains complete fidelity to your Grocy inventory entries, including meal kits, prepared foods, and brand-specific items.

### 2. Multi-Strategy Ingredient Matching

When matching recipe ingredients to inventory items, the system uses multiple approaches:

1. **Exact Matching**: Direct string comparison between recipe ingredients and inventory items
2. **Substring Matching**: Checking if recipe ingredient appears within inventory item or vice versa
3. **Core Ingredient Matching**: Using a knowledge base of core ingredients to match related terms
4. **Simplified Name Matching**: Creating "simplified" versions of inventory items by removing packaging terms

This multi-layered approach significantly improves matches for prepared foods and meal kits.

### 3. Culinary-Aware Ingredient Grouping

When creating ingredient combinations for recipe search:

- **Meal Structure Knowledge**: Uses understanding of classic meal structures (protein + starch + vegetable)
- **Cuisine-Based Combinations**: Groups ingredients that typically appear together in specific cuisines
- **Prepared Food Handling**: Special logic for meal kits to add appropriate complementary ingredients
- **AI Assistance**: Optional AI guidance for even more sophisticated combinations

This results in more logical ingredient groupings and better recipe matches.

### 4. AI Recipe Generation Fallback

When Spoonacular can't find suitable recipes:

- **Custom Recipe Creation**: Generates recipes specifically using available ingredients
- **JSON Formatting**: Returns recipe in same format as Spoonacular for consistent handling
- **Specialized Logic**: Focuses especially on meal kits and prepared foods that may not be in standard databases
- **Fallback Trigger**: Activates when recipes have very low fit scores (10% or less)

## Development Guidelines

When modifying ingredient handling:

1. Always run tests with real-world meal kits and prepared foods
2. Preserve the original name preservation approach
3. Consider adding new matching strategies rather than modifying existing ones
4. When in doubt, err on the side of exact matching over fuzzy matching

## Related Documents

- [[DECISIONS]] - See "Ingredient Naming Strategy" and "Recipe Fallback Strategy"
- [[SYSTEM_OVERVIEW]] - Review "Recipe Service" section
- [[README]] - Features related to ingredient handling