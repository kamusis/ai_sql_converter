# SQL Conversion Automation Tool

[![Python Tests](https://github.com/kamusis/ai_sql_converter/actions/workflows/python-tests.yml/badge.svg)](https://github.com/kamusis/ai_sql_converter/actions/workflows/python-tests.yml)

A powerful AI-powered tool for automatically converting SQL scripts between different database management systems with comprehensive prompt optimization.

## 🌟 Features

- **Multi-Database Support**: Convert SQL between major database types:
  - SYBASE
  - MYSQL
  - POSTGRESQL
  - ORACLE
  - SQLSERVER
  - DB2

- **Smart Conversion**:
  - Preserves original SQL functionality
  - Handles complex SQL structures
  - Supports large SQL files through intelligent chunking
  - Parallel processing for faster conversion

- **Performance Tracking**:
  - Detailed time logging
  - Per-chunk conversion tracking
  - Optimization time monitoring

- **Multiple AI Provider Support**:
  - OpenAI
  - Anthropic

## 📋 Requirements

- Python 3.8+
- OpenAI API key or Anthropic API key
- Required Python packages:
  ```
  openai>=1.3.0
  anthropic>=0.5.0
  python-dotenv
  aiohttp
  ```

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/kamusis/ai_sql_converter
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key or Anthropic API key and other configurations

## 🔧 Usage

### Basic Usage

1. Place your SQL files in the `sql_files` directory
2. Configure the `.env` file
3. Run the converter:
   ```bash
   python sql_converter.py
   ```

### Advanced Usage

#### Multiple File Conversion
```bash
# Configure SOURCE_DB_CODE_FILE in .env:
SOURCE_DB_CODE_FILE=./sql_files/*.sql    # Process all SQL files
# Or specify multiple files:
SOURCE_DB_CODE_FILE=./sql_files/file1.sql;./sql_files/file2.sql
```

#### Custom Output Location
```bash
# Configure TARGET_DB_CODE_FILE in .env:
TARGET_DB_CODE_FILE=./output/    # Custom output directory
# Or use 'auto' for automatic naming:
TARGET_DB_CODE_FILE=auto         # Creates [source_name]_result.sql
```

## 🔑 Environment Variables

The following environment variables can be configured in `.env` file:

```bash
# OpenAI Configuration
OPENAI_ENABLED=true                 # Enable/disable OpenAI provider
OPENAI_API_KEY=your_openai_api_key  # Your OpenAI API key
OPENAI_MODEL=gpt-4o-mini            # Model to use for OpenAI

# Claude Configuration
CLAUDE_ENABLED=false                   # Enable/disable Claude provider
CLAUDE_API_KEY=your_claude_api_key     # Your Claude API key
CLAUDE_MODEL=claude-3-haiku-20240307   # Model to use for Claude

# Default AI Provider
DEFAULT_AI_PROVIDER=openai         # Which provider to use by default (openai/claude)

# Database Configuration
SOURCE_DB_TYPE=SYBASE             # Source database type
TARGET_DB_TYPE=POSTGRESQL         # Target database type
SOURCE_DB_CODE_FILE=./sql_files/source1.sql  # Source SQL file(s)
TARGET_DB_CODE_FILE=auto          # Target file naming (auto/specific path)
```

### Environment Variables Description

#### AI Provider Configuration
- `OPENAI_ENABLED`: Enable/disable OpenAI provider (true/false)
- `CLAUDE_ENABLED`: Enable/disable Claude provider (true/false)
- `DEFAULT_AI_PROVIDER`: Default provider to use (openai/claude)

#### OpenAI Configuration
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: OpenAI model to use
  - Available models: gpt-4o-mini, gpt-4o, o1-preview, o1-mini

#### Claude Configuration
- `CLAUDE_API_KEY`: Your Claude API key
- `CLAUDE_MODEL`: Claude model to use
  - Available models: claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-haiku-20240307, claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022

#### Database Configuration
- `SOURCE_DB_TYPE`: Source database type
- `TARGET_DB_TYPE`: Target database type
- `SOURCE_DB_CODE_FILE`: Source SQL file path
- `TARGET_DB_CODE_FILE`: Target SQL file path

### Supported Database Types
- SYBASE
- MYSQL
- POSTGRESQL
- ORACLE
- SQLSERVER
- DB2

## 🛠 Configuration Tips

### Prompt Templates
`prompts/optimized_prompt.txt`:
   - Modified as you see fit

### Enabling Multiple Providers
1. Set `OPENAI_ENABLED=true` and/or `CLAUDE_ENABLED=true`
2. Configure respective API keys
3. Set preferred `DEFAULT_AI_PROVIDER`

### Provider Selection Strategy
- System uses the default provider specified in `DEFAULT_AI_PROVIDER`
- Falls back to first available provider if default is unavailable
- Allows runtime provider switching via API

### Best Practices
- Enable multiple providers for redundancy
- Configure fallback providers
- Test with different providers for optimal results

## 🔍 Program Logic

### 1. Prompt Management
- Loads prompt template

### 2. SQL Processing
- Splits large SQL files into manageable chunks
- Handles complex SQL structures (stored procedures, functions)
- Maintains SQL statement integrity during splitting

### 3. Conversion Process
- Parallel processing of SQL chunks
- Uses GPT-4o-mini or Claude-3-haiku for faster conversion
- Maintains conversion context across chunks

### 4. Performance Optimization
- Caches optimized prompts
- Parallel chunk processing
- Efficient file handling
- Smart chunk size management

## 📁 Directory Structure

```
.
├── sql_converter.py         # Main conversion script
├── .env                     # Configuration file
├── requirements.txt         # Python dependencies
├── prompts/
│   └── optimized_prompt.txt   # Optimized prompt
├── sql_files/               # Source SQL files
│   └── source1.sql
└── README.md               # This documentation

```

## ⚠️ Limitations

- Relies on OpenAI's API or Anthropic's API availability
- Performance depends on API response time
- Complex SQL structures may require manual verification
- API rate limits may affect processing speed

## 🔄 Troubleshooting

1. **Conversion Errors**:
   - Verify source SQL syntax
   - Check chunk size configuration
   - Review database type settings

2. **Performance Issues**:
   - Adjust chunk size
   - Check network connectivity
   - Verify API key status

## 🛠 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

MIT License

Copyright (c) 2024 [kamusis@Enmotech](https://github.com/kamusis)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 👥 Authors

[kamusis@Enmotech](https://github.com/kamusis)

## 🧪 Testing

### Test Structure

1. **File Loading Tests** (`tests/test_file_loading.py`)
   - Tests SQL file loading and validation
   - Tests environment configuration
   - Tests basic functionality including:
     - SQL file reading
     - Environment variable handling
     - Database type validation

### Test Fixtures

Test fixtures are located in the `tests/fixtures` directory. These include:
- Sample SQL files for different database types
- Expected conversion results

### Writing New Tests

When adding new features or fixing bugs:
1. Add corresponding test cases in `test_file_loading.py`
2. Follow the existing test structure and naming conventions
3. Ensure all tests pass before submitting changes
