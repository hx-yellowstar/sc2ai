import re
from custom_logger import output_log


def get_unit_first_order(unit):
    order_queue = unit.orders
    try:
        first_order = re.search('\(name=(.*?)\)', str(order_queue[0].ability)).group(1)
    except Exception as e:
        output_log(e)
        first_order = ''
    return first_order
