import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize('url,expected', [
    ('postgresql://postgres.ref:password@aws-0-test.pooler.supabase.com:5432/postgres', 'sslmode=require'),
    ('postgresql://postgres.ref:password@aws-0-test.pooler.supabase.com:6543/postgres?sslmode=require', 'port 5432'),
    ('postgresql://postgres.PROJECT_REF:password@host:5432/postgres?sslmode=require', 'real PostgreSQL'),
])
def test_unsafe_database_configuration_is_rejected(url, expected):
    result = subprocess.run([sys.executable, '-c', 'import config.settings'],
                            cwd=Path(__file__).resolve().parents[1],
                            env={**os.environ, 'DATABASE_URL': url}, capture_output=True, text=True)
    assert result.returncode != 0
    assert expected in result.stderr


def test_supabase_session_pooler_configuration():
    result = subprocess.run([sys.executable, '-c', 'from config.settings import DATABASES; print(DATABASES["default"]["HOST"])'],
                            cwd=Path(__file__).resolve().parents[1],
                            env={**os.environ, 'DATABASE_URL': 'postgresql://postgres.ref:password@aws-0-test.pooler.supabase.com:5432/postgres?sslmode=require'},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'aws-0-test.pooler.supabase.com'
