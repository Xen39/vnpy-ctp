__all__=["sleep_till"]

import time

def sleep_till(func, timeout=60):
    count = 0
    while not func():
        time.sleep(1)
        count += 1
        if count > timeout:
            return False
    return True