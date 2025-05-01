# Changelog

## [Unreleased]

### Added
- Intelligent ingredient combinations using AI for vastly improved recipe search results
- New recipe output format with clear "fit score" and ingredient categorization
- Support for simplified recipe output format via `simplified=true` parameter
- Better visualization of which ingredients you have vs. need to buy

### Changed
- Updated `/ai/suggest-recipes` endpoint to use formatted recipe output
- Improved inventory sync to correctly handle deletions from Grocy
- Fixed bug with dietary restrictions where empty preferences weren't properly handled
- Fixed OpenAI API calls in feedback.py to use the newer client format

### Fixed
- Empty ingredient lists no longer cause recipe search failures
- Fixed parameter order bug in user preference updates
- Fixed trailing whitespace bug in ingredient name cleaning
- Empty dietary restrictions now properly recognized in inventory sync

## [0.1.0] - 2025-04-01

### Added
- Initial release with basic recipe suggestions
- Integration with Grocy inventory system
- User preference management
- AI filtering of inventory items
- Recipe classification with AI
