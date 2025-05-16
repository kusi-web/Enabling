from odoo import models, fields
from odoo.exceptions import UserError, ValidationError,logging,Warning

_logger = logging.getLogger(__name__)

class DuplicateVendorBillWizard(models.TransientModel):
    _name = 'duplicate.vendor.bill.wizard'
    _description = 'Duplicate Vendor Bill Warning Wizard'

    move_id = fields.Many2one('account.move', string='Move', required=True)
    warning_message = fields.Text(string='Message', readonly=True, default='Vendor with the same amount detected in the last 12 months.')

    def confirm(self):
        _logger.info("\n\n\t confirm=== ")

        for rec in self:
            _logger.info("\n\n\t move_id before confirmation:==== %s", rec.move_id)
            """Called when the user clicks 'Confirm' in the popup."""
            # Call the continuation of the approval logic from the related move

            if self.move_id:
                _logger.info("\n\n\t move_id is valid, proceeding with _continue_approval_logic")
                return  rec.move_id._continue_approval_logic()
            else:
                _logger.warning("\n\n\t move_id is None, cannot proceed")
                raise UserError(_('No move_id is set, unable to proceed.'))
