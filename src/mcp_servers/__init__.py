"""
MCP Servers Package - Model Context Protocol servers for executing actions.

MCP servers are the "hands" of the AI Employee system. They execute
approved actions like sending emails, browser automation, etc.

Available Servers:
- EmailMCPServer: Send, draft, reply, forward emails via Gmail API
- OdooMCP: Odoo ERP accounting integration
- SocialMCP: Social media posting (Facebook, Instagram, Twitter)
"""

try:
    from .email_mcp import EmailMCPServer
except ImportError:
    EmailMCPServer = None

try:
    from .odoo_mcp import OdooMCP
except ImportError:
    OdooMCP = None

try:
    from .social_mcp import SocialMCP
except ImportError:
    SocialMCP = None

__all__ = ['EmailMCPServer', 'OdooMCP', 'SocialMCP']
