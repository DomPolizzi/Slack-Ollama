'''
This module contains the `thread_run_map` dictionary which maps thread IDs to their corresponding run map.
Eventually, we will move to redis
'''
thread_run_map: dict[str, str] = {}