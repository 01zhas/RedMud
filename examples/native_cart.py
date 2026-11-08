from redmud import Pipeline, field as F, list_sum
item = Pipeline().check('quantity_positive', F('quantity') > 0).derive('total', F('price') * F('quantity'))
order = Pipeline().map_list('items', item).derive('order_total', list_sum('items', 'total'))
cart = Pipeline().map_list('orders', order).derive('cart_total', list_sum('orders', 'order_total'))
result = cart.run_one({'cart_id':5001,'orders':[{'items':[{'price':1000,'quantity':2},{'price':500,'quantity':3}]}]})
assert result.ok and result.value['cart_total'] == 3500
print(result.value)
