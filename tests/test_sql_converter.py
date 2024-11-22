import unittest
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from sql_converter import SQLConverter
from prompt_optimizer import PromptOptimizer

class TestSQLConverter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """Set up test environment before each test case"""
        self.test_env = {
            'OPENAI_API_KEY': 'test-key',
            'SOURCE_DB_TYPE': 'SYBASE',
            'TARGET_DB_TYPE': 'POSTGRESQL',
            'SOURCE_DB_CODE_FILE': './tests/fixtures/test_source.sql',
            'TARGET_DB_CODE_FILE': 'auto'
        }
        with patch.dict('os.environ', self.test_env):
            self.converter = SQLConverter()
        
        # Create test SQL file
        os.makedirs('./tests/fixtures', exist_ok=True)
        with open('./tests/fixtures/test_source.sql', 'w') as f:
            f.write('SELECT * FROM test_table WHERE id = 1;')

    def tearDown(self):
        """Clean up after each test case"""
        if os.path.exists('./tests/fixtures/test_source.sql'):
            os.remove('./tests/fixtures/test_source.sql')

    def test_initialization(self):
        """Test SQLConverter initialization"""
        self.assertEqual(self.converter.source_db_type, 'SYBASE')
        self.assertEqual(self.converter.target_db_type, 'POSTGRESQL')
        self.assertIsInstance(self.converter.prompt_optimizer, PromptOptimizer)

    @patch('asyncio.get_event_loop')
    async def test_convert_sql_chunk(self, mock_loop):
        """Test SQL chunk conversion"""
        # 创建模拟响应
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="SELECT * FROM test_table WHERE id = 1;"))
        ]
        
        # 设置模拟执行器
        mock_executor = MagicMock()
        mock_executor.submit = MagicMock(return_value=mock_response)
        
        # 设置模拟事件循环
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_response)
        
        chunk = "SELECT * FROM test_table WHERE id = 1;"
        result = await self.converter._convert_sql_chunk(chunk)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_split_sql_into_chunks(self):
        """Test SQL splitting functionality"""
        sql = "SELECT * FROM table1 go INSERT INTO table2 VALUES (1, 2) go UPDATE table3 SET col = 1"
        chunks = self.converter._split_sql_into_chunks(sql)
        self.assertEqual(len(chunks), 3)

    @patch('sql_converter.SQLConverter._convert_sql_chunk')
    async def test_convert_sql_parallel(self, mock_convert):
        """Test parallel SQL conversion"""
        mock_convert.return_value = "converted SQL"
        sql = "SELECT * FROM table1; INSERT INTO table2 VALUES (1, 2);"
        result = await self.converter._convert_sql_parallel(sql)
        self.assertIsInstance(result, str)
        self.assertTrue(mock_convert.called)

    def test_validate_db_type(self):
        """Test database type validation"""
        self.assertTrue(self.converter._validate_db_type('POSTGRESQL'))
        with self.assertRaises(ValueError):
            self.converter._validate_db_type('INVALID_DB')

class TestPromptOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = PromptOptimizer()

    def test_load_original_prompt(self):
        """Test loading original prompt template"""
        prompt = self.optimizer.load_original_prompt()
        self.assertIsInstance(prompt, str)
        self.assertTrue(len(prompt) > 0)

    @patch('os.path.exists')
    def test_load_optimized_prompt(self, mock_exists):
        """Test loading optimized prompt"""
        mock_exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data='test prompt')):
            prompt = self.optimizer.load_optimized_prompt()
            self.assertEqual(prompt, 'test prompt')

    def test_save_optimized_prompt(self):
        """Test saving optimized prompt"""
        test_prompt = "Test optimized prompt"
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            self.optimizer.save_optimized_prompt(test_prompt)
            mock_file.assert_called_once()

if __name__ == '__main__':
    unittest.main()
