# Change Log

## [Unreleased]

### Added
- **AnyCost Stream API Compliance**: Updated `upload_to_anycost()` function to include required `month` parameter in ISO 8601 format (e.g., "2024-08")
- **Operation Type Support**: Added support for operation types when uploading to AnyCost Stream:
  - `replace_drop` (default): Replace all existing data for the month
  - `replace_hourly`: Replace data with overlapping hours  
  - `sum`: Append data to existing records
- **Interactive Prompts**: Added user prompts for month selection and operation type during upload
- **Comprehensive Test Suite**: Added unit tests covering all functions with 11 test cases
  - Tests for CSV processing, data transformation, and API upload functionality
  - Mocked external dependencies for reliable testing
  - Located in `tests/` directory with pytest framework

### Changed  
- Enhanced function documentation to explain all required and optional parameters for AnyCost Stream uploads
- Updated file header comments to document month and operation requirements

### Technical Details
- JSON payload now includes `month`, `operation`, and `data` fields as per AnyCost Stream API specification
- Maintains backward compatibility while adding new required functionality
- All tests pass successfully with proper mocking of external dependencies

---

## Resources for generating a changelog:

[skywinder/Github-Changelog-Generator](https://github.com/skywinder/Github-Changelog-Generator) - generates a full changelog that overwrites the existing CHANGELOG.md. 

[hzalaz/wt-oss-milestone-changelog](https://github.com/hzalaz/wt-oss-milestone-changelog) - generates a snippet of Markdown that can be added to a CHANGELOG.md.

[conventional-changelog/conventional-changelog](https://github.com/conventional-changelog/conventional-changelog/tree/master/packages/conventional-changelog-cli) - generates a full changelog based on commit history with the option to append to an existing changelog.