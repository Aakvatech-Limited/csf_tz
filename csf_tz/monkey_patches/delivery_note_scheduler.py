"""Compatibility entry point for the delivery-note scheduler.

The scheduled hook uses custom_api directly; importing this module no longer
replaces that function at runtime.
"""

from csf_tz.custom_api import create_delivery_note_for_all_pending_sales_invoice

__all__ = ["create_delivery_note_for_all_pending_sales_invoice"]
