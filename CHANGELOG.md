# Changelog

## [1.1.2] - 2024-11-25

### 🔧 Dependencies
- Added `setup.py` for proper package management
- Fixed invalid requirements.txt format
- Removed unused `json` module import
- Added `colorama` for Windows color support
- Moved test dependencies to optional [test] section
- Improved dependency documentation

## [1.1.1] - 2024-11-25

### 🐛 Bug Fixes
- Added missing `glob` module import for wildcard file pattern support
- Fixed potential crash in multi-file mode when using wildcards

### 🧪 Testing
- Added test cases for multi-file SQL processing
- Added wildcard pattern file loading tests

## [1.1.0] - 2024-11-25

### 🚀 Enhanced Progress Monitoring

#### Added
- Detailed progress tracking for SQL chunk processing
  - Millisecond-precision timing for each chunk conversion
  - Size change statistics (input → output chars with percentage)
  - Individual chunk success/failure status with timing

#### Changed
- Improved logging format with emoji indicators
  - 📊 Initial statistics
  - 🔄 Processing status
  - ✅ Success status
  - ❌ Failure status
  - 📈 Final summary

#### Enhanced Statistics
- Added comprehensive conversion statistics
  - Total processing time (ms)
  - Average time per chunk (ms)
  - Input/output size comparison
  - Success/failure ratio
  - Chunk size distribution

### 🔧 Configuration Updates

#### Changed
- Updated default OpenAI model to 'gpt-4o-mini'
- Changed default AI provider to 'openai' (from 'claude')
- Retained Claude model as 'claude-3-haiku-20240307'

### 📝 File Management

#### Changed
- Enhanced target file naming strategy
  - New format: `{source_filename}_{target_db_type}_{model_name}.sql`
  - Full model name preservation in output filename

### 🐛 Bug Fixes
- Fixed asynchronous API calls using `asyncio.to_thread()`
- Resolved "object Message can't be used in 'await' expression" error in Claude integration

### 💡 Code Quality
- Improved error handling with detailed error messages
- Enhanced code documentation
- Added thousand separators for better number readability
- Optimized progress display formatting

## [1.0.0] - 2024-11-22

### 🎉 Initial Release
- Basic SQL conversion functionality
- Support for OpenAI and Claude providers
- Chunk-based processing for large SQL files
- Asynchronous conversion pipeline
- Basic progress monitoring
