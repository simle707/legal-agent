# -*- coding: utf-8 -*-
"""分页工具"""
from typing import List


class PageUtil:

    @staticmethod
    def paginate(data: List, page_num: int = 1, page_size: int = 10) -> List:
        if page_num < 1:
            page_num = 1
        start = (page_num - 1) * page_size
        return data[start:start + page_size]

    @staticmethod
    def total(data: List) -> int:
        return len(data)
