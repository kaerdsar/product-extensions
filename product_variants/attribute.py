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


class ProductAttribute(models.Model):
    _name = 'product.attribute'
    _inherit = 'product.attribute'

    belongs_to = fields.Selection([('product', 'Product'),
                                   ('variant', 'Variant')], 'Belongs to')
    attribute_type = fields.Selection([('str', 'String'),
                                       ('int', 'Integer'),
                                       ('float', 'Float')], 'Type',
                                      default='str')
    mandatory = fields.Boolean('Mandatory')
    show_in_name = fields.Boolean('Show in Name')
    sequence = fields.Integer('Sequence', default=0)
    source = fields.Char('Source')
    
    @api.one
    def pull_values_from_source(self):
        model = self.env[self.source]
        values = [x['name'] for x in model.search_read([], ['name'])]
        value = self.env['product.attribute.value']
        return value.find_or_create_values(self, values)


class ProductAttributeValue(models.Model):
    _name = 'product.attribute.value'
    _inherit = 'product.attribute.value'

    @api.one
    @api.constrains('name')
    def _check_attribute_type(self):
        try:
            eval('%s("%s")' % (self.attribute_id.attribute_type, self.name))
        except:
            raise ValidationError("Invalid type")
            
    @api.model
    def find_or_create_values(self, attribute, names):
        value_ids = []
        for name in names:
            domain = [('attribute_id', '=', attribute.id), ('name', '=', name)]
            values = self.search(domain)
            if values:
                vid = values[0].id
            else:
                vid = self.create({x[0]: x[2] for x in domain})
            value_ids.append(vid)
        return value_ids
            
