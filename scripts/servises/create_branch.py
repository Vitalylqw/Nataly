#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для создания Git ветки."""
import subprocess
import sys

def create_branch(branch_name: str) -> None:
    """Создает новую Git ветку и переключается на неё."""
    try:
        result = subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print(f'Ветка "{branch_name}" успешно создана и активирована.')
            print(result.stdout)
        else:
            print(f'Ошибка при создании ветки: {result.stderr}')
            sys.exit(1)
    except Exception as e:
        print(f'Ошибка: {e}')
        sys.exit(1)

if __name__ == '__main__':
    branch_name = 'доработки'
    create_branch(branch_name)

