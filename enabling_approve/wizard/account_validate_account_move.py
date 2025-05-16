from odoo import models, fields, _, api
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class ValidateAccountMove(models.TransientModel):
    _inherit = "validate.account.move"
    _description = "Validate Account Move"

    def validate_move(self):
        if self._context.get('active_model') == 'account.move':
            domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'draft')]
        elif self._context.get('active_model') == 'account.journal':
            domain = [('journal_id', '=', self._context.get('active_id')), ('state', '=', 'draft')]
        else:
            _logger.info("\n\n\t\t  ============ context =========== %s", self._context)
            raise UserError(_("Missing 'active_model' in context."))

        moves = self.env['account.move'].search(domain).filtered('line_ids')

        if not moves:
            raise UserError(_('There are no journal items in the draft state to post.'))
        if self.env['account.move'].search(domain, limit=1).move_type not in ('in_invoice', 'in_refund', 'in_receipt'):
            return super(ValidateAccountMove, self).validate_move()
        else:
            moves = moves.filtered(
                lambda x: x.approval_stage == 'first_approved' and x.second_approver_id.id == self.env.uid
            )
            moves._post(not self.force_post)
            moves.write({'approval_stage': 'final_approved'})
            return {'type': 'ir.actions.act_window_close'}

class ApprovalWizard(models.TransientModel):
    _name = 'approval.wizard'

    reason_selection = fields.Selection([
        ('1', 'A suitable hapu business could not be found.'),
        ('2', 'A hapu business was not considered as the supply / job was time critical.'),
        ('3', 'The expenditure is $1000 or less (excl. GST).'),
        ('4', 'Other reason (please add details as log note).')
    ], string='Reason', tracking=True)

    reasons_id = fields.Many2one('reasons.toi.pakihi',string="Reasons", required=True, tracking=True)
    move_id = fields.Many2one('account.move')

    def action_approve(self):
        active_id = self._context.get('active_id')
        record = self.env['account.move'].browse(active_id)
        _logger.info("\n\n\t\t  ============ self.move_id =========== %s %s", self.move_id, record)
        # record.reason_selection = self.reason_selection
        record.reasons_id = self.reasons_id
        
        # _logger.info("\n\n\t\t  ============ context =========== %s", record.reason_selection)
        _logger.info("\n\n\t\t  ============ context =====reasons_id====== %s", record.reasons_id)
        # self.move_id.reason_selection = self.reason_selection
        self.move_id.reasons_id = self.reasons_id
        
        # _logger.info("\n\n\t\t  ============ context =========== %s", self.move_id.reason_selection)
        _logger.info("\n\n\t\t  ============ context ==reasons_id========= %s", self.move_id.reasons_id)
        record.action_approve_new()