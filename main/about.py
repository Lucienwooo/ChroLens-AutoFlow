# -*- coding: utf-8 -*-
"""
關於對話框 - ChroLens_AutoFlow
封裝版本資訊對話框以保持介面統一
"""

from version_info_dialog import VersionInfoDialog

def AboutDialog(parent=None):
    """
    提供與舊版相容的介面，背後調用新的 VersionInfoDialog
    """
    from ChroLens_AutoFlow import VERSION, FULL_APP_NAME
    # 這裡我們需要一個 MainWindow 實例的 version_manager，但在獨立調用時可能沒有
    # 所以在 ChroLens_AutoFlow.py 中直接調用 VersionInfoDialog 是更佳實踐
    # 此檔案保留作為模組導入的預留
    pass
