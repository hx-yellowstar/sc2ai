reported_log = set()


def output_log(log_content):
    log_content = str(log_content)
    if log_content not in reported_log:
        reported_log.add(log_content)
        print('CUSTOM_INFO: {0}'.format(log_content))