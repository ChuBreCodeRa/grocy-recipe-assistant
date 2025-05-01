# Use Cases

This document outlines common practical scenarios that demonstrate the Grocy AI Recipe Assistant's functionality.

## 1. Weeknight Dinner for a Busy Parent

**Scenario**: Alyssa gets home late and needs to make a quick dinner with what she has on hand.

**Flow**:
1. Alyssa asks: "Hey Google, what can I make for dinner tonight?"
2. Home Assistant sends a request to the Recipe Assistant's `/ai/suggest-recipes?max_ready_time=30` endpoint.
3. The system:
   - Retrieves current inventory from Grocy (canned goods, pasta, etc.)
   - Uses AI to filter out non-food items
   - Creates intelligent ingredient combinations based on cooking principles
   - Searches for recipes matching these meaningful combinations
   - Ranks results by "fit score" showing which recipes best match available ingredients
   - Returns 3 recipe options that can be made in under 30 minutes
4. Home Assistant responds: "You could make Quick Tuna Pasta with ingredients you have. You'll need pasta, canned tuna, and garlic which you already have. You're missing fresh parsley. Would you like the full recipe?"

**Key Features Utilized**:
- Inventory sync with Grocy
- AI filtering of inventory
- Intelligent ingredient combinations
- Recipe scoring with fit percentage
- Time constraint filtering

## 2. Weekend Cooking with More Effort

**Scenario**: Brendan has more time on weekends and enjoys more complex recipes.

**Flow**:
1. Brendan says: "Hey Google, suggest a weekend dinner recipe."
2. The system:
   - Recognizes Brendan's profile from the request
   - Uses his "moderate" to "hard" effort tolerance
   - Does not apply maxReadyTime restriction
   - Factors in his preference for stronger flavors based on past feedback
3. Home Assistant responds: "I recommend Homemade Pasta Carbonara. The preparation will take about 50 minutes, but you have all the ingredients and it matches your taste preferences."

## 3. Recipe Feedback Loop

**Scenario**: Alyssa tries a recipe and wants to provide feedback.

**Flow**:
1. After dinner, Alyssa says: "Hey Google, rate dinner 4 stars."
2. Home Assistant prompts: "What did you think of the Quick Chicken Stir Fry?"
3. Alyssa responds: "It was tasty but a bit too salty and took longer than expected."
4. The system:
   - Sends the feedback to the `/feedback/submit` endpoint
   - AI parses the review and extracts:
     - Effort perception: "moderate" (since it took longer than expected)
     - Key taste factors: "salty" is too high
     - Overall sentiment: "positive" (4 stars, "tasty")
   - Stores these structured insights in the `user_ratings` table
5. Overnight, the scheduled cron job updates Alyssa's preferences:
   - Slightly reduces the "saltiness" preference in her taste profile
   - Adjusts her effort tolerance to better reflect actual preparation times

## 4. Inventory-Aware Suggestions

**Scenario**: Brendan wants a recipe suggestion that uses the most items in his inventory.

**Flow**:
1. Brendan opens the mobile app and taps "What can I make?"
2. The app calls `/ai/suggest-recipes` with the `simplified=true` parameter to get a quick list view
3. The system:
   - Retrieves current inventory from Grocy 
   - Uses AI to filter out non-food items
   - Creates intelligent ingredient combinations (e.g., "pasta + tomato sauce + cheese" or "chicken + rice + garlic")
   - Searches for recipes that utilize these combinations
   - Sorts results by "fit score" (percentage of required ingredients already in inventory)
4. The app displays a list of recipes with clear fit scores
5. Brendan taps on "Pasta Primavera" which shows a 75% fit
6. The app calls `/ai/suggest-recipes/{recipe_id}` to get detailed information including:
   - A clear list of ingredients he already has
   - A minimal shopping list of what he needs to buy
   - Step-by-step cooking instructions

**Key Features Utilized**:
- Intelligent ingredient combinations
- Fit score calculation
- Simplified API response format for list views
- Detailed ingredients breakdown by availability

## 5. Administrative Override

**Scenario**: Testing recipes with specific ingredients regardless of inventory.

**Flow**:
1. Admin makes a direct API call with:
   ```
   POST /ai/suggest-recipes
   {
     "inventory_override": ["chicken", "broccoli", "rice"],
     "simplified": true
   }
   ```
2. System bypasses the actual inventory and generates recipe suggestions based solely on the override.
3. Returns simplified JSON results for easy processing.

## 6. Dietary Restriction Support

**Scenario**: Adapting to newly discovered dietary restrictions.

**Flow**:
1. Alyssa discovers she has a gluten sensitivity.
2. Her preferences are updated to exclude glutenous ingredients.
3. Future recipe suggestions automatically filter out recipes with gluten.
4. When inventory contains gluten-free alternatives, they are prioritized in recipe matches.

## 7. Mobile App Integration

**Scenario**: Carlos is at the grocery store and wants to know what ingredients he needs to buy for dinner.

**Flow**:
1. Carlos opens the mobile app and browses recipe suggestions
2. Each recipe clearly shows:
   - A fit score percentage
   - Which ingredients he already has at home
   - Which ingredients he needs to purchase
3. Carlos selects an Italian pasta dish that shows a 60% fit score
4. He taps "Add missing ingredients to shopping list"
5. The app adds the 4 missing ingredients to his Grocy shopping list
6. Carlos purchases the items, checking them off in the app as he shops

**Key Features Utilized**:
- Simplified recipe view for mobile interface
- Clear visualization of have vs. need-to-buy ingredients
- Integration with Grocy shopping list

## Related Documents

- [[SYSTEM_OVERVIEW]]
- [[USER_REQUIREMENTS]]
- [[API_REFERENCE]]
