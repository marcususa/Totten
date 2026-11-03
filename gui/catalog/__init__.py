from .catalog_view import SearchCatalogWorkspace, on_group_selected
from .core import CatalogAnalysis

def create_workspace(master, name="analysis", **kwargs):
    """
    Factory router for the catalog package:
    - Returns SearchCatalogWorkspace when explicitly navigating to catalog search.
    - Defaults directly to the core Catalog Analysis view on app startup.
    """
    if name in ("search_catalog", "catalog"):
        return SearchCatalogWorkspace(master, **kwargs)
    else:
        kwargs.pop('target_game', None)
        kwargs.pop('active_index', None)
        return CatalogAnalysis(master, **kwargs)