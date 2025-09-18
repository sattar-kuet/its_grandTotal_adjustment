from odoo import models, fields, api
class AccountMove(models.Model):
    _inherit = "account.move"

    custom_total = fields.Monetary(
        string="Custom Total",
        store=True,
        currency_field="currency_id"
    )

    @api.depends(    'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'discount_type',
        'discount_rate',
        'custom_total')  # same dependencies including custom_total
    def _compute_amount(self):
        # First call the original implementation
        super(AccountMove, self)._compute_amount()

        for move in self:
            try:
                tax_rate = 0.15

                # If custom_total is provided and > 0, use it
                if move.custom_total and move.custom_total > 0:
                    subtotal = move.amount_untaxed_signed or 0.0
                    total = move.custom_total or 0.0
                # Prevent division by zero
                if subtotal <= 0:
                    continue
                total = round(total, 2)

                if move.discount_type == 'amount':
                    discount = subtotal - (move.custom_total / (1 + tax_rate))
                    move.amount_discount = discount
                    its_untaxed_amount = subtotal - discount
                else:  # percent
                    denominator = subtotal * (1 + tax_rate)
                    if denominator == 0:
                        continue
                    discount = (1 - (move.custom_total / denominator)) * 100
                    move.amount_discount = (discount * subtotal) / 100
                    its_untaxed_amount = subtotal - move.amount_discount

                # Tax and totals
                its_tax = its_untaxed_amount * tax_rate
                its_untaxed_amount = total - its_tax
                move.amount_untaxed = its_untaxed_amount
                move.amount_tax = its_tax
                move.amount_total = total
                move.amount_residual = move.amount_total
                move.amount_residual_signed = move.amount_total

            except ZeroDivisionError:
                continue
            except Exception as e:
                print(f"Error in custom total computation: {e}")
                continue

    @api.onchange('custom_total', 'discount_type')
    def _onchange_custom_total(self):
        for move in self:
            tax_rate = 0.15

            # If custom_total is provided and > 0, use subtotal from amount_untaxed_signed
            if move.custom_total and move.custom_total > 0:
                subtotal = move.amount_untaxed_signed or 0.0
                total = move.custom_total or 0.0
            if subtotal <= 0:
                continue
            total = round(total, 2)

            if move.discount_type == 'amount':
                discount = subtotal - (move.custom_total / (1 + tax_rate))
                move.discount_rate = discount
                its_total_discount = discount
                its_untaxed_amount = subtotal - its_total_discount
            else:  # percent
                denominator = subtotal * (1 + tax_rate)
                if denominator == 0:
                    continue
                discount = (1 - (move.custom_total / denominator)) * 100
                move.discount_rate = discount
                its_total_discount = (discount * subtotal) / 100
                its_untaxed_amount = subtotal - its_total_discount

            # Tax and totals
            its_tax = its_untaxed_amount * tax_rate
            its_untaxed_amount = total - its_tax

            # Show breakdown in text
            move.breakdown_details = f"""
                Subtotal: {subtotal:.2f}
                Discount: -{its_total_discount:.2f}
                Untaxed Amount: {its_untaxed_amount:.2f}
                Tax (15%): {its_tax:.2f}
                ----------------------------
                Total: {total:.2f}
            """.strip()
