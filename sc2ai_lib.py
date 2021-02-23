import re
from custom_logger import output_log


def get_unit_first_order(unit):
    order_queue = unit.orders
    try:
        first_order = order_queue[0].ability.button_name
    except Exception as e:
        output_log(e)
        first_order = ''
    return first_order
