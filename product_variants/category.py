# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010, 2014 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
from openerp.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    manual_variants = fields.Boolean('Create Variants Manually')
    product_attributes = fields.Many2many('product.attribute',
                                          'category_product_attribute_rel',
                                          'category_id', 'attribute_id',
                                          'Attributes',
                                          domain=[('belongs_to', '=', 'product')])
    variant_attributes = fields.Many2many('product.attribute',
                                          'category_variant_attribute_rel',
                                          'category_id', 'attribute_id',
                                          'Attributes',
                                          domain=[('belongs_to', '=', 'variant')])
    menu_parent = fields.Many2one('ir.ui.menu', 'Menu Parent')
    menu = fields.Many2one('ir.ui.menu', 'Menu')
    action = fields.Many2one('ir.actions.act_window', 'Action')
    
    @api.model
    def create(self, vals):
        obj = super(ProductCategory, self).create(vals)
        if obj.define_product_type and obj.menu_parent:
            obj.create_menu_and_action()
        return obj
        
    @api.one
    def unlink(self):
        self.unlink_menu_and_action()
        return super(ProductCategory, self).unlink()
                                          
    @api.one
    def create_menu_and_action(self):
        action, menu = False, False
        if self.action:
            action = self.action
        else:
            vals = {
                'name': self.name,
                'res_model': 'product.template',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'context': {'category': self.name}
            }
            action = self.env['ir.actions.act_window'].sudo().create(vals)
        if self.menu:
            menu = self.menu
        else:
            vals = {
                'name': self.name,
                'parent_id': self.menu_parent.id,
                'action': '%s,%s' % ('ir.actions.act_window', str(action.id))
            }
            menu = self.env['ir.ui.menu'].sudo().create(vals)
        return self.write({'action': action.id, 'menu': menu.id})
        
    @api.one
    def unlink_menu_and_action(self):
        if self.menu:
            self.menu.unlink()
        if self.action:
            self.action.unlink()
