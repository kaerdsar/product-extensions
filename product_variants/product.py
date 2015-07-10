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
from lxml import etree

import openerp
from openerp import models, fields, api
from openerp.exceptions import ValidationError


def slug(name):
    return name.replace(' ', '_').lower()


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    manual_variants = fields.Boolean(compute='_create_variants_manually',
                                     string='Create Variants Manually')

    @api.model
    def fields_view_get(self, *args, **kwargs):
        ctx = self.env.context
        res = super(ProductTemplate, self).fields_view_get(*args, **kwargs)
        if kwargs.get('view_type') == 'form' and ctx.get('category'):
            category = self.env['product.category'].search([('name', '=', ctx['category'])])
            if category:
                arch = res['fields']['product_variant_ids']['views']['tree']['arch']
                arch_start = arch.split('</tree>')[0]

                for attribute in category[0].variant_attributes:
                    field = slug(attribute.name)
                    arch_start += '<field name="%s" />' % field
                    res['fields']['product_variant_ids']['views']['tree']['fields'][field] = {'string': attribute.name, 'type': 'char'}
            
                arch = arch_start + '</tree>'
                res['fields']['product_variant_ids']['views']['tree']['arch'] = arch
        return res
        
    @api.one
    def _create_variants_manually(self):
        category = self.categ_id
        while (category.parent_id):
            if category.manual_variants:
                return True
            category = category.parent_id
        return category.manual_variants
        
    def create_variant_ids(self, cr, uid, ids, context=None):
        xids = [x.id for x in self.browse(cr, uid, ids) if not x.categ_id.manual_variants]
        return super(ProductTemplate, self).create_variant_ids(cr, uid, xids, context)
        
    def _get_default_category(self, cr, uid, context=None):
        if context.get('category'):
            domain = [('name', '=', context['category'])]
            res = self.pool.get('product.category').search(cr, uid, domain)
            return res and res[0] or False
            
    def _get_attributes_by_category(self, cr, uid, context=None):
        if context.get('category'):
            domain = [('name', '=', context['category'])]
            res = self.pool.get('product.category').search(cr, uid, domain)
            if res:
                category = self.pool.get('product.category').browse(cr, uid, res[0])
                return [(0, 0, {'attribute_id': x.id}) for x in category.product_attributes]
            
    _defaults = {
        'categ_id': _get_default_category,
        'attribute_line_ids': _get_attributes_by_category
    }
        
        
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    variant = fields.Char('Name Variant')
    
    def __getitem__(self, key):
        try:
            return super(ProductProduct, self).__getitem__(key)
        except Exception as ex:
            if isinstance(key, basestring):
                if '_ids' in self.__dict__:
                    return self.get_attribute_value(key)
                else:
                    return fields.Char(string=key)
            raise ex
    
    @api.model
    def create(self, vals):
        vals, dynamic_vals = self.clean_data(vals)
        obj = super(ProductProduct, self).create(vals)
        for field, value in dynamic_vals.items():
            obj.set_attribute_value(field, value)
        return obj
        
    @api.multi
    def write(self, vals):
        vals, dynamic_vals = self.clean_data(vals)
        res = super(ProductProduct, self).write(vals)
        for field, value in dynamic_vals.items():
            for record in self:
                record.set_attribute_value(field, value)
        return res
        
    @api.multi
    def read(self, fields=None, load='_classic_read'):
        fields, dynamic_fields = self.clean_data(fields)
        res = super(ProductProduct, self).read(fields, load)
        for field in dynamic_fields:
            for record in res:
                value = self.browse(record['id']).get_attribute_value(field)
                if value:
                    record[field] = value
        return res
        
    @api.one
    def get_attribute_value(self, field):
        for x in self.attribute_value_ids:
            if field == slug(x.attribute_id.name):
                return x.name
        return False
        
    @api.one
    def set_attribute_value(self, field, value):
        pav = self.env['product.attribute.value']
        for x in self.categ_id.variant_attributes:
            if field == x.name or field == slug(x.name):
                domain_I = [('name', '=', value), ('attribute_id', '=', x.id)]
                values = pav.search(domain_I)
                if values:
                    return values[0].write({'product_ids': [(4, self.id)]})
                else:
                    domain_II = [('product_ids', 'in', self.id),
                                 ('attribute_id', '=', x.id)]
                    for value in pav.search(domain_II):
                        value.write({'product_ids': [(3, self.id)]})
                    vals = {x[0]: x[2] for x in domain_I}
                    vals['product_ids'] = [(6, 0, [self.id])]
                    return pav.create(vals)

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            variant = ""
            for attribute_line in record.product_tmpl_id.attribute_line_ids:
                if attribute_line.attribute_id.show_in_name and attribute_line.value_ids:
                    for value in attribute_line.value_ids:
                        variant += "%s "%value.name
            if variant == "":
                name = record.name
            else:
                record.variant = variant
                name = "%s [%s]" % (record.name, record.variant)
            result.append((record.id, name))
        return result

    def clean_data(self, data):
        dynamic_data = None
        if isinstance(data, list):
            dynamic_data = []
            static_data = []
            for field in data:
                if field not in self._fields:
                    dynamic_data.append(field)
                else:
                    static_data.append(field)
            data = static_data
        elif isinstance(data, dict):
            dynamic_data = {}
            for key in data.copy():
                if key not in self._fields:
                    dynamic_data[key] = data[key]
                    del data[key]
        return data, dynamic_data
