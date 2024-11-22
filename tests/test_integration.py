import unittest
import os
import asyncio
from unittest.mock import patch
from sql_converter import SQLConverter

class TestSQLConverterIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for SQL Converter"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        cls.test_files = {
            'sybase_to_postgresql': {
                'source': './tests/fixtures/sybase_source.sql',
                'expected': './tests/fixtures/postgresql_expected.sql'
            },
            'mysql_to_postgresql': {
                'source': './tests/fixtures/mysql_source.sql',
                'expected': './tests/fixtures/postgresql_expected_mysql.sql'
            }
        }
        
        # Create test fixtures directory
        os.makedirs('./tests/fixtures', exist_ok=True)
        
        # Create test SQL files
        cls._create_test_files()

    @classmethod
    def _create_test_files(cls):
        """Create test SQL files with sample content"""
        sybase_sql = """
        /* Sybase SQL */
        SELECT TOP 10 * FROM employees
        WHERE salary > 50000
        ORDER BY hire_date DESC
        """

        mysql_sql = """
        /* MySQL SQL */
        SELECT * FROM employees
        WHERE salary > 50000
        LIMIT 10
        ORDER BY hire_date DESC
        """

        postgresql_expected = """
        /* PostgreSQL SQL */
        SELECT * FROM employees
        WHERE salary > 50000
        ORDER BY hire_date DESC
        LIMIT 10
        """

        postgresql_expected_mysql = """
        /* PostgreSQL SQL */
        SELECT * FROM employees
        WHERE salary > 50000
        ORDER BY hire_date DESC
        LIMIT 10
        """

        # Write test files
        with open(cls.test_files['sybase_to_postgresql']['source'], 'w') as f:
            f.write(sybase_sql)
        with open(cls.test_files['sybase_to_postgresql']['expected'], 'w') as f:
            f.write(postgresql_expected)
        with open(cls.test_files['mysql_to_postgresql']['source'], 'w') as f:
            f.write(mysql_sql)
        with open(cls.test_files['mysql_to_postgresql']['expected'], 'w') as f:
            f.write(postgresql_expected_mysql)

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests"""
        for test_case in cls.test_files.values():
            for file_path in test_case.values():
                if os.path.exists(file_path):
                    os.remove(file_path)
        if os.path.exists('./tests/fixtures'):
            os.rmdir('./tests/fixtures')

    async def test_sybase_to_postgresql_conversion(self):
        """Test Sybase to PostgreSQL conversion"""
        test_env = {
            'OPENAI_API_KEY': 'test-key',
            'SOURCE_DB_TYPE': 'SYBASE',
            'TARGET_DB_TYPE': 'POSTGRESQL',
            'SOURCE_DB_CODE_FILE': self.test_files['sybase_to_postgresql']['source'],
            'TARGET_DB_CODE_FILE': 'auto'
        }
        
        with open(self.test_files['sybase_to_postgresql']['source'], 'r') as f:
            source_sql = f.read().strip()
        with open(self.test_files['sybase_to_postgresql']['expected'], 'r') as f:
            expected_sql = f.read().strip()

        with patch.dict('os.environ', test_env):
            converter = SQLConverter()
            converted_sql = await converter.convert_sql(source_sql)
        
        # Compare normalized SQL (removing whitespace and case sensitivity)
        self.assertEqual(
            ' '.join(converted_sql.lower().split()),
            ' '.join(expected_sql.lower().split())
        )

    async def test_mysql_to_postgresql_conversion(self):
        """Test MySQL to PostgreSQL conversion"""
        test_env = {
            'OPENAI_API_KEY': 'test-key',
            'SOURCE_DB_TYPE': 'MYSQL',
            'TARGET_DB_TYPE': 'POSTGRESQL',
            'SOURCE_DB_CODE_FILE': self.test_files['mysql_to_postgresql']['source'],
            'TARGET_DB_CODE_FILE': 'auto'
        }
        
        with open(self.test_files['mysql_to_postgresql']['source'], 'r') as f:
            source_sql = f.read().strip()
        with open(self.test_files['mysql_to_postgresql']['expected'], 'r') as f:
            expected_sql = f.read().strip()

        with patch.dict('os.environ', test_env):
            converter = SQLConverter()
            converted_sql = await converter.convert_sql(source_sql)
        
        # Compare normalized SQL (removing whitespace and case sensitivity)
        self.assertEqual(
            ' '.join(converted_sql.lower().split()),
            ' '.join(expected_sql.lower().split())
        )

if __name__ == '__main__':
    unittest.main()
