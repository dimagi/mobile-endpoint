import multiprocessing
preload_app = True
workers = multiprocessing.cpu_count() * 2 + 1
