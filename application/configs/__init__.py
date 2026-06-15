"""
Configuration package for the hedge-fund grade trading system.

The legacy ``Configs`` singleton was retired in E1.T6. All configuration is now
produced by the single loader at ``bootstrap.settings.load_settings``. This
package retains only the typed schemas, environment helpers, and the
``EnhancedConfigLoader`` used by that loader.
"""
